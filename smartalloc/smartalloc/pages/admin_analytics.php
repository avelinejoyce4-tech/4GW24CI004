<?php
// pages/admin_analytics.php
session_start();
require_once '../config/db.php';
requireLogin('admin');
$pageTitle = 'Analytics';
$activePage = 'analytics';
include '../partials/admin_layout.php';

// Data for charts
$by_type = $db->query("SELECT problem_type, COUNT(*) as cnt FROM tasks GROUP BY problem_type")->fetch_all(MYSQLI_ASSOC);
$by_status = $db->query("SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status")->fetch_all(MYSQLI_ASSOC);
$by_urgency = $db->query("SELECT urgency, COUNT(*) as cnt FROM tasks GROUP BY urgency ORDER BY urgency DESC")->fetch_all(MYSQLI_ASSOC);
$monthly = $db->query("SELECT DATE_FORMAT(created_at,'%b') as month, COUNT(*) as cnt FROM tasks WHERE created_at >= DATE_SUB(NOW(), INTERVAL 6 MONTH) GROUP BY DATE_FORMAT(created_at,'%Y%m') ORDER BY created_at")->fetch_all(MYSQLI_ASSOC);
?>

<div class="sidebar" id="sidebar">
  <div class="sidebar-logo"><div class="logo-icon">🎯</div><div class="logo-text">Smart<span>Alloc</span></div></div>
  <div class="nav-section">
    <div class="nav-label">Main</div>
    <a class="nav-item" href="/smartalloc/pages/admin_dashboard.php"><i class="fas fa-chart-pie"></i> Dashboard</a>
    <a class="nav-item" href="/smartalloc/pages/admin_tasks.php"><i class="fas fa-tasks"></i> Tasks</a>
    <a class="nav-item" href="#"><i class="fas fa-building"></i> NGOs</a>
    <a class="nav-item" href="#"><i class="fas fa-users"></i> Volunteers</a>
    <a class="nav-item active" href="/smartalloc/pages/admin_analytics.php"><i class="fas fa-chart-bar"></i> Analytics</a>
  </div>
  <div class="sidebar-footer">
    <a class="nav-item" href="/smartalloc/pages/logout.php" style="color:var(--danger)"><i class="fas fa-sign-out-alt"></i> Logout</a>
  </div>
</div>

<div class="main-content" id="mainContent">
  <div class="topnav">
    <button class="topnav-toggle" onclick="toggleSidebar()"><i class="fas fa-bars"></i></button>
    <div class="topnav-title">📊 Analytics</div>
    <div class="topnav-actions">
      <div class="user-pill" onclick="toggleUserMenu()">
        <div class="user-avatar"><?= strtoupper(substr($user['name'],0,1)) ?></div>
        <div><div class="user-name"><?= htmlspecialchars($user['name']) ?></div><div class="user-role">Admin</div></div>
      </div>
    </div>
  </div>

  <div class="page-content">
    <div class="grid-2" style="gap:20px">
      <!-- Tasks by Type -->
      <div class="section-card">
        <div class="section-header"><div class="section-title">🍰 Tasks by Type</div></div>
        <div style="padding:20px;height:280px"><canvas id="typeChart"></canvas></div>
      </div>

      <!-- Tasks by Status -->
      <div class="section-card">
        <div class="section-header"><div class="section-title">📊 Tasks by Status</div></div>
        <div style="padding:20px;height:280px"><canvas id="statusChart"></canvas></div>
      </div>
    </div>

    <!-- Monthly Trend -->
    <div class="section-card">
      <div class="section-header"><div class="section-title">📈 Monthly Task Trend</div></div>
      <div style="padding:20px;height:260px"><canvas id="monthChart"></canvas></div>
    </div>

    <!-- Urgency Distribution -->
    <div class="section-card">
      <div class="section-header"><div class="section-title">⚡ Urgency Distribution</div></div>
      <div style="padding:20px;height:220px"><canvas id="urgencyChart"></canvas></div>
    </div>
  </div>
</div>

<div id="sidebarOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99" onclick="toggleSidebar()"></div>

<script>
Chart.defaults.color = 'rgba(255,255,255,0.6)';
Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
Chart.defaults.font.family = 'Space Grotesk';

const COLORS = ['#00D4AA','#FF4757','#FFA502','#5352ED','#2ED573','#1E90FF'];

// Tasks by Type
<?php
$typeLabels = array_column($by_type, 'problem_type');
$typeData = array_column($by_type, 'cnt');
?>
new Chart(document.getElementById('typeChart'), {
  type: 'doughnut',
  data: {
    labels: <?=json_encode(array_map('ucfirst', $typeLabels))?>,
    datasets: [{ data: <?=json_encode($typeData)?>, backgroundColor: COLORS, borderWidth: 0, hoverOffset: 8 }]
  },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { position: 'right' } } }
});

// Tasks by Status
<?php
$statusLabels = array_column($by_status, 'status');
$statusData = array_column($by_status, 'cnt');
?>
new Chart(document.getElementById('statusChart'), {
  type: 'bar',
  data: {
    labels: <?=json_encode(array_map('ucwords', array_map(fn($s)=>str_replace('-',' ',$s), $statusLabels)))?>,
    datasets: [{ label: 'Tasks', data: <?=json_encode($statusData)?>, backgroundColor: ['#00D4AA','#FFA502','#2ED573'], borderRadius: 8, borderSkipped: false }]
  },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } }
});

// Monthly
<?php
$months = array_column($monthly, 'month');
$mCounts = array_column($monthly, 'cnt');
?>
new Chart(document.getElementById('monthChart'), {
  type: 'line',
  data: {
    labels: <?=json_encode($months ?: ['Jan','Feb','Mar','Apr','May','Jun'])?>,
    datasets: [{
      label: 'Tasks Created',
      data: <?=json_encode($mCounts ?: [2,5,3,8,6,10])?>,
      borderColor: '#00D4AA', backgroundColor: 'rgba(0,212,170,0.1)',
      borderWidth: 2, fill: true, tension: 0.4, pointBackgroundColor: '#00D4AA', pointRadius: 5
    }]
  },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true } } }
});

// Urgency
<?php
$urgLabels = array_map(fn($r)=>['1'=>'Minimal','2'=>'Low','3'=>'Medium','4'=>'High','5'=>'Critical'][$r['urgency']], $by_urgency);
$urgData = array_column($by_urgency, 'cnt');
?>
new Chart(document.getElementById('urgencyChart'), {
  type: 'bar',
  data: {
    labels: <?=json_encode($urgLabels)?>,
    datasets: [{ data: <?=json_encode($urgData)?>, backgroundColor: ['#888','#00D4AA','#5352ED','#FFA502','#FF4757'], borderRadius: 6, borderSkipped: false }]
  },
  options: { responsive: true, maintainAspectRatio: false, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }, indexAxis: 'y' }
});

function toggleSidebar() {
  const sb = document.getElementById('sidebar'); const mc = document.getElementById('mainContent'); const ov = document.getElementById('sidebarOverlay');
  if(window.innerWidth <= 768) { sb.classList.toggle('mobile-open'); ov.style.display = sb.classList.contains('mobile-open') ? 'block' : 'none'; }
  else { sb.classList.toggle('collapsed'); mc.classList.toggle('expanded'); }
}
function toggleUserMenu() { alert('Admin: <?= $user['name'] ?>'); }
</script>
</body>
</html>
