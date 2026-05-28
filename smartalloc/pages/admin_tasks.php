<?php
// pages/admin_tasks.php
session_start();
require_once '../config/db.php';
requireLogin('admin');
$pageTitle = 'Manage Tasks';
$activePage = 'tasks';
include '../partials/admin_layout.php';

$tasks = $db->query("SELECT t.*, u.name as creator_name FROM tasks t LEFT JOIN users u ON t.created_by = u.id ORDER BY t.urgency DESC, t.created_at DESC")->fetch_all(MYSQLI_ASSOC);
$volunteers = $db->query("SELECT id, name, skills, location FROM users WHERE role='volunteer' AND status='active'")->fetch_all(MYSQLI_ASSOC);
$urgency_color = [5=>'#FF4757',4=>'#FFA502',3=>'#5352ED',2=>'#00D4AA',1=>'#888'];
?>
<div class="sidebar" id="sidebar">
  <div class="sidebar-logo"><div class="logo-icon">🎯</div><div class="logo-text">Smart<span>Alloc</span></div></div>
  <div class="nav-section">
    <div class="nav-label">Main</div>
    <a class="nav-item" href="/smartalloc/pages/admin_dashboard.php"><i class="fas fa-chart-pie"></i> Dashboard</a>
    <a class="nav-item active" href="/smartalloc/pages/admin_tasks.php"><i class="fas fa-tasks"></i> Tasks</a>
    <a class="nav-item" href="#"><i class="fas fa-building"></i> NGOs</a>
    <a class="nav-item" href="#"><i class="fas fa-users"></i> Volunteers</a>
    <a class="nav-item" href="/smartalloc/pages/admin_analytics.php"><i class="fas fa-chart-bar"></i> Analytics</a>
  </div>
  <div class="sidebar-footer">
    <a class="nav-item" href="/smartalloc/pages/logout.php" style="color:var(--danger)"><i class="fas fa-sign-out-alt"></i> Logout</a>
  </div>
</div>

