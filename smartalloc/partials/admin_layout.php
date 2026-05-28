<?php
// partials/admin_layout.php - Shared layout for admin pages
// Usage: include at top of admin pages
// Variables needed: $pageTitle (string), $activePage (string)

$user = $_SESSION['user'];
$db = getDB();

// Get notifications count
$nq = $db->prepare("SELECT COUNT(*) as cnt FROM notifications WHERE user_id = ? AND is_read = 0");
$nq->bind_param('i', $user['id']);
$nq->execute();
$notif_count = $nq->get_result()->fetch_assoc()['cnt'];

// Get task stats
$stats = $db->query("SELECT
  SUM(status='open') as open_tasks,
  SUM(status='in-progress') as active_tasks,
  SUM(status='completed') as completed_tasks,
  COUNT(*) as total_tasks
FROM tasks")->fetch_assoc();

$vol_count = $db->query("SELECT COUNT(*) as cnt FROM users WHERE role='volunteer'")->fetch_assoc()['cnt'];
$ngo_count = $db->query("SELECT COUNT(*) as cnt FROM users WHERE role='ngo'")->fetch_assoc()['cnt'];
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title><?= htmlspecialchars($pageTitle ?? 'Admin') ?> - SmartAlloc</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<style>
:root {
  --primary: #00D4AA;
  --primary-dark: #00A882;
  --bg: #0A0A1A;
  --sidebar-bg: #0F0F23;
  --card-bg: rgba(255,255,255,0.03);
  --border: rgba(255,255,255,0.08);
  --text: #FFFFFF;
  --text-muted: rgba(255,255,255,0.45);
  --glow: rgba(0,212,170,0.2);
  --danger: #FF4757;
  --warning: #FFA502;
  --info: #5352ED;
  --success: #2ED573;
  --sidebar-w: 260px;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: var(--bg);
  font-family: 'Space Grotesk', sans-serif;
  color: var(--text);
  display: flex;
  min-height: 100vh;
  overflow-x: hidden;
}

/* SIDEBAR */
.sidebar {
  width: var(--sidebar-w);
  background: var(--sidebar-bg);
  border-right: 1px solid var(--border);
  display: flex;
  flex-direction: column;
  position: fixed;
  top: 0; left: 0; bottom: 0;
  z-index: 100;
  transition: transform 0.3s ease;
}

.sidebar.collapsed { transform: translateX(-100%); }

.sidebar-logo {
  padding: 24px 20px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; gap: 12px;
}

.logo-icon {
  width: 40px; height: 40px; border-radius: 12px;
  background: linear-gradient(135deg, var(--primary), #6C63FF);
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  box-shadow: 0 0 20px var(--glow);
  flex-shrink: 0;
}

.logo-text {
  font-family: 'Syne', sans-serif;
  font-size: 20px; font-weight: 800;
  letter-spacing: -0.5px;
}
.logo-text span { color: var(--primary); }

.nav-section { padding: 20px 12px 8px; }
.nav-label {
  font-size: 10px; font-weight: 600;
  color: var(--text-muted); letter-spacing: 1.5px;
  text-transform: uppercase; padding: 0 8px;
  margin-bottom: 6px;
}

.nav-item {
  display: flex; align-items: center; gap: 12px;
  padding: 11px 12px; border-radius: 10px;
  color: var(--text-muted); text-decoration: none;
  font-size: 14px; font-weight: 500;
  transition: all 0.2s; margin-bottom: 2px;
  cursor: pointer;
}
.nav-item:hover { background: rgba(255,255,255,0.05); color: var(--text); }
.nav-item.active {
  background: rgba(0,212,170,0.12);
  color: var(--primary);
  border-left: 3px solid var(--primary);
}
.nav-item i { width: 18px; text-align: center; font-size: 15px; }

.nav-badge {
  margin-left: auto;
  background: var(--danger); color: white;
  font-size: 10px; font-weight: 700;
  padding: 2px 7px; border-radius: 20px;
}

.sidebar-footer {
  margin-top: auto;
  padding: 16px 12px;
  border-top: 1px solid var(--border);
}

/* MAIN CONTENT */
.main-content {
  margin-left: var(--sidebar-w);
  flex: 1;
  min-height: 100vh;
  transition: margin-left 0.3s ease;
}

.main-content.expanded { margin-left: 0; }

/* TOP NAV */
.topnav {
  background: rgba(10,10,26,0.9);
  backdrop-filter: blur(20px);
  border-bottom: 1px solid var(--border);
  padding: 0 24px;
  height: 64px;
  display: flex; align-items: center; gap: 16px;
  position: sticky; top: 0; z-index: 50;
}

.topnav-toggle {
  background: none; border: none; color: var(--text);
  font-size: 18px; cursor: pointer; padding: 8px;
  border-radius: 8px; transition: background 0.2s;
}
.topnav-toggle:hover { background: rgba(255,255,255,0.08); }

.topnav-title {
  font-family: 'Syne', sans-serif;
  font-size: 18px; font-weight: 700;
  flex: 1;
}

.topnav-actions { display: flex; align-items: center; gap: 12px; }

.notif-btn {
  position: relative;
  background: rgba(255,255,255,0.06); border: 1px solid var(--border);
  border-radius: 10px; padding: 8px 12px;
  color: var(--text); cursor: pointer;
  transition: all 0.2s; font-size: 16px;
}
.notif-btn:hover { background: rgba(255,255,255,0.1); }
.notif-badge {
  position: absolute; top: -6px; right: -6px;
  background: var(--danger); color: white;
  font-size: 10px; font-weight: 700;
  width: 18px; height: 18px;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
}

.user-pill {
  display: flex; align-items: center; gap: 10px;
  background: rgba(255,255,255,0.05); border: 1px solid var(--border);
  border-radius: 30px; padding: 6px 14px 6px 6px;
  cursor: pointer; transition: all 0.2s;
}
.user-pill:hover { background: rgba(255,255,255,0.08); }
.user-avatar {
  width: 32px; height: 32px; border-radius: 50%;
  background: linear-gradient(135deg, var(--primary), #6C63FF);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; font-weight: 700; color: #0A0A1A;
}
.user-name { font-size: 14px; font-weight: 600; }
.user-role { font-size: 11px; color: var(--primary); }

/* PAGE CONTENT */
.page-content { padding: 28px 24px; }

/* STAT CARDS */
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }

.stat-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 16px; padding: 20px;
  position: relative; overflow: hidden;
  transition: transform 0.2s;
}
.stat-card:hover { transform: translateY(-2px); }
.stat-card::before {
  content: ''; position: absolute;
  top: 0; left: 0; right: 0; height: 2px;
  background: var(--accent-color, var(--primary));
}
.stat-number {
  font-family: 'Syne', sans-serif;
  font-size: 36px; font-weight: 800;
  line-height: 1; margin-bottom: 4px;
  color: var(--accent-color, var(--primary));
}
.stat-label { font-size: 13px; color: var(--text-muted); font-weight: 500; }
.stat-icon {
  position: absolute; top: 16px; right: 16px;
  font-size: 28px; opacity: 0.15;
}

/* SECTION CARDS */
.section-card {
  background: var(--card-bg);
  border: 1px solid var(--border);
  border-radius: 16px;
  overflow: hidden;
  margin-bottom: 20px;
}
.section-header {
  padding: 18px 20px;
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center; justify-content: space-between;
}
.section-title {
  font-size: 15px; font-weight: 700;
  display: flex; align-items: center; gap: 8px;
}
.section-action {
  font-size: 13px; color: var(--primary);
  text-decoration: none; font-weight: 600;
  background: rgba(0,212,170,0.1); border: 1px solid rgba(0,212,170,0.2);
  padding: 6px 14px; border-radius: 8px;
  transition: all 0.2s; cursor: pointer;
  border: none; font-family: inherit;
}
.section-action:hover { background: rgba(0,212,170,0.2); }

/* TABLE */
.data-table { width: 100%; border-collapse: collapse; }
.data-table th {
  padding: 12px 20px;
  font-size: 11px; font-weight: 600;
  color: var(--text-muted); text-transform: uppercase;
  letter-spacing: 0.5px; text-align: left;
  border-bottom: 1px solid var(--border);
}
.data-table td {
  padding: 14px 20px;
  font-size: 14px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.data-table tr:last-child td { border-bottom: none; }
.data-table tr:hover td { background: rgba(255,255,255,0.02); }

/* BADGES */
.badge {
  padding: 4px 10px; border-radius: 20px;
  font-size: 11px; font-weight: 700; text-transform: uppercase;
}
.badge-open { background: rgba(0,212,170,0.15); color: var(--primary); }
.badge-inprogress { background: rgba(255,165,2,0.15); color: var(--warning); }
.badge-completed { background: rgba(46,213,115,0.15); color: var(--success); }
.badge-critical { background: rgba(255,71,87,0.15); color: var(--danger); }
.badge-high { background: rgba(255,165,2,0.15); color: var(--warning); }
.badge-medium { background: rgba(83,82,237,0.15); color: #7C7BFF; }
.badge-low { background: rgba(255,255,255,0.08); color: var(--text-muted); }

/* URGENCY DOTS */
.urgency { display: flex; align-items: center; gap: 4px; }
.urgency-dot { width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.15); }
.urgency-dot.filled { background: var(--u-color, var(--primary)); }

/* BUTTONS */
.btn { padding: 8px 16px; border-radius: 8px; border: none; cursor: pointer; font-family: inherit; font-size: 13px; font-weight: 600; transition: all 0.2s; display: inline-flex; align-items: center; gap: 6px; }
.btn-primary { background: var(--primary); color: #0A0A1A; }
.btn-primary:hover { background: var(--primary-dark); transform: translateY(-1px); }
.btn-ghost { background: rgba(255,255,255,0.06); color: var(--text); border: 1px solid var(--border); }
.btn-ghost:hover { background: rgba(255,255,255,0.1); }
.btn-danger { background: rgba(255,71,87,0.1); color: var(--danger); border: 1px solid rgba(255,71,87,0.2); }
.btn-danger:hover { background: rgba(255,71,87,0.2); }
.btn-sm { padding: 5px 12px; font-size: 12px; }

/* GRID */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.grid-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; }

/* AI MATCH CARD */
.match-item {
  display: flex; align-items: center; gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(255,255,255,0.04);
}
.match-item:last-child { border-bottom: none; }
.match-score {
  font-family: 'Syne', sans-serif;
  font-size: 22px; font-weight: 800;
  color: var(--primary); min-width: 60px;
}
.match-info { flex: 1; }
.match-title { font-weight: 600; font-size: 14px; margin-bottom: 4px; }
.match-sub { font-size: 12px; color: var(--text-muted); }

/* MODAL */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.7); backdrop-filter: blur(8px);
  z-index: 1000; display: none; align-items: center; justify-content: center;
}
.modal-overlay.open { display: flex; }
.modal {
  background: #131325; border: 1px solid var(--border);
  border-radius: 20px; padding: 32px; width: 90%; max-width: 540px;
  animation: modalIn 0.3s ease-out;
}
@keyframes modalIn {
  from { opacity: 0; transform: scale(0.95) translateY(-10px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
.modal h3 { font-family: 'Syne', sans-serif; font-size: 20px; font-weight: 800; margin-bottom: 20px; }
.modal-close { float: right; background: none; border: none; color: var(--text-muted); font-size: 20px; cursor: pointer; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }
.form-g { margin-bottom: 16px; }
.form-g label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
.form-g input, .form-g select, .form-g textarea {
  width: 100%; background: rgba(255,255,255,0.05); border: 1px solid var(--border);
  border-radius: 10px; padding: 12px; color: #fff; font-size: 14px; font-family: inherit; outline: none;
}
.form-g input:focus, .form-g select:focus, .form-g textarea:focus { border-color: var(--primary); }
.form-g select option { background: #131325; }

/* QUICK ACTIONS */
.quick-action {
  display: flex; align-items: center; gap: 14px;
  padding: 14px 20px; background: rgba(255,255,255,0.03);
  border: 1px solid var(--border); border-radius: 12px;
  cursor: pointer; transition: all 0.2s; margin-bottom: 10px;
  text-decoration: none; color: var(--text);
}
.quick-action:hover { background: rgba(0,212,170,0.05); border-color: rgba(0,212,170,0.2); }
.qa-icon { font-size: 22px; width: 44px; height: 44px; background: rgba(255,255,255,0.05); border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.qa-text { font-size: 14px; font-weight: 600; }
.qa-sub { font-size: 12px; color: var(--text-muted); }

/* TOAST */
.toast {
  position: fixed; bottom: 24px; right: 24px;
  background: rgba(0,212,170,0.15); border: 1px solid rgba(0,212,170,0.3);
  border-radius: 12px; padding: 14px 20px;
  color: var(--primary); font-size: 14px; font-weight: 500;
  z-index: 9999; display: none; align-items: center; gap: 10px;
  backdrop-filter: blur(10px);
}
.toast.show { display: flex; animation: toastIn 0.3s ease; }
@keyframes toastIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

/* MAP PLACEHOLDER */
.map-container {
  height: 280px; background: rgba(255,255,255,0.02);
  border-radius: 12px; position: relative; overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}
.map-dots span {
  position: absolute; width: 14px; height: 14px;
  border-radius: 50%; border: 2px solid white;
  cursor: pointer;
  animation: pulse-dot 2s ease-in-out infinite;
}
@keyframes pulse-dot {
  0%, 100% { box-shadow: 0 0 0 0 currentColor; opacity: 1; }
  50% { box-shadow: 0 0 0 8px transparent; opacity: 0.8; }
}

/* RESPONSIVE */
@media (max-width: 1024px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .grid-2 { grid-template-columns: 1fr; }
}
@media (max-width: 768px) {
  .sidebar { transform: translateX(-100%); }
  .sidebar.mobile-open { transform: translateX(0); }
  .main-content { margin-left: 0; }
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .page-content { padding: 16px; }
  .form-row { grid-template-columns: 1fr; }
}
</style>
