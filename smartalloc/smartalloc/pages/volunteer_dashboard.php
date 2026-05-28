<?php
// pages/volunteer_dashboard.php
session_start();
require_once '../config/db.php';
requireLogin('volunteer');

$user = $_SESSION['user'];
$db = getDB();

// Volunteer stats
$my_assignments = $db->prepare("SELECT a.*, t.title, t.location, t.problem_type, t.urgency, t.description, t.volunteers_needed FROM assignments a JOIN tasks t ON a.task_id = t.id WHERE a.volunteer_id = ? ORDER BY a.assigned_at DESC");
$my_assignments->bind_param('i', $user['id']);
$my_assignments->execute();
$my_tasks = $my_assignments->get_result()->fetch_all(MYSQLI_ASSOC);

$active_count = count(array_filter($my_tasks, fn($t) => in_array($t['status'], ['accepted','in-progress'])));
$completed_count = count(array_filter($my_tasks, fn($t) => $t['status'] === 'completed'));

// Available tasks (not yet assigned to this volunteer)
$avail = $db->prepare("SELECT t.* FROM tasks t LEFT JOIN assignments a ON a.task_id = t.id AND a.volunteer_id = ? WHERE t.status='open' AND a.id IS NULL ORDER BY t.urgency DESC LIMIT 8");
$avail->bind_param('i', $user['id']);
$avail->execute();
$available_tasks = $avail->get_result()->fetch_all(MYSQLI_ASSOC);

// Notifications
$nq = $db->prepare("SELECT * FROM notifications WHERE user_id = ? AND is_read = 0 ORDER BY created_at DESC LIMIT 5");
$nq->bind_param('i', $user['id']);
$nq->execute();
$notifs = $nq->get_result()->fetch_all(MYSQLI_ASSOC);
$notif_count = count($notifs);

// User full details
$uq = $db->prepare("SELECT * FROM users WHERE id = ?");
$uq->bind_param('i', $user['id']);
$uq->execute();
$volunteer_details = $uq->get_result()->fetch_assoc();

