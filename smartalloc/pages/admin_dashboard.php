<?php
// pages/admin_dashboard.php
session_start();
require_once '../config/db.php';
requireLogin('admin');

$pageTitle = 'Dashboard';
$activePage = 'dashboard';
include '../partials/admin_layout.php';

// Recent tasks
$tasks = $db->query("SELECT t.*, u.name as creator FROM tasks t LEFT JOIN users u ON t.created_by = u.id ORDER BY t.created_at DESC LIMIT 8")->fetch_all(MYSQLI_ASSOC);

// Recent volunteers
$volunteers = $db->query("SELECT u.*, COUNT(a.id) as task_count FROM users u LEFT JOIN assignments a ON u.id = a.volunteer_id WHERE u.role='volunteer' GROUP BY u.id ORDER BY task_count DESC LIMIT 5")->fetch_all(MYSQLI_ASSOC);

// AI Matches (rule-based)
$ai_matches = $db->query("
  SELECT t.id as task_id, t.title as task_title, t.problem_type, t.location as task_loc,
         u.id as vol_id, u.name as vol_name, u.skills, u.location as vol_loc,
         CASE
           WHEN u.skills LIKE CONCAT('%', t.problem_type, '%') THEN 94
           WHEN u.location = t.location THEN 82
           ELSE 70
         END as match_score
  FROM tasks t
  JOIN users u ON u.role='volunteer'
  LEFT JOIN assignments a ON a.task_id = t.id AND a.volunteer_id = u.id
  WHERE t.status='open' AND a.id IS NULL
  ORDER BY match_score DESC, t.urgency DESC
  LIMIT 5
")->fetch_all(MYSQLI_ASSOC);

$urgency_map = [5=>'Critical',4=>'High',3=>'Medium',2=>'Low',1=>'Minimal'];
$urgency_color = [5=>'#FF4757',4=>'#FFA502',3=>'#5352ED',2=>'#00D4AA',1=>'#888'];
?>

<!-- SIDEBAR -->
<div class="sidebar" id="sidebar">
  <div class="sidebar-logo">
    <div class="logo-icon">🎯</div>
    <div class="logo-text">Smart<span>Alloc</span></div>
  </div>

  <div class="nav-section">
    <div class="nav-label">Main</div>
    <a class="nav-item active" href="/smartalloc/pages/admin_dashboard.php"><i class="fas fa-chart-pie"></i> Dashboard</a>
    <a class="nav-item" href="/smartalloc/pages/admin_tasks.php"><i class="fas fa-tasks"></i> Tasks <span class="nav-badge"><?= $stats['open_tasks'] ?></span></a>
    <a class="nav-item" href="#" onclick="showSection('ngos')"><i class="fas fa-building"></i> NGOs</a>
    <a class="nav-item" href="#" onclick="showSection('volunteers')"><i class="fas fa-users"></i> Volunteers</a>
    <a class="nav-item" href="/smartalloc/pages/admin_analytics.php"><i class="fas fa-chart-bar"></i> Analytics</a>
  </div>

  <div class="nav-section">
    <div class="nav-label">System</div>
    <a class="nav-item" href="#"><i class="fas fa-cog"></i> Settings</a>
  </div>

  <div class="sidebar-footer">
    <a class="nav-item" href="/smartalloc/pages/logout.php" style="color: var(--danger)"><i class="fas fa-sign-out-alt"></i> Logout</a>
  </div>
</div>

<!-- MAIN -->
<div class="main-content" id="mainContent">
  <!-- TOP NAV -->
  <div class="topnav">
    <button class="topnav-toggle" onclick="toggleSidebar()" title="Toggle Menu">
      <i class="fas fa-bars"></i>
    </button>
    <div class="topnav-title">Dashboard</div>
    <div class="topnav-actions">
      <button class="notif-btn" onclick="toggleNotifs()" title="Notifications">
        🔔 <?php if($notif_count > 0): ?><span class="notif-badge"><?= $notif_count ?></span><?php endif; ?>
      </button>
      <div class="user-pill" onclick="toggleUserMenu()">
        <div class="user-avatar"><?= strtoupper(substr($user['name'],0,1)) ?></div>
        <div>
          <div class="user-name"><?= htmlspecialchars($user['name']) ?></div>
          <div class="user-role">Administrator</div>
        </div>
      </div>
    </div>
  </div>

  <!-- PAGE CONTENT -->
  <div class="page-content">

    <!-- STAT CARDS -->
    <div class="stat-grid">
      <div class="stat-card" style="--accent-color: #00D4AA">
        <div class="stat-number"><?= $stats['active_tasks'] + $stats['open_tasks'] ?></div>
        <div class="stat-label">Active Tasks</div>
        <div class="stat-icon">📋</div>
      </div>
      <div class="stat-card" style="--accent-color: #FFA502">
        <div class="stat-number"><?= $stats['open_tasks'] ?></div>
        <div class="stat-label">Pending Tasks</div>
        <div class="stat-icon">⏳</div>
      </div>
      <div class="stat-card" style="--accent-color: #2ED573">
        <div class="stat-number"><?= $stats['completed_tasks'] ?></div>
        <div class="stat-label">Completed</div>
        <div class="stat-icon">✅</div>
      </div>
      <div class="stat-card" style="--accent-color: #5352ED">
        <div class="stat-number"><?= $vol_count ?></div>
        <div class="stat-label">Volunteers</div>
        <div class="stat-icon">👥</div>
      </div>
    </div>

    <!-- MAP + QUICK ACTIONS -->
    <div class="grid-2">
      <!-- LIVE TASK MAP -->
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">📍 Live Task Map</div>
          <button class="section-action" onclick="loadMap()">View Full Map</button>
        </div>
        <div style="padding: 16px;">
          <div class="map-container" id="taskMap">
            <div id="mapContent" style="width:100%;height:100%;position:relative;background:linear-gradient(135deg,#0d1117,#161b22);border-radius:8px;overflow:hidden;">
              <!-- Grid lines -->
              <svg style="position:absolute;inset:0;width:100%;height:100%;opacity:0.1" viewBox="0 0 400 280">
                <defs><pattern id="g" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M 40 0 L 0 0 0 40" fill="none" stroke="#00D4AA" stroke-width="0.5"/></pattern></defs>
                <rect width="400" height="280" fill="url(#g)"/>
              </svg>
              <!-- Task dots -->
              <?php foreach($tasks as $i => $t):
                $colors = [5=>'#FF4757',4=>'#FFA502',3=>'#5352ED',2=>'#00D4AA',1=>'#888'];
                $x = 15 + ($i * 13) % 70;
                $y = 20 + ($i * 17) % 60;
                $clr = $colors[$t['urgency']] ?? '#00D4AA';
              ?>
              <div style="position:absolute;left:<?=$x?>%;top:<?=$y?>%;transform:translate(-50%,-50%)">
                <div style="width:14px;height:14px;border-radius:50%;background:<?=$clr?>;border:2px solid white;cursor:pointer;box-shadow:0 0 8px <?=$clr?>"
                     title="<?=htmlspecialchars($t['title'])?> - <?=htmlspecialchars($t['location'])?>"></div>
              </div>
              <?php endforeach; ?>
              <!-- Legend -->
              <div style="position:absolute;bottom:12px;left:12px;display:flex;gap:10px;font-size:11px;">
                <span style="display:flex;align-items:center;gap:4px"><span style="width:8px;height:8px;border-radius:50%;background:#FF4757;display:inline-block"></span>Critical</span>
                <span style="display:flex;align-items:center;gap:4px"><span style="width:8px;height:8px;border-radius:50%;background:#FFA502;display:inline-block"></span>High</span>
                <span style="display:flex;align-items:center;gap:4px"><span style="width:8px;height:8px;border-radius:50%;background:#00D4AA;display:inline-block"></span>Normal</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- QUICK ACTIONS -->
      <div class="section-card">
        <div class="section-header">
          <div class="section-title">⚡ Quick Actions</div>
        </div>
        <div style="padding: 16px;">
          <div class="quick-action" onclick="openModal('taskModal')">
            <div class="qa-icon">➕</div>
            <div><div class="qa-text">New Task</div><div class="qa-sub">Create a new need/task</div></div>
          </div>
          <div class="quick-action" href="/smartalloc/pages/admin_tasks.php">
            <div class="qa-icon">👥</div>
            <div><div class="qa-text">Add Volunteer</div><div class="qa-sub">Register new volunteer</div></div>
          </div>
          <div class="quick-action" onclick="runAIMatch()">
            <div class="qa-icon">🤖</div>
            <div><div class="qa-text">Run AI Matching</div><div class="qa-sub">Auto-assign volunteers</div></div>
          </div>
          <div class="quick-action" href="/smartalloc/pages/admin_analytics.php">
            <div class="qa-icon">📊</div>
            <div><div class="qa-text">View Reports</div><div class="qa-sub">Analytics & insights</div></div>
          </div>
        </div>
      </div>
    </div>

    <!-- RECENT TASKS TABLE -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">📋 Recent Tasks</div>
        <a href="/smartalloc/pages/admin_tasks.php" class="section-action">View All →</a>
      </div>
      <table class="data-table">
        <thead>
          <tr>
            <th>#ID</th>
            <th>Title</th>
            <th>Location</th>
            <th>Type</th>
            <th>Urgency</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach($tasks as $t): ?>
          <tr>
            <td style="color:var(--text-muted)">#<?= $t['id'] ?></td>
            <td><strong><?= htmlspecialchars($t['title']) ?></strong></td>
            <td style="color:var(--text-muted)">📍 <?= htmlspecialchars($t['location']) ?></td>
            <td>
              <?php $type_icons=['food'=>'🍽️','medical'=>'🏥','shelter'=>'🏠','water'=>'💧','education'=>'📚','other'=>'📌']; ?>
              <?= $type_icons[$t['problem_type']] ?? '📌' ?> <?= ucfirst($t['problem_type']) ?>
            </td>
            <td>
              <div class="urgency">
                <?php for($i=1;$i<=5;$i++): ?>
                <div class="urgency-dot <?= $i<=$t['urgency']?'filled':'' ?>"
                     style="<?= $i<=$t['urgency']?'--u-color:'.$urgency_color[$t['urgency']] :''?>"></div>
                <?php endfor; ?>
                <span style="font-size:11px;color:var(--text-muted);margin-left:4px"><?= $t['urgency'] ?>/5</span>
              </div>
            </td>
            <td>
              <?php
                $s=$t['status'];
                $cls=$s==='open'?'badge-open':($s==='in-progress'?'badge-inprogress':'badge-completed');
              ?>
              <span class="badge <?= $cls ?>"><?= ucfirst(str_replace('-',' ',$s)) ?></span>
            </td>
            <td style="display:flex;gap:6px">
              <button class="btn btn-ghost btn-sm" onclick="editTask(<?= htmlspecialchars(json_encode($t)) ?>)">✏️</button>
              <button class="btn btn-danger btn-sm" onclick="deleteTask(<?= $t['id'] ?>)">🗑️</button>
            </td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    </div>

    <!-- AI MATCHING -->
    <div class="section-card">
      <div class="section-header">
        <div class="section-title">🤖 AI-Powered Matching</div>
        <button class="section-action" onclick="runAIMatch()">Run Matching →</button>
      </div>
      <div id="ai-match-list">
        <?php foreach($ai_matches as $m): ?>
        <div class="match-item">
          <div class="match-score"><?= $m['match_score'] ?>%</div>
          <div class="match-info">
            <div class="match-title">🎯 <?= htmlspecialchars($m['task_title']) ?> → <?= htmlspecialchars($m['vol_name']) ?></div>
            <div class="match-sub">📍 <?= htmlspecialchars($m['task_loc']) ?> | Skills: <?= htmlspecialchars($m['skills'] ?? 'General') ?></div>
          </div>
          <button class="btn btn-primary btn-sm" onclick="assignVolunteer(<?= $m['task_id'] ?>, <?= $m['vol_id'] ?>)">
            ASSIGN
          </button>
        </div>
        <?php endforeach; ?>
        <?php if(empty($ai_matches)): ?>
        <div style="padding:24px;text-align:center;color:var(--text-muted)">No pending matches. All tasks are assigned!</div>
        <?php endif; ?>
      </div>
    </div>

  </div><!-- /page-content -->
</div><!-- /main-content -->

<!-- CREATE TASK MODAL -->
<div class="modal-overlay" id="taskModal">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('taskModal')">✕</button>
    <h3>➕ Create New Task</h3>
    <form id="taskForm" onsubmit="createTask(event)">
      <div class="form-g">
        <label>Task Title</label>
        <input type="text" name="title" placeholder="e.g. Food Distribution Drive" required>
      </div>
      <div class="form-row">
        <div class="form-g">
          <label>Problem Type</label>
          <select name="problem_type">
            <option value="food">🍽️ Food</option>
            <option value="medical">🏥 Medical</option>
            <option value="shelter">🏠 Shelter</option>
            <option value="water">💧 Water</option>
            <option value="education">📚 Education</option>
            <option value="other">📌 Other</option>
          </select>
        </div>
        <div class="form-g">
          <label>Urgency (1-5)</label>
          <select name="urgency">
            <option value="5">🔴 5 - Critical</option>
            <option value="4">🟠 4 - High</option>
            <option value="3" selected>🟡 3 - Medium</option>
            <option value="2">🟢 2 - Low</option>
            <option value="1">⚪ 1 - Minimal</option>
          </select>
        </div>
      </div>
      <div class="form-row">
        <div class="form-g">
          <label>Location</label>
          <input type="text" name="location" placeholder="e.g. Downtown Chennai" required>
        </div>
        <div class="form-g">
          <label>Volunteers Needed</label>
          <input type="number" name="volunteers_needed" value="5" min="1">
        </div>
      </div>
      <div class="form-g">
        <label>Description</label>
        <textarea name="description" rows="3" placeholder="Describe the task..."></textarea>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px">
        <button type="button" class="btn btn-ghost" onclick="closeModal('taskModal')">Cancel</button>
        <button type="submit" class="btn btn-primary">Create Task</button>
      </div>
    </form>
  </div>
</div>

<!-- TOAST -->
<div class="toast" id="toast">✅ <span id="toastMsg">Done!</span></div>

<!-- OVERLAY for mobile sidebar -->
<div id="sidebarOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99" onclick="toggleSidebar()"></div>

<script>
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const mc = document.getElementById('mainContent');
  const ov = document.getElementById('sidebarOverlay');
  if(window.innerWidth <= 768) {
    sb.classList.toggle('mobile-open');
    ov.style.display = sb.classList.contains('mobile-open') ? 'block' : 'none';
  } else {
    sb.classList.toggle('collapsed');
    mc.classList.toggle('expanded');
  }
}