<div class="main-content" id="mainContent">
  <div class="topnav">
    <button class="topnav-toggle" onclick="toggleSidebar()"><i class="fas fa-bars"></i></button>
    <div class="topnav-title">📋 Task Management</div>
    <div class="topnav-actions">
      <button class="btn btn-primary" onclick="openModal('taskModal')">+ New Task</button>
      <div class="user-pill" onclick="toggleUserMenu()">
        <div class="user-avatar"><?= strtoupper(substr($user['name'],0,1)) ?></div>
        <div><div class="user-name"><?= htmlspecialchars($user['name']) ?></div><div class="user-role">Admin</div></div>
      </div>
    </div>
  </div>

  <div class="page-content">
    <!-- FILTERS -->
    <div class="section-card" style="margin-bottom:20px">
      <div style="padding:16px;display:flex;gap:12px;flex-wrap:wrap;align-items:center">
        <input type="text" id="searchBox" placeholder="🔍 Search tasks..." oninput="filterTasks()"
               style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 14px;color:white;font-family:inherit;font-size:14px;outline:none;flex:1;min-width:200px">
        <select id="filterStatus" onchange="filterTasks()" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 14px;color:white;font-family:inherit;font-size:14px;outline:none">
          <option value="">All Status</option>
          <option value="open">Open</option>
          <option value="in-progress">In Progress</option>
          <option value="completed">Completed</option>
        </select>
        <select id="filterType" onchange="filterTasks()" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 14px;color:white;font-family:inherit;font-size:14px;outline:none">
          <option value="">All Types</option>
          <option value="food">Food</option>
          <option value="medical">Medical</option>
          <option value="shelter">Shelter</option>
          <option value="water">Water</option>
          <option value="education">Education</option>
        </select>
        <select id="filterUrgency" onchange="filterTasks()" style="background:rgba(255,255,255,0.05);border:1px solid rgba(255,255,255,0.1);border-radius:10px;padding:10px 14px;color:white;font-family:inherit;font-size:14px;outline:none">
          <option value="">All Urgency</option>
          <option value="5">🔴 Critical (5)</option>
          <option value="4">🟠 High (4)</option>
          <option value="3">🟡 Medium (3)</option>
          <option value="2">🟢 Low (2)</option>
          <option value="1">⚪ Minimal (1)</option>
        </select>
      </div>
    </div>

    <!-- TASK CARDS GRID -->
    <div id="tasksGrid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:16px">
      <?php foreach($tasks as $t):
        $clr = $urgency_color[$t['urgency']] ?? '#888';
        $type_icons=['food'=>'🍽️','medical'=>'🏥','shelter'=>'🏠','water'=>'💧','education'=>'📚','other'=>'📌'];
      ?>
      <div class="task-card section-card" data-status="<?=$t['status']?>" data-type="<?=$t['problem_type']?>" data-urgency="<?=$t['urgency']?>" data-title="<?=strtolower(htmlspecialchars($t['title']))?>" style="margin-bottom:0;border-left:3px solid <?=$clr?>">
        <div style="padding:18px">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px">
            <div>
              <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px">#<?=$t['id']?> • <?=$type_icons[$t['problem_type']]?> <?=ucfirst($t['problem_type'])?></div>
              <div style="font-weight:700;font-size:16px"><?=htmlspecialchars($t['title'])?></div>
            </div>
            <div style="display:flex;flex-direction:column;align-items:flex-end;gap:6px">
              <span class="badge <?=$t['status']==='open'?'badge-open':($t['status']==='in-progress'?'badge-inprogress':'badge-completed')?>"><?=ucfirst(str_replace('-',' ',$t['status']))?></span>
              <span style="font-size:13px;font-weight:700;color:<?=$clr?>">⚡ <?=$t['urgency']?>/5</span>
            </div>
          </div>

          <div style="font-size:13px;color:var(--text-muted);margin-bottom:12px">
            📍 <?=htmlspecialchars($t['location'])?>
            <?php if($t['description']): ?><br><span style="margin-top:6px;display:block"><?=htmlspecialchars(substr($t['description'],0,80))?>...</span><?php endif; ?>
          </div>

          <div style="display:flex;justify-content:space-between;align-items:center;padding-top:12px;border-top:1px solid rgba(255,255,255,0.06)">
            <div style="font-size:12px;color:var(--text-muted)">
              👥 <?=$t['volunteers_needed']?> needed •
              🕒 <?=date('M d', strtotime($t['created_at']))?>
            </div>
            <div style="display:flex;gap:8px">
              <button class="btn btn-ghost btn-sm" onclick="openAssign(<?=$t['id']?>, '<?=addslashes($t['title'])?>')">👤 Assign</button>
              <button class="btn btn-ghost btn-sm" onclick="editTask(<?=htmlspecialchars(json_encode($t))?>)">✏️</button>
              <button class="btn btn-danger btn-sm" onclick="deleteTask(<?=$t['id']?>)">🗑️</button>
            </div>
          </div>
        </div>
      </div>
      <?php endforeach; ?>
    </div>
  </div>
</div>

<!-- CREATE TASK MODAL -->
<div class="modal-overlay" id="taskModal">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('taskModal')">✕</button>
    <h3 id="modalTitle">➕ Create New Task</h3>
    <form id="taskForm" onsubmit="submitTask(event)">
      <input type="hidden" name="action" id="formAction" value="create">
      <input type="hidden" name="id" id="formTaskId">
      <div class="form-g"><label>Task Title</label><input type="text" name="title" id="formTitle" placeholder="e.g. Food Distribution" required></div>
      <div class="form-row">
        <div class="form-g"><label>Type</label><select name="problem_type" id="formType"><option value="food">🍽️ Food</option><option value="medical">🏥 Medical</option><option value="shelter">🏠 Shelter</option><option value="water">💧 Water</option><option value="education">📚 Education</option><option value="other">Other</option></select></div>
        <div class="form-g"><label>Urgency</label><select name="urgency" id="formUrgency"><option value="5">🔴 Critical</option><option value="4">🟠 High</option><option value="3" selected>🟡 Medium</option><option value="2">🟢 Low</option><option value="1">⚪ Minimal</option></select></div>
      </div>
      <div class="form-row">
        <div class="form-g"><label>Location</label><input type="text" name="location" id="formLocation" placeholder="City/Area" required></div>
        <div class="form-g"><label>Volunteers Needed</label><input type="number" name="volunteers_needed" id="formVolNeeded" value="5" min="1"></div>
      </div>
      <div class="form-g"><label>Description</label><textarea name="description" id="formDesc" rows="3" placeholder="Describe the task..."></textarea></div>
      <div style="display:flex;gap:10px;justify-content:flex-end;margin-top:8px">
        <button type="button" class="btn btn-ghost" onclick="closeModal('taskModal')">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Task</button>
      </div>
    </form>
  </div>
