<?php
// pages/ngo_dashboard.php
session_start();
require_once '../config/db.php';
requireLogin('ngo');

$user = $_SESSION['user'];
$ngo = $_SESSION['ngo'] ?? null;
$db = getDB();

// Load NGO data
if(!$ngo) {
  $nq = $db->prepare("SELECT * FROM ngos WHERE user_id = ?");
  $nq->bind_param('i', $user['id']);
  $nq->execute();
  $ngo = $nq->get_result()->fetch_assoc();
  $_SESSION['ngo'] = $ngo;
}

// NGO's tasks
$tq = $db->prepare("SELECT * FROM tasks WHERE created_by = ? OR ngo_id = ? ORDER BY urgency DESC, created_at DESC");
$tq->bind_param('ii', $user['id'], $ngo['id'] ?? 0);
$tq->execute();
$my_tasks = $tq->get_result()->fetch_all(MYSQLI_ASSOC);

$active_count = count(array_filter($my_tasks, fn($t)=>$t['status']==='open'));
$completed_count = count(array_filter($my_tasks, fn($t)=>$t['status']==='completed'));

// Assigned volunteers
$vq = $db->prepare("SELECT DISTINCT u.*, a.status as assign_status, t.title as task_title FROM users u JOIN assignments a ON a.volunteer_id = u.id JOIN tasks t ON a.task_id = t.id WHERE (t.created_by = ? OR t.ngo_id = ?) AND a.status IN ('accepted','in-progress') ORDER BY a.assigned_at DESC LIMIT 10");
$vq->bind_param('ii', $user['id'], $ngo['id'] ?? 0);
$vq->execute();
$volunteers = $vq->get_result()->fetch_all(MYSQLI_ASSOC);

// Notifications
$notifQ = $db->prepare("SELECT * FROM notifications WHERE user_id = ? AND is_read=0 ORDER BY created_at DESC LIMIT 5");
$notifQ->bind_param('i', $user['id']);
$notifQ->execute();
$notifs = $notifQ->get_result()->fetch_all(MYSQLI_ASSOC);
$notif_count = count($notifs);