$urgency_color = [5=>'#FF4757',4=>'#FFA502',3=>'#5352ED',2=>'#00D4AA',1=>'#888'];
$type_icons=['food'=>'🍽️','medical'=>'🏥','shelter'=>'🏠','water'=>'💧','education'=>'📚','other'=>'📌'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Volunteer Dashboard - SmartAlloc</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<style>
:root {
  --primary: #00D4AA; --bg: #0A0A1A; --card-bg: rgba(255,255,255,0.03);
  --border: rgba(255,255,255,0.08); --text: #fff; --text-muted: rgba(255,255,255,0.45);
  --glow: rgba(0,212,170,0.2); --danger: #FF4757; --warning: #FFA502; --success: #2ED573;
}
* { margin:0; padding:0; box-sizing:border-box; }
body { background:var(--bg); font-family:'Space Grotesk',sans-serif; color:var(--text); min-height:100vh; padding-bottom:80px; }

.topnav { background:rgba(10,10,26,0.95); backdrop-filter:blur(20px); border-bottom:1px solid var(--border); padding:0 20px; height:60px; display:flex; align-items:center; gap:12px; position:sticky; top:0; z-index:50; }
.logo { font-family:'Syne',sans-serif; font-size:18px; font-weight:800; flex:1; }
.logo span { color:var(--primary); }
.icon-btn { background:rgba(255,255,255,0.06); border:1px solid var(--border); border-radius:10px; padding:8px 12px; color:var(--text); cursor:pointer; font-size:16px; position:relative; transition:all 0.2s; }
.icon-btn:hover { background:rgba(255,255,255,0.1); }
.badge-dot { position:absolute; top:-5px; right:-5px; background:var(--danger); color:white; font-size:9px; font-weight:700; width:16px; height:16px; border-radius:50%; display:flex; align-items:center; justify-content:center; }
.profile-btn { display:flex; align-items:center; gap:8px; background:rgba(255,255,255,0.05); border:1px solid var(--border); border-radius:30px; padding:5px 12px 5px 5px; cursor:pointer; transition:all 0.2s; }
.profile-btn:hover { background:rgba(255,255,255,0.08); }
.avatar { width:32px; height:32px; border-radius:50%; background:linear-gradient(135deg,var(--primary),#6C63FF); display:flex; align-items:center; justify-content:center; font-size:13px; font-weight:700; color:#0A0A1A; }
.uname { font-size:13px; font-weight:600; }
.urole { font-size:10px; color:var(--primary); }

.page { max-width:900px; margin:0 auto; padding:20px 16px; }

/* HERO */
.hero { background:linear-gradient(135deg,rgba(0,212,170,0.08),rgba(108,99,255,0.08)); border:1px solid rgba(0,212,170,0.15); border-radius:20px; padding:24px; margin-bottom:20px; display:flex; align-items:center; gap:20px; }
.hero-icon { font-size:48px; }
.hero h2 { font-family:'Syne',sans-serif; font-size:22px; font-weight:800; }
.hero p { color:var(--text-muted); font-size:14px; margin-top:4px; }
.stat-pills { display:flex; gap:12px; margin-top:14px; flex-wrap:wrap; }
.stat-pill { background:rgba(255,255,255,0.06); border:1px solid var(--border); border-radius:30px; padding:8px 16px; text-align:center; }
.stat-pill-num { font-family:'Syne',sans-serif; font-size:20px; font-weight:800; color:var(--primary); display:block; }
.stat-pill-label { font-size:11px; color:var(--text-muted); }

/* CARDS */
.section-card { background:var(--card-bg); border:1px solid var(--border); border-radius:16px; overflow:hidden; margin-bottom:16px; }
.section-header { padding:16px 18px; border-bottom:1px solid var(--border); display:flex; align-items:center; justify-content:space-between; }
.section-title { font-size:14px; font-weight:700; display:flex; align-items:center; gap:8px; }
.section-action { font-size:12px; color:var(--primary); background:rgba(0,212,170,0.08); border:1px solid rgba(0,212,170,0.15); padding:5px 12px; border-radius:8px; cursor:pointer; font-family:inherit; transition:all 0.2s; }
.section-action:hover { background:rgba(0,212,170,0.15); }

.task-item { padding:16px 18px; border-bottom:1px solid rgba(255,255,255,0.04); }
.task-item:last-child { border-bottom:none; }
.task-top { display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:10px; }
.task-name { font-weight:700; font-size:15px; }
.task-meta { font-size:12px; color:var(--text-muted); margin-top:4px; }

.progress-bar { background:rgba(255,255,255,0.08); border-radius:4px; height:6px; margin:10px 0; }
.progress-fill { height:100%; border-radius:4px; background:linear-gradient(90deg,var(--primary),#6C63FF); transition:width 0.5s; }

.btn { padding:8px 14px; border-radius:8px; border:none; cursor:pointer; font-family:inherit; font-size:12px; font-weight:600; transition:all 0.2s; display:inline-flex; align-items:center; gap:5px; }
.btn-primary { background:var(--primary); color:#0A0A1A; }
.btn-primary:hover { filter:brightness(1.1); transform:translateY(-1px); }
.btn-ghost { background:rgba(255,255,255,0.06); color:var(--text); border:1px solid var(--border); }
.btn-ghost:hover { background:rgba(255,255,255,0.1); }
.btn-danger { background:rgba(255,71,87,0.1); color:var(--danger); border:1px solid rgba(255,71,87,0.2); }
.btn-success { background:rgba(46,213,115,0.1); color:var(--success); border:1px solid rgba(46,213,115,0.2); }
.task-actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }

.badge { padding:3px 9px; border-radius:20px; font-size:10px; font-weight:700; text-transform:uppercase; }
.badge-open { background:rgba(0,212,170,0.15); color:var(--primary); }
.badge-inprogress { background:rgba(255,165,2,0.15); color:var(--warning); }
.badge-accepted { background:rgba(83,82,237,0.15); color:#7C7BFF; }
.badge-completed { background:rgba(46,213,115,0.15); color:var(--success); }

.avail-item { display:flex; align-items:center; gap:14px; padding:14px 18px; border-bottom:1px solid rgba(255,255,255,0.04); }
.avail-item:last-child { border-bottom:none; }
.urgency-dot { width:10px; height:10px; border-radius:50%; flex-shrink:0; }
.avail-info { flex:1; }
.avail-name { font-weight:600; font-size:14px; }
.avail-meta { font-size:12px; color:var(--text-muted); margin-top:3px; }

/* AI MODAL */
.modal-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(8px); z-index:1000; display:none; align-items:center; justify-content:center; padding:16px; }
.modal-overlay.open { display:flex; }
.modal { background:#131325; border:1px solid var(--border); border-radius:20px; padding:28px; width:100%; max-width:520px; animation:modalIn 0.3s ease-out; max-height:90vh; overflow-y:auto; }
@keyframes modalIn { from{opacity:0;transform:scale(0.95)}to{opacity:1;transform:scale(1)} }
.modal h3 { font-family:'Syne',sans-serif; font-size:20px; font-weight:800; margin-bottom:8px; }
.modal-close { float:right; background:none; border:none; color:var(--text-muted); font-size:20px; cursor:pointer; }

.ai-input-area { width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border); border-radius:12px; padding:14px; color:var(--text); font-family:inherit; font-size:14px; resize:none; outline:none; min-height:100px; transition:all 0.2s; }
.ai-input-area:focus { border-color:var(--primary); background:rgba(0,212,170,0.04); }

.ai-parsed { background:rgba(0,212,170,0.06); border:1px solid rgba(0,212,170,0.2); border-radius:12px; padding:16px; margin-top:16px; display:none; }
.ai-parsed h4 { font-size:13px; color:var(--primary); margin-bottom:12px; text-transform:uppercase; letter-spacing:0.5px; }
.parsed-row { display:flex; justify-content:space-between; align-items:center; margin-bottom:8px; font-size:13px; }
.parsed-key { color:var(--text-muted); }
.parsed-val { font-weight:600; }

.ai-loading { display:none; text-align:center; padding:20px; color:var(--text-muted); }
.spinner { display:inline-block; width:24px; height:24px; border:2px solid rgba(0,212,170,0.2); border-top-color:var(--primary); border-radius:50%; animation:spin 0.8s linear infinite; margin-bottom:8px; }
@keyframes spin { to{transform:rotate(360deg)} }

/* PROFILE PANEL */
.profile-panel { position:fixed; top:0; right:0; bottom:0; width:320px; background:#0F0F23; border-left:1px solid var(--border); z-index:200; transform:translateX(100%); transition:transform 0.3s ease; padding:24px; overflow-y:auto; }
.profile-panel.open { transform:translateX(0); }
.profile-overlay { position:fixed; inset:0; background:rgba(0,0,0,0.5); z-index:199; display:none; }
.profile-overlay.open { display:block; }

/* NOTIF DROPDOWN */
.notif-panel { position:fixed; top:68px; right:20px; width:320px; background:#0F0F23; border:1px solid var(--border); border-radius:16px; z-index:200; padding:16px; display:none; box-shadow:0 20px 60px rgba(0,0,0,0.5); }
.notif-panel.open { display:block; animation:modalIn 0.2s ease; }
.notif-item { padding:12px; border-bottom:1px solid rgba(255,255,255,0.05); font-size:13px; }
.notif-item:last-child { border-bottom:none; }

/* BOTTOM NAV */
.bottom-nav { position:fixed; bottom:0; left:0; right:0; background:rgba(10,10,26,0.95); backdrop-filter:blur(20px); border-top:1px solid var(--border); display:flex; justify-content:space-around; padding:8px 0 12px; z-index:50; }
.nav-tab { display:flex; flex-direction:column; align-items:center; gap:4px; color:var(--text-muted); font-size:10px; font-weight:500; cursor:pointer; padding:6px 12px; border-radius:10px; transition:all 0.2s; text-decoration:none; }
.nav-tab.active { color:var(--primary); }
.nav-tab i { font-size:18px; }

/* FAB */
.fab { position:fixed; bottom:80px; right:20px; width:54px; height:54px; border-radius:50%; background:linear-gradient(135deg,var(--primary),#6C63FF); border:none; color:#0A0A1A; font-size:24px; font-weight:700; cursor:pointer; box-shadow:0 8px 25px rgba(0,212,170,0.4); z-index:60; display:flex; align-items:center; justify-content:center; transition:all 0.2s; }
.fab:hover { transform:scale(1.1); box-shadow:0 12px 35px rgba(0,212,170,0.5); }

.form-g { margin-bottom:14px; }
.form-g label { display:block; font-size:11px; color:var(--text-muted); margin-bottom:6px; text-transform:uppercase; letter-spacing:0.5px; }
.form-g input, .form-g select, .form-g textarea { width:100%; background:rgba(255,255,255,0.05); border:1px solid var(--border); border-radius:10px; padding:11px 13px; color:#fff; font-size:14px; font-family:inherit; outline:none; }
.form-g input:focus, .form-g select:focus { border-color:var(--primary); }
.form-g select option { background:#131325; }

.toast { position:fixed; bottom:88px; left:50%; transform:translateX(-50%); background:rgba(0,212,170,0.15); border:1px solid rgba(0,212,170,0.3); border-radius:12px; padding:12px 20px; color:var(--primary); font-size:13px; z-index:9999; display:none; white-space:nowrap; }
.toast.show { display:block; animation:toastIn 0.3s ease; }
@keyframes toastIn { from{opacity:0;transform:translateX(-50%) translateY(8px)}to{opacity:1;transform:translateX(-50%) translateY(0)} }
</style>
</head>
<body>

<!-- TOP NAV -->
<div class="topnav">
  <div class="logo">Smart<span>Alloc</span></div>
  <button class="icon-btn" onclick="toggleNotifs()" title="Notifications">
    🔔 <?php if($notif_count>0): ?><span class="badge-dot"><?=$notif_count?></span><?php endif; ?>
  </button>
  <div class="profile-btn" onclick="openProfile()">
    <div class="avatar"><?=strtoupper(substr($user['name'],0,1))?></div>
    <div><div class="uname"><?=htmlspecialchars($user['name'])?></div><div class="urole">Volunteer</div></div>
  </div>
</div>

<!-- NOTIFICATIONS PANEL -->
<div class="notif-panel" id="notifPanel">
  <div style="font-weight:700;margin-bottom:12px;font-size:14px">🔔 Notifications</div>
  <?php foreach($notifs as $n): ?>
  <div class="notif-item">📌 <?=htmlspecialchars($n['message'])?><div style="font-size:11px;color:var(--text-muted);margin-top:4px"><?=date('M d, H:i',strtotime($n['created_at']))?></div></div>
  <?php endforeach; ?>
  <?php if(empty($notifs)): ?><div class="notif-item" style="color:var(--text-muted)">No new notifications</div><?php endif; ?>
</div>

<!-- MAIN PAGE -->
<div class="page">
  <!-- HERO -->
  <div class="hero">
    <div class="hero-icon">👋</div>
    <div style="flex:1">
      <h2>Hello, <?=htmlspecialchars(explode(' ', $user['name'])[0])?>!</h2>
      <p>Ready to make a difference today?</p>
      <?php if($volunteer_details['volunteer_id']): ?>
      <p style="margin-top:4px;font-size:12px;color:var(--primary)">ID: <?=htmlspecialchars($volunteer_details['volunteer_id'])?></p>
      <?php endif; ?>
      <div class="stat-pills">
        <div class="stat-pill"><span class="stat-pill-num"><?=$completed_count?></span><span class="stat-pill-label">Completed</span></div>
        <div class="stat-pill"><span class="stat-pill-num"><?=$active_count?></span><span class="stat-pill-label">Active</span></div>
        <div class="stat-pill"><span class="stat-pill-num"><?=count($available_tasks)?></span><span class="stat-pill-label">Available</span></div>
      </div>
    </div>
  </div>

  <!-- MY ACTIVE TASKS -->
  <div class="section-card">
    <div class="section-header">
      <div class="section-title">📋 Your Active Tasks</div>
      <button class="section-action" onclick="location.reload()">↺ Refresh</button>
    </div>
    <?php $active = array_filter($my_tasks, fn($t)=>in_array($t['status'],['accepted','in-progress'])); ?>
    <?php if(empty($active)): ?>
    <div style="padding:24px;text-align:center;color:var(--text-muted)">No active tasks. Accept some tasks below!</div>
    <?php endif; ?>
    <?php foreach($active as $t):
      $clr = $urgency_color[$t['urgency']] ?? '#888';
      $badge_class = $t['status']==='in-progress' ? 'badge-inprogress' : 'badge-accepted';
    ?>
    <div class="task-item" style="border-left:3px solid <?=$clr?>">
      <div class="task-top">
        <div>
          <div class="task-name"><?=$type_icons[$t['problem_type']]?> <?=htmlspecialchars($t['title'])?></div>
          <div class="task-meta">📍 <?=htmlspecialchars($t['location'])?> • Urgency <?=$t['urgency']?>/5</div>
        </div>
        <span class="badge <?=$badge_class?>"><?=ucfirst(str_replace('-',' ',$t['status']))?></span>
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:6px">Progress: <?=$t['progress']?>%</div>
      <div class="progress-bar"><div class="progress-fill" style="width:<?=$t['progress']?>%"></div></div>
      <div class="task-actions">
        <button class="btn btn-primary" onclick="updateProgress(<?=$t['id']?>, <?=$t['task_id']?>)">📈 Update Progress</button>
        <button class="btn btn-success" onclick="completeTask(<?=$t['id']?>, <?=$t['task_id']?>)">✅ Mark Complete</button>
        <button class="btn btn-ghost" onclick="window.open('https://maps.google.com/?q='+encodeURIComponent('<?=addslashes($t['location'])?>'), '_blank')">🗺️ Directions</button>
      </div>
    </div>
    <?php endforeach; ?>
  </div>

  <!-- AVAILABLE TASKS -->
  <div class="section-card">
    <div class="section-header">
      <div class="section-title">🎯 Available Tasks Near You</div>
    </div>
    <?php foreach($available_tasks as $t):
      $clr = $urgency_color[$t['urgency']] ?? '#888';
    ?>
    <div class="avail-item">
      <div class="urgency-dot" style="background:<?=$clr?>;box-shadow:0 0 6px <?=$clr?>"></div>
      <div class="avail-info">
        <div class="avail-name"><?=$type_icons[$t['problem_type']]?> <?=htmlspecialchars($t['title'])?></div>
        <div class="avail-meta">📍 <?=htmlspecialchars($t['location'])?> • 👥 <?=$t['volunteers_needed']?> needed • ⚡ <?=$t['urgency']?>/5</div>
      </div>
      <button class="btn btn-primary" onclick="acceptTask(<?=$t['id']?>)">Accept →</button>
    </div>
    <?php endforeach; ?>
    <?php if(empty($available_tasks)): ?>
    <div style="padding:24px;text-align:center;color:var(--text-muted)">No available tasks right now. Check back later!</div>
    <?php endif; ?>
  </div>
</div>

<!-- FAB: Report New Need -->
<button class="fab" onclick="openModal('aiModal')" title="Report New Need">+</button>

<!-- BOTTOM NAV -->
<div class="bottom-nav">
  <a href="/smartalloc/pages/volunteer_dashboard.php" class="nav-tab active"><i class="fas fa-home"></i>Home</a>
  <a href="#" class="nav-tab" onclick="window.open('https://maps.google.com/?q=Chennai+NGO+volunteer+tasks', '_blank')"><i class="fas fa-map-marker-alt"></i>Map</a>
  <a href="#" class="nav-tab" onclick="document.querySelector('.section-card').scrollIntoView()"><i class="fas fa-clipboard-list"></i>My Tasks</a>
  <a href="#" class="nav-tab" onclick="openProfile()"><i class="fas fa-user"></i>Profile</a>
  <a href="/smartalloc/pages/logout.php" class="nav-tab"><i class="fas fa-sign-out-alt"></i>Logout</a>
</div>

<!-- AI NEED REPORT MODAL -->
<div class="modal-overlay" id="aiModal">
  <div class="modal">
    <button class="modal-close" onclick="closeModal('aiModal')">✕</button>
    <h3>🤖 Report a Need (AI-Powered)</h3>
    <p style="color:var(--text-muted);font-size:13px;margin-bottom:16px">Just describe what you see in plain language. Our AI will extract all the details for you!</p>

    <div class="form-g">
      <label>Describe the situation</label>
      <textarea class="ai-input-area" id="aiInput" placeholder="e.g. There are about 50 families near Anna Nagar who haven't had food since yesterday morning. Its very urgent, they need clean drinking water too. The area is flooded near the main road."></textarea>
    </div>

    <div style="display:flex;gap:10px;margin-bottom:16px">
      <button class="btn btn-primary" onclick="analyzeWithAI()" style="flex:1">🤖 Analyze with AI</button>
      <button class="btn btn-ghost" onclick="clearAI()">✕ Clear</button>
    </div>

    <div class="ai-loading" id="aiLoading">
      <div class="spinner"></div>
      <div>AI is analyzing your description...</div>
    </div>

    <div class="ai-parsed" id="aiParsed">
      <h4>✅ Extracted Details</h4>
      <div class="parsed-row"><span class="parsed-key">📍 Location</span><span class="parsed-val" id="pLocation">-</span></div>
      <div class="parsed-row"><span class="parsed-key">🏷️ Type</span><span class="parsed-val" id="pType">-</span></div>
      <div class="parsed-row"><span class="parsed-key">⚡ Urgency</span><span class="parsed-val" id="pUrgency">-</span></div>
      <div class="parsed-row"><span class="parsed-key">👥 Est. People</span><span class="parsed-val" id="pPeople">-</span></div>
      <div class="parsed-row"><span class="parsed-key">📝 Summary</span><span class="parsed-val" id="pSummary" style="font-size:12px;text-align:right;max-width:60%">-</span></div>
      <div style="margin-top:14px;display:flex;gap:10px">
        <button class="btn btn-primary" onclick="submitParsedTask()" style="flex:1">📤 Submit Task</button>
        <button class="btn btn-ghost" onclick="editParsed()">✏️ Edit</button>
      </div>
    </div>

    <!-- Manual form (shown after "Edit") -->
    <div id="manualForm" style="display:none;margin-top:16px">
      <div class="form-g"><label>Title</label><input type="text" id="mTitle"></div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
        <div class="form-g"><label>Location</label><input type="text" id="mLocation"></div>
        <div class="form-g"><label>Type</label>
          <select id="mType"><option value="food">Food</option><option value="medical">Medical</option><option value="shelter">Shelter</option><option value="water">Water</option><option value="education">Education</option><option value="other">Other</option></select>
        </div>
      </div>
      <div class="form-g"><label>Urgency (1-5)</label>
        <select id="mUrgency"><option value="5">5-Critical</option><option value="4">4-High</option><option value="3" selected>3-Medium</option><option value="2">2-Low</option><option value="1">1-Minimal</option></select>
      </div>
      <button class="btn btn-primary" onclick="submitManualTask()" style="width:100%;justify-content:center">📤 Submit</button>
    </div>
  </div>
</div>

<!-- PROFILE PANEL -->
<div class="profile-overlay" id="profileOverlay" onclick="closeProfile()"></div>
<div class="profile-panel" id="profilePanel">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:24px">
    <h3 style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800">My Profile</h3>
    <button onclick="closeProfile()" style="background:none;border:none;color:var(--text-muted);font-size:20px;cursor:pointer">✕</button>
  </div>
  <div style="text-align:center;margin-bottom:24px">
    <div style="width:72px;height:72px;border-radius:50%;background:linear-gradient(135deg,var(--primary),#6C63FF);display:flex;align-items:center;justify-content:center;font-size:28px;font-weight:700;color:#0A0A1A;margin:0 auto 12px"><?=strtoupper(substr($user['name'],0,1))?></div>
    <div style="font-weight:700;font-size:18px"><?=htmlspecialchars($volunteer_details['name'])?></div>
    <div style="color:var(--primary);font-size:13px;margin-top:4px">Volunteer</div>
    <?php if($volunteer_details['volunteer_id']): ?>
    <div style="background:rgba(0,212,170,0.1);border:1px solid rgba(0,212,170,0.2);border-radius:20px;padding:4px 14px;display:inline-block;font-size:12px;margin-top:8px;color:var(--primary)"><?=htmlspecialchars($volunteer_details['volunteer_id'])?></div>
    <?php endif; ?>
  </div>
  <?php $details = [['📧 Email', $volunteer_details['email']], ['📞 Phone', $volunteer_details['phone'] ?: 'Not set'], ['📍 Location', $volunteer_details['location'] ?: 'Not set'], ['🛠️ Skills', $volunteer_details['skills'] ?: 'Not set'], ['📅 Joined', date('M Y', strtotime($volunteer_details['created_at']))]]; ?>
  <?php foreach($details as [$label, $val]): ?>
  <div style="padding:12px;background:rgba(255,255,255,0.03);border:1px solid var(--border);border-radius:10px;margin-bottom:10px">
    <div style="font-size:11px;color:var(--text-muted);margin-bottom:4px"><?=$label?></div>
    <div style="font-size:14px;font-weight:600"><?=htmlspecialchars($val)?></div>
  </div>
  <?php endforeach; ?>
  <div style="margin-top:16px;text-align:center;display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px">
    <div style="background:rgba(0,212,170,0.08);border:1px solid rgba(0,212,170,0.15);border-radius:12px;padding:12px;text-align:center">
      <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:var(--primary)"><?=$completed_count?></div>
      <div style="font-size:11px;color:var(--text-muted)">Done</div>
    </div>
    <div style="background:rgba(255,165,2,0.08);border:1px solid rgba(255,165,2,0.15);border-radius:12px;padding:12px;text-align:center">
      <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:var(--warning)"><?=$active_count?></div>
      <div style="font-size:11px;color:var(--text-muted)">Active</div>
    </div>
    <div style="background:rgba(83,82,237,0.08);border:1px solid rgba(83,82,237,0.15);border-radius:12px;padding:12px;text-align:center">
      <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;color:#7C7BFF"><?=count($my_tasks)?></div>
      <div style="font-size:11px;color:var(--text-muted)">Total</div>
    </div>
  </div>
  <a href="/smartalloc/pages/logout.php" class="btn btn-danger" style="width:100%;justify-content:center;margin-top:20px">🚪 Logout</a>
</div>

<div class="toast" id="toast"><span id="toastMsg"></span></div>

<script>
let parsedData = {};

function openModal(id) { document.getElementById(id).classList.add('open'); }
function closeModal(id) { document.getElementById(id).classList.remove('open'); }
function openProfile() { document.getElementById('profilePanel').classList.add('open'); document.getElementById('profileOverlay').classList.add('open'); }
function closeProfile() { document.getElementById('profilePanel').classList.remove('open'); document.getElementById('profileOverlay').classList.remove('open'); }
function toggleNotifs() { document.getElementById('notifPanel').classList.toggle('open'); }
document.addEventListener('click', (e) => { if(!e.target.closest('#notifPanel') && !e.target.closest('.icon-btn')) document.getElementById('notifPanel').classList.remove('open'); });

function showToast(msg, type='success') {
  const t = document.getElementById('toast');
  document.getElementById('toastMsg').textContent = msg;
  t.style.color = type==='error' ? '#FF4757' : '#00D4AA';
  t.style.background = type==='error' ? 'rgba(255,71,87,0.15)' : 'rgba(0,212,170,0.15)';
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 3000);
}

async function analyzeWithAI() {
  const text = document.getElementById('aiInput').value.trim();
  if(!text) { showToast('Please describe the situation first!', 'error'); return; }

  document.getElementById('aiLoading').style.display = 'block';
  document.getElementById('aiParsed').style.display = 'none';
  document.getElementById('manualForm').style.display = 'none';

  try {
    const response = await fetch('/smartalloc/api/ai_parse.php', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    const data = await response.json();
    document.getElementById('aiLoading').style.display = 'none';

    if(data.success) {
      parsedData = data.parsed;
      document.getElementById('pLocation').textContent = parsedData.location || 'Unknown';
      document.getElementById('pType').textContent = (parsedData.problem_type || 'other').charAt(0).toUpperCase() + (parsedData.problem_type || 'other').slice(1);
      document.getElementById('pUrgency').textContent = (parsedData.urgency || 3) + '/5 - ' + ['','Minimal','Low','Medium','High','Critical'][parsedData.urgency || 3];
      document.getElementById('pPeople').textContent = parsedData.estimated_people || 'Unknown';
      document.getElementById('pSummary').textContent = parsedData.title || text.substring(0,60) + '...';
      document.getElementById('aiParsed').style.display = 'block';
    } else {
      showToast('AI parsing failed. Use manual mode below.', 'error');
      editParsed();
    }
  } catch(err) {
    document.getElementById('aiLoading').style.display = 'none';
    // Fallback: demo parse
    parsedData = fallbackParse(text);
    document.getElementById('pLocation').textContent = parsedData.location;
    document.getElementById('pType').textContent = parsedData.problem_type.charAt(0).toUpperCase() + parsedData.problem_type.slice(1);
    document.getElementById('pUrgency').textContent = parsedData.urgency + '/5';
    document.getElementById('pPeople').textContent = parsedData.estimated_people;
    document.getElementById('pSummary').textContent = parsedData.title;
    document.getElementById('aiParsed').style.display = 'block';
  }
}

function fallbackParse(text) {
  const lower = text.toLowerCase();
  // Simple rule-based extraction
  const types = ['food','medical','shelter','water','education'];
  const problem_type = types.find(t => lower.includes(t)) || 'other';
  const urgency = lower.includes('urgent') || lower.includes('critical') || lower.includes('emergency') ? 5 :
                  lower.includes('severe') || lower.includes('desperate') ? 4 :
                  lower.includes('need') || lower.includes('require') ? 3 : 2;
  const numMatch = text.match(/\d+/);
  const estimated_people = numMatch ? numMatch[0] + ' people' : 'Unknown';
  // Try to extract location (word after "near", "at", "in")
  const locMatch = text.match(/(?:near|at|in|around)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)/);
  const location = locMatch ? locMatch[1] : 'Location not specified';
  const title = (problem_type.charAt(0).toUpperCase() + problem_type.slice(1)) + ' Need - ' + location;
  return { problem_type, urgency, estimated_people, location, title, description: text };
}

function clearAI() {
  document.getElementById('aiInput').value = '';
  document.getElementById('aiParsed').style.display = 'none';
  document.getElementById('manualForm').style.display = 'none';
  document.getElementById('aiLoading').style.display = 'none';
}

function editParsed() {
  document.getElementById('aiParsed').style.display = 'none';
  document.getElementById('manualForm').style.display = 'block';
  if(parsedData.title) document.getElementById('mTitle').value = parsedData.title;
  if(parsedData.location) document.getElementById('mLocation').value = parsedData.location;
  if(parsedData.problem_type) document.getElementById('mType').value = parsedData.problem_type;
  if(parsedData.urgency) document.getElementById('mUrgency').value = parsedData.urgency;
}

function submitParsedTask() {
  const fd = new FormData();
  fd.append('action', 'create');
  fd.append('title', parsedData.title || 'Community Need');
  fd.append('location', parsedData.location || 'Unknown');
  fd.append('problem_type', parsedData.problem_type || 'other');
  fd.append('urgency', parsedData.urgency || 3);
  fd.append('description', parsedData.description || document.getElementById('aiInput').value);
  fd.append('volunteers_needed', 5);
  submitTask(fd);
}

function submitManualTask() {
  const fd = new FormData();
  fd.append('action', 'create');
  fd.append('title', document.getElementById('mTitle').value || 'Community Need');
  fd.append('location', document.getElementById('mLocation').value);
  fd.append('problem_type', document.getElementById('mType').value);
  fd.append('urgency', document.getElementById('mUrgency').value);
  fd.append('description', document.getElementById('aiInput').value);
  fd.append('volunteers_needed', 5);
  submitTask(fd);
}

function submitTask(fd) {
  fetch('/smartalloc/api/tasks.php', { method:'POST', body:fd })
    .then(r => r.json())
    .then(d => {
      if(d.success) { showToast('Need reported successfully!'); closeModal('aiModal'); clearAI(); }
      else showToast(d.error || 'Failed to submit', 'error');
    });
}

function acceptTask(taskId) {
  fetch('/smartalloc/api/tasks.php', { method:'POST', body:new URLSearchParams({action:'assign', task_id:taskId, volunteer_id:<?=$user['id']?>}) })
    .then(r => r.json())
    .then(d => { if(d.success) { showToast('Task accepted!'); setTimeout(() => location.reload(), 800); } else showToast(d.error || 'Error', 'error'); });
}

function updateProgress(assignId, taskId) {
  const p = prompt('Enter your current progress (0-100):', '50');
  if(p === null) return;
  const val = Math.min(100, Math.max(0, parseInt(p) || 0));
  fetch('/smartalloc/api/tasks.php', { method:'POST', body:new URLSearchParams({action:'progress', assign_id:assignId, progress:val}) })
    .then(r => r.json())
    .then(d => { if(d.success) { showToast('Progress updated to ' + val + '%!'); setTimeout(() => location.reload(), 800); } });
}

function completeTask(assignId, taskId) {
  if(!confirm('Mark this task as completed?')) return;
  fetch('/smartalloc/api/tasks.php', { method:'POST', body:new URLSearchParams({action:'complete', assign_id:assignId, task_id:taskId}) })
    .then(r => r.json())
    .then(d => { if(d.success) { showToast('Task completed! Great job! 🎉'); setTimeout(() => location.reload(), 800); } });
}
</script>
</body>
</html>