</div>

<!-- ASSIGN MODAL -->
<div class="modal-overlay" id="assignModal">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('assignModal')">✕</button>
    <h3 id="assignTitle">👤 Assign Volunteer</h3>
    <form onsubmit="doAssign(event)">
      <input type="hidden" name="action" value="assign">
      <input type="hidden" name="task_id" id="assignTaskId">
      <div class="form-g">
        <label>Select Volunteer</label>
        <select name="volunteer_id" required>
          <option value="">-- Select --</option>
          <?php foreach($volunteers as $v): ?>
          <option value="<?=$v['id']?>"><?=htmlspecialchars($v['name'])?> | <?=htmlspecialchars($v['skills'])?> | <?=htmlspecialchars($v['location'])?></option>
          <?php endforeach; ?>
        </select>
      </div>
      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button type="button" class="btn btn-ghost" onclick="closeModal('assignModal')">Cancel</button>
        <button type="submit" class="btn btn-primary">Assign</button>
      </div>
    </form>
  </div>
</div>

<div class="toast" id="toast">✅ <span id="toastMsg">Done!</span></div>
<div id="sidebarOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:99" onclick="toggleSidebar()"></div>

<script>
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const mc = document.getElementById('mainContent');
  const ov = document.getElementById('sidebarOverlay');
  if(window.innerWidth <= 768) { sb.classList.toggle('mobile-open'); ov.style.display = sb.classList.contains('mobile-open') ? 'block' : 'none'; }
  else { sb.classList.toggle('collapsed'); mc.classList.toggle('expanded'); }
}
function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  t.style.color = type==='error' ? '#FF4757' : '#00D4AA';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}
function toggleUserMenu() { showToast('Logged in as: <?= $user['name'] ?> (Admin)'); }

function filterTasks() {
  const search = document.getElementById('searchBox').value.toLowerCase();
  const status = document.getElementById('filterStatus').value;
  const type = document.getElementById('filterType').value;
  const urgency = document.getElementById('filterUrgency').value;
  document.querySelectorAll('.task-card').forEach(card => {
    const matchSearch = !search || card.dataset.title.includes(search);
    const matchStatus = !status || card.dataset.status === status;
    const matchType = !type || card.dataset.type === type;
    const matchUrgency = !urgency || card.dataset.urgency === urgency;
    card.style.display = (matchSearch && matchStatus && matchType && matchUrgency) ? '' : 'none';
  });
}

function editTask(t) {
  document.getElementById('modalTitle').textContent = '✏️ Edit Task';
  document.getElementById('formAction').value = 'update';
  document.getElementById('formTaskId').value = t.id;
  document.getElementById('formTitle').value = t.title;
  document.getElementById('formType').value = t.problem_type;
  document.getElementById('formUrgency').value = t.urgency;
  document.getElementById('formLocation').value = t.location;
  document.getElementById('formVolNeeded').value = t.volunteers_needed;
  document.getElementById('formDesc').value = t.description || '';
  openModal('taskModal');
}

function submitTask(e) {
  e.preventDefault();
  const fd = new FormData(e.target);
  fetch('/smartalloc/api/tasks.php', { method:'POST', body:fd })
    .then(r => r.json())
    .then(d => {
      if(d.success) { showToast('Task saved!'); closeModal('taskModal'); setTimeout(() => location.reload(), 800); }
      else showToast(d.error || 'Error', 'error');
    });
}

function deleteTask(id) {
  if(!confirm('Delete this task? This cannot be undone.')) return;
  fetch('/smartalloc/api/tasks.php', { method:'POST', body: new URLSearchParams({action:'delete', id}) })
    .then(r => r.json())
    .then(d => { if(d.success) { showToast('Deleted!'); setTimeout(() => location.reload(), 600); } });
}

function openAssign(id, title) {
  document.getElementById('assignTitle').textContent = '👤 Assign: ' + title;
  document.getElementById('assignTaskId').value = id;
  openModal('assignModal');
}

function doAssign(e) {
  e.preventDefault();
  const fd = new FormData(e.target);
  fetch('/smartalloc/api/tasks.php', { method:'POST', body:fd })
    .then(r => r.json())
    .then(d => {
      if(d.success) { showToast('Volunteer assigned!'); closeModal('assignModal'); setTimeout(() => location.reload(), 800); }
      else showToast(d.error || 'Already assigned', 'error');
    });
}
</script>
</body>
</html>