$urgency_color = [5=>'#FF4757',4=>'#FFA502',3=>'#5352ED',2=>'#00D4AA',1=>'#888'];
$type_icons=['food'=>'🍽️','medical'=>'🏥','shelter'=>'🏠','water'=>'💧','education'=>'📚','other'=>'📌'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>NGO Dashboard - SmartAlloc</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
:root { --primary:#00D4AA;--bg:#0A0A1A;--card-bg:rgba(255,255,255,0.03);--border:rgba(255,255,255,0.08);--text:#fff;--text-muted:rgba(255,255,255,0.45);--glow:rgba(0,212,170,0.2);--danger:#FF4757;--warning:#FFA502;--success:#2ED573; }
*{margin:0;padding:0;box-sizing:border-box;}
body{background:var(--bg);font-family:'Space Grotesk',sans-serif;color:var(--text);min-height:100vh;padding-bottom:80px;}

.topnav{background:rgba(10,10,26,0.95);backdrop-filter:blur(20px);border-bottom:1px solid var(--border);padding:0 20px;height:60px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:50;}
.logo{font-family:'Syne',sans-serif;font-size:18px;font-weight:800;flex:1;}
.logo span{color:var(--primary);}
.icon-btn{background:rgba(255,255,255,0.06);border:1px solid var(--border);border-radius:10px;padding:8px 12px;color:var(--text);cursor:pointer;font-size:16px;position:relative;transition:all 0.2s;}
.badge-dot{position:absolute;top:-5px;right:-5px;background:var(--danger);color:white;font-size:9px;font-weight:700;width:16px;height:16px;border-radius:50%;display:flex;align-items:center;justify-content:center;}
.ngo-pill{display:flex;align-items:center;gap:8px;background:rgba(255,255,255,0.05);border:1px solid var(--border);border-radius:30px;padding:5px 12px 5px 5px;cursor:pointer;transition:all 0.2s;}
.ngo-pill:hover{background:rgba(255,255,255,0.08);}
.ngo-logo{width:32px;height:32px;border-radius:50%;background:linear-gradient(135deg,#6C63FF,#FF6B35);display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:700;color:white;}
.ngo-name{font-size:13px;font-weight:600;}
.ngo-role{font-size:10px;color:var(--primary);}

.page{max-width:900px;margin:0 auto;padding:20px 16px;}

.hero{background:linear-gradient(135deg,rgba(108,99,255,0.1),rgba(255,107,53,0.05));border:1px solid rgba(108,99,255,0.2);border-radius:20px;padding:24px;margin-bottom:20px;}
.hero-top{display:flex;align-items:center;gap:16px;margin-bottom:16px;}
.hero-org-logo{width:56px;height:56px;border-radius:16px;background:linear-gradient(135deg,#6C63FF,#FF6B35);display:flex;align-items:center;justify-content:center;font-size:24px;}
.hero h2{font-family:'Syne',sans-serif;font-size:20px;font-weight:800;}
.hero p{color:var(--text-muted);font-size:13px;margin-top:4px;}
.verified-badge{display:inline-flex;align-items:center;gap:4px;background:rgba(0,212,170,0.1);border:1px solid rgba(0,212,170,0.2);border-radius:20px;padding:3px 10px;font-size:11px;color:var(--primary);margin-top:6px;}
.stat-pills{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;}
.stat-pill{background:rgba(255,255,255,0.05);border:1px solid var(--border);border-radius:12px;padding:14px;text-align:center;}
.stat-pill-num{font-family:'Syne',sans-serif;font-size:26px;font-weight:800;color:var(--primary);display:block;}
.stat-pill-label{font-size:11px;color:var(--text-muted);}

.section-card{background:var(--card-bg);border:1px solid var(--border);border-radius:16px;overflow:hidden;margin-bottom:16px;}
.section-header{padding:16px 18px;border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;}
.section-title{font-size:14px;font-weight:700;}
.section-action{font-size:12px;color:var(--primary);background:rgba(0,212,170,0.08);border:1px solid rgba(0,212,170,0.15);padding:5px 12px;border-radius:8px;cursor:pointer;font-family:inherit;transition:all 0.2s;}

.task-item{padding:16px 18px;border-bottom:1px solid rgba(255,255,255,0.04);}
.task-item:last-child{border-bottom:none;}
.task-top{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:8px;}
.task-name{font-weight:700;font-size:15px;}
.task-meta{font-size:12px;color:var(--text-muted);margin-top:4px;}
.task-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;}
.btn{padding:8px 14px;border-radius:8px;border:none;cursor:pointer;font-family:inherit;font-size:12px;font-weight:600;transition:all 0.2s;display:inline-flex;align-items:center;gap:5px;}
.btn-primary{background:var(--primary);color:#0A0A1A;}
.btn-primary:hover{filter:brightness(1.1);}
.btn-ghost{background:rgba(255,255,255,0.06);color:var(--text);border:1px solid var(--border);}
.btn-ghost:hover{background:rgba(255,255,255,0.1);}
.btn-danger{background:rgba(255,71,87,0.1);color:var(--danger);border:1px solid rgba(255,71,87,0.2);}

.badge{padding:3px 9px;border-radius:20px;font-size:10px;font-weight:700;text-transform:uppercase;}
.badge-open{background:rgba(0,212,170,0.15);color:var(--primary);}
.badge-inprogress{background:rgba(255,165,2,0.15);color:var(--warning);}
.badge-completed{background:rgba(46,213,115,0.15);color:var(--success);}

.quick-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;padding:16px;}
.qa{display:flex;flex-direction:column;align-items:center;gap:8px;padding:20px 12px;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:12px;cursor:pointer;transition:all 0.2s;text-align:center;}
.qa:hover{background:rgba(0,212,170,0.05);border-color:rgba(0,212,170,0.2);}
.qa-icon{font-size:28px;}
.qa-label{font-size:12px;font-weight:600;}

.vol-item{display:flex;align-items:center;gap:14px;padding:14px 18px;border-bottom:1px solid rgba(255,255,255,0.04);}
.vol-item:last-child{border-bottom:none;}
.vol-avatar{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,var(--primary),#6C63FF);display:flex;align-items:center;justify-content:center;font-size:15px;font-weight:700;color:#0A0A1A;flex-shrink:0;}
.vol-info{flex:1;}
.vol-name{font-weight:600;font-size:14px;}
.vol-meta{font-size:12px;color:var(--text-muted);margin-top:3px;}
.status-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0;}
.active-dot{background:var(--success);box-shadow:0 0 6px var(--success);}
.idle-dot{background:var(--text-muted);}
.vol-actions{display:flex;gap:6px;}

.modal-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.7);backdrop-filter:blur(8px);z-index:1000;display:none;align-items:center;justify-content:center;padding:16px;}
.modal-overlay.open{display:flex;}
.modal{background:#131325;border:1px solid var(--border);border-radius:20px;padding:28px;width:100%;max-width:500px;animation:modalIn 0.3s ease-out;max-height:90vh;overflow-y:auto;}
@keyframes modalIn{from{opacity:0;transform:scale(0.95)}to{opacity:1;transform:scale(1)}}
.modal h3{font-family:'Syne',sans-serif;font-size:20px;font-weight:800;margin-bottom:16px;}
.modal-close{float:right;background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer;}
.form-g{margin-bottom:14px;}
.form-g label{display:block;font-size:11px;color:var(--text-muted);margin-bottom:6px;text-transform:uppercase;letter-spacing:0.5px;}
.form-g input,.form-g select,.form-g textarea{width:100%;background:rgba(255,255,255,0.05);border:1px solid var(--border);border-radius:10px;padding:11px 13px;color:#fff;font-size:14px;font-family:inherit;outline:none;}
.form-g input:focus,.form-g select:focus{border-color:var(--primary);}
.form-g select option{background:#131325;}

/* Profile panel */
.profile-panel{position:fixed;top:0;right:0;bottom:0;width:320px;background:#0F0F23;border-left:1px solid var(--border);z-index:200;transform:translateX(100%);transition:transform 0.3s ease;padding:24px;overflow-y:auto;}
.profile-panel.open{transform:translateX(0);}
.profile-overlay{position:fixed;inset:0;background:rgba(0,0,0,0.5);z-index:199;display:none;}
.profile-overlay.open{display:block;}

.notif-panel{position:fixed;top:68px;right:20px;width:300px;background:#0F0F23;border:1px solid var(--border);border-radius:16px;z-index:200;padding:16px;display:none;box-shadow:0 20px 60px rgba(0,0,0,0.5);}
.notif-panel.open{display:block;animation:modalIn 0.2s ease;}
.notif-item{padding:10px;border-bottom:1px solid rgba(255,255,255,0.05);font-size:13px;}

.bottom-nav{position:fixed;bottom:0;left:0;right:0;background:rgba(10,10,26,0.95);backdrop-filter:blur(20px);border-top:1px solid var(--border);display:flex;justify-content:space-around;padding:8px 0 12px;z-index:50;}
.nav-tab{display:flex;flex-direction:column;align-items:center;gap:4px;color:var(--text-muted);font-size:10px;font-weight:500;cursor:pointer;padding:6px 12px;border-radius:10px;transition:all 0.2s;text-decoration:none;}
.nav-tab.active{color:var(--primary);}
.nav-tab i{font-size:18px;}

.toast{position:fixed;bottom:88px;left:50%;transform:translateX(-50%);background:rgba(0,212,170,0.15);border:1px solid rgba(0,212,170,0.3);border-radius:12px;padding:12px 20px;color:var(--primary);font-size:13px;z-index:9999;display:none;white-space:nowrap;}
.toast.show{display:block;}
</style>
</head>
<body>

<!-- TOP NAV -->
<div class="topnav">
  <div class="logo">Smart<span>Alloc</span></div>
  <button class="icon-btn" onclick="toggleNotifs()">
    🔔 <?php if($notif_count>0): ?><span class="badge-dot"><?=$notif_count?></span><?php endif; ?>
  </button>
  <div class="ngo-pill" onclick="openProfile()">
    <div class="ngo-logo">🏢</div>
    <div>
      <div class="ngo-name"><?=htmlspecialchars($ngo['org_name'] ?? $user['name'])?></div>
      <div class="ngo-role">NGO <?=$ngo && $ngo['verified'] ? '✓' : ''?></div>
    </div>
  </div>
</div>

<div class="notif-panel" id="notifPanel">
  <div style="font-weight:700;margin-bottom:12px;font-size:14px">🔔 Notifications</div>
  <?php foreach($notifs as $n): ?>
  <div class="notif-item">📌 <?=htmlspecialchars($n['message'])?><div style="font-size:11px;color:var(--text-muted);margin-top:3px"><?=date('M d',strtotime($n['created_at']))?></div></div>
  <?php endforeach; ?>
  <?php if(empty($notifs)): ?><div class="notif-item" style="color:var(--text-muted)">No new notifications</div><?php endif; ?>
</div>

<div class="page">
  <!-- HERO -->
  <div class="hero">
    <div class="hero-top">
      <div class="hero-org-logo">🏢</div>
      <div>
        <h2>Welcome, <?=htmlspecialchars($ngo['org_name'] ?? $user['name'])?>!</h2>
        <p>Manage your requests and track volunteers</p>
        <?php if($ngo && $ngo['verified']): ?>
        <div class="verified-badge">✓ Verified NGO</div>
        <?php endif; ?>
      </div>
    </div>
    <div class="stat-pills">
      <div class="stat-pill"><span class="stat-pill-num"><?=$active_count?></span><span class="stat-pill-label">Active Requests</span></div>
      <div class="stat-pill"><span class="stat-pill-num"><?=count($volunteers)?></span><span class="stat-pill-label">Assigned Volunteers</span></div>
      <div class="stat-pill"><span class="stat-pill-num"><?=$completed_count?></span><span class="stat-pill-label">Completed</span></div>
    </div>
  </div>

  <!-- ACTIVE REQUESTS -->
  <div class="section-card">
    <div class="section-header">
      <div class="section-title">📋 Your Active Requests</div>
      <button class="section-action" onclick="location.reload()">↺ Refresh</button>
    </div>
    <?php $active_tasks = array_filter($my_tasks, fn($t)=>$t['status']!=='completed'); ?>
    <?php foreach($active_tasks as $t):
      $clr = $urgency_color[$t['urgency']];
    ?>
    <div class="task-item" style="border-left:3px solid <?=$clr?>">
      <div class="task-top">
        <div>
          <div class="task-name"><?=$type_icons[$t['problem_type']]?> <?=htmlspecialchars($t['title'])?></div>
          <div class="task-meta">📍 <?=htmlspecialchars($t['location'])?> • Urgency <?=$t['urgency']?>/5</div>
        </div>
        <span class="badge <?=$t['status']==='open'?'badge-open':'badge-inprogress'?>"><?=ucfirst(str_replace('-',' ',$t['status']))?></span>
      </div>
      <?php
        $va = $db->prepare("SELECT COUNT(*) as c FROM assignments WHERE task_id = ?");
        $va->bind_param('i', $t['id']); $va->execute();
        $assigned = $va->get_result()->fetch_assoc()['c'];
      ?>
      <div style="font-size:13px;color:var(--text-muted)">👥 <?=$assigned?>/<?=$t['volunteers_needed']?> volunteers assigned</div>
      <div class="task-actions">
        <button class="btn btn-ghost" onclick="showToast('Task details: '+<?=json_encode($t['title'])?>)">👁️ View Details</button>
        <button class="btn btn-primary" onclick="openModal('requestModal')">+ Request More Help</button>
        <button class="btn btn-danger" onclick="deleteTask(<?=$t['id']?>)">🗑️ Remove</button>
      </div>
    </div>
    <?php endforeach; ?>
    <?php if(empty($active_tasks)): ?>
    <div style="padding:24px;text-align:center;color:var(--text-muted)">No active requests. Create one!</div>
    <?php endif; ?>
  </div>

  <!-- QUICK ACTIONS -->
  <div class="section-card">
    <div class="section-header"><div class="section-title">⚡ Quick Actions</div></div>
    <div class="quick-grid">
      <div class="qa" onclick="openModal('requestModal')"><div class="qa-icon">📝</div><div class="qa-label">Request New Help</div></div>
      <div class="qa" onclick="document.querySelector('.section-card:last-of-type').scrollIntoView({behavior:'smooth'})"><div class="qa-icon">👥</div><div class="qa-label">View Volunteers</div></div>
      <div class="qa" onclick="window.location.href='/smartalloc/pages/admin_analytics.php'"><div class="qa-icon">📊</div><div class="qa-label">View Reports</div></div>
    </div>
  </div>

  <!-- ASSIGNED VOLUNTEERS -->
  <div class="section-card">
    <div class="section-header"><div class="section-title">👥 Assigned Volunteers</div></div>
    <?php foreach($volunteers as $v): ?>
    <div class="vol-item">
      <div class="vol-avatar"><?=strtoupper(substr($v['name'],0,1))?></div>
      <div class="vol-info">
        <div class="vol-name"><?=htmlspecialchars($v['name'])?></div>
        <div class="vol-meta">🛠️ <?=htmlspecialchars($v['skills'] ?? 'General')?> • 📋 <?=htmlspecialchars($v['task_title'])?></div>
      </div>
      <div class="status-dot <?=$v['assign_status']==='in-progress'?'active-dot':'idle-dot'?>"></div>
      <div class="vol-actions">
        <button class="btn btn-ghost btn-sm" onclick="showToast('Chat feature coming soon!')" style="padding:6px 10px;font-size:11px">💬</button>
        <button class="btn btn-ghost btn-sm" onclick="window.open('https://maps.google.com/?q='+encodeURIComponent('<?=addslashes($v['location'])?>'), '_blank')" style="padding:6px 10px;font-size:11px">📍</button>
      </div>
    </div>
    <?php endforeach; ?>
    <?php if(empty($volunteers)): ?>
    <div style="padding:24px;text-align:center;color:var(--text-muted)">No volunteers assigned yet.</div>
    <?php endif; ?>
  </div>
</div>

<!-- REQUEST HELP MODAL -->
<div class="modal-overlay" id="requestModal">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('requestModal')">✕</button>
    <h3>📝 Request Volunteer Help</h3>
    <form onsubmit="submitRequest(event)">
      <div class="form-g"><label>What help do you need?</label><input type="text" name="title" placeholder="e.g. Medical camp volunteers needed" required></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div class="form-g"><label>Type</label><select name="problem_type"><option value="food">🍽️ Food</option><option value="medical">🏥 Medical</option><option value="shelter">🏠 Shelter</option><option value="water">💧 Water</option><option value="education">📚 Education</option><option value="other">Other</option></select></div>
        <div class="form-g"><label>Urgency</label><select name="urgency"><option value="5">🔴 Critical</option><option value="4">🟠 High</option><option value="3" selected>🟡 Medium</option><option value="2">🟢 Low</option></select></div>
      </div>
      <div class="form-g"><label>Location</label><input type="text" name="location" placeholder="Where is help needed?" required></div>
      <div class="form-g"><label>Volunteers Needed</label><input type="number" name="volunteers_needed" value="5" min="1"></div>
      <div class="form-g"><label>Description</label><textarea name="description" rows="3" placeholder="Describe what volunteers should do..."></textarea></div>
      <div style="display:flex;gap:10px;justify-content:flex-end">
        <button type="button" class="btn btn-ghost" onclick="closeModal('requestModal')">Cancel</button>
        <button type="submit" class="btn btn-primary">Submit Request</button>
      </div>
    </form>
  </div>
</div>

<!-- PROFILE PANEL -->
<div class="profile-overlay" id="profileOverlay" onclick="closeProfile()"></div>
<div class="profile-panel" id="profilePanel">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
    <h3 style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800">Organisation Details</h3>
    <button onclick="closeProfile()" style="background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer">✕</button>
  </div>
  <div style="text-align:center;margin-bottom:24px">
    <div style="width:72px;height:72px;border-radius:20px;background:linear-gradient(135deg,#6C63FF,#FF6B35);display:flex;align-items:center;justify-content:center;font-size:32px;margin:0 auto 12px">🏢</div>
    <div style="font-weight:700;font-size:18px"><?=htmlspecialchars($ngo['org_name'] ?? $user['name'])?></div>
    <?php if($ngo && $ngo['verified']): ?><div style="color:var(--primary);font-size:13px;margin-top:4px">✓ Verified NGO</div><?php endif; ?>
  </div>
  <?php $details = [
    ['📧 Contact Email', $user['email']],
    ['📞 Phone', $user['phone'] ?: 'Not set'],
    ['🏢 Organisation', $ngo['org_name'] ?? 'Not set'],
    ['🏷️ Type', $ngo['org_type'] ?? 'Not set'],
    ['📋 Reg. No.', $ngo['registration_no'] ?? 'Not set'],
    ['📍 Address', $ngo['address'] ?? 'Not set'],
  ]; ?>
  <?php foreach($details as [$label, $val]): ?>
  <div style="padding:12px;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:10px;margin-bottom:8px">
    <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px"><?=$label?></div>
    <div style="font-size:13px;font-weight:600"><?=htmlspecialchars($val)?></div>
  </div>
  <?php endforeach; ?>
  <a href="/smartalloc/pages/logout.php" class="btn btn-danger" style="width:100%;justify-content:center;margin-top:20px">🚪 Logout</a>
</div>

<div class="bottom-nav">
  <a href="/smartalloc/pages/ngo_dashboard.php" class="nav-tab active"><i class="fas fa-home"></i>Home</a>
  <a href="#" class="nav-tab" onclick="document.querySelectorAll('.section-card')[0].scrollIntoView({behavior:'smooth'})"><i class="fas fa-clipboard-list"></i>Requests</a>
  <a href="#" class="nav-tab" onclick="document.querySelector('.section-card:last-of-type').scrollIntoView({behavior:'smooth'})"><i class="fas fa-users"></i>Volunteers</a>
  <a href="/smartalloc/pages/admin_analytics.php" class="nav-tab"><i class="fas fa-chart-bar"></i>Reports</a>
  <a href="/smartalloc/pages/logout.php" class="nav-tab"><i class="fas fa-sign-out-alt"></i>Logout</a>
</div>

<div class="toast" id="toast"><span id="toastMsg"></span></div>

<script>
function openModal(id){document.getElementById(id).classList.add('open');}
function closeModal(id){document.getElementById(id).classList.remove('open');}
function openProfile(){document.getElementById('profilePanel').classList.add('open');document.getElementById('profileOverlay').classList.add('open');}
function closeProfile(){document.getElementById('profilePanel').classList.remove('open');document.getElementById('profileOverlay').classList.remove('open');}
function toggleNotifs(){document.getElementById('notifPanel').classList.toggle('open');}
document.addEventListener('click',(e)=>{if(!e.target.closest('#notifPanel')&&!e.target.closest('.icon-btn'))document.getElementById('notifPanel').classList.remove('open');});

function showToast(msg,type='success'){
  const t=document.getElementById('toast');
  document.getElementById('toastMsg').textContent=msg;
  t.style.color=type==='error'?'#FF4757':'#00D4AA';
  t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),3000);
}

function submitRequest(e){
  e.preventDefault();
  const fd=new FormData(e.target);
  fd.append('action','create');
  fetch('/smartalloc/api/tasks.php',{method:'POST',body:fd})
    .then(r=>r.json())
    .then(d=>{
      if(d.success){showToast('Request submitted! Admin will assign volunteers.');closeModal('requestModal');setTimeout(()=>location.reload(),1000);}
      else showToast(d.error||'Failed','error');
    });
}

function deleteTask(id){
  if(!confirm('Remove this request?'))return;
  fetch('/smartalloc/api/tasks.php',{method:'POST',body:new URLSearchParams({action:'delete',id})})
    .then(r=>r.json())
    .then(d=>{if(d.success){showToast('Removed');setTimeout(()=>location.reload(),600);}});
}
</script>
</body>
</html>