function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }

function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  t.style.background = type==='error' ? 'rgba(255,71,87,0.15)' : 'rgba(0,212,170,0.15)';
  t.style.color = type==='error' ? '#FF4757' : '#00D4AA';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

function createTask(e) {
  e.preventDefault();
  const fd = new FormData(e.target);
  fd.append('action', 'create');
  fetch('/smartalloc/api/tasks.php', { method: 'POST', body: fd })
    .then(r => r.json())
    .then(d => {
      if(d.success) { showToast('Task created successfully!'); closeModal('taskModal'); location.reload(); }
      else showToast(d.error || 'Failed to create task', 'error');
    });
}

function deleteTask(id) {
  if(!confirm('Delete this task?')) return;
  fetch('/smartalloc/api/tasks.php', { method: 'POST', body: new URLSearchParams({action:'delete',id}) })
    .then(r => r.json())
    .then(d => { if(d.success) { showToast('Task deleted'); location.reload(); } });
}

function editTask(t) {
  // For demo: show a pre-filled modal
  showToast('Edit feature: Open admin_tasks.php for full editing');
}

function assignVolunteer(taskId, volId) {
  fetch('/smartalloc/api/tasks.php', { method: 'POST', body: new URLSearchParams({action:'assign', task_id:taskId, volunteer_id:volId}) })
    .then(r => r.json())
    .then(d => { if(d.success) { showToast('Volunteer assigned!'); location.reload(); } else showToast(d.error, 'error'); });
}

function runAIMatch() {
  showToast('🤖 AI matching engine running...');
  setTimeout(() => { showToast('Matches updated! Scroll down to see results.'); location.reload(); }, 1500);
}

function loadMap() {
  window.open('https://www.google.com/maps/search/NGO+volunteer+tasks+Chennai', '_blank');
}

function toggleNotifs() { showToast('📬 <?= $notif_count ?> unread notifications'); }
function toggleUserMenu() { showToast('Logged in as: <?= $user['name'] ?> (Admin)'); }
</script>
</body>
</html>
