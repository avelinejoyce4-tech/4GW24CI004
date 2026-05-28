<?php
// pages/login.php
session_start();
if (isset($_SESSION['user'])) {
    header("Location: /smartalloc/pages/" . $_SESSION['user']['role'] . "_dashboard.php");
    exit;
}

require_once '../config/db.php';
$error = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';
    $volunteer_id = trim($_POST['volunteer_id'] ?? '');

    $db = getDB();
    $stmt = $db->prepare("SELECT * FROM users WHERE email = ? AND status = 'active'");
    $stmt->bind_param('s', $email);
    $stmt->execute();
    $result = $stmt->get_result();
    $user = $result->fetch_assoc();

    // For demo: accept 'admin123' directly OR proper hash
    $valid = false;
    if ($user) {
        if ($password === 'admin123') $valid = true; // Demo shortcut
        elseif (password_verify($password, $user['password'])) $valid = true;
    }

    if ($valid) {
        // Volunteer ID check (optional field)
        if ($user['role'] === 'volunteer' && !empty($volunteer_id) && $user['volunteer_id'] !== $volunteer_id) {
            $error = 'Volunteer ID does not match our records.';
        } else {
            $_SESSION['user'] = [
                'id' => $user['id'],
                'name' => $user['name'],
                'email' => $user['email'],
                'role' => $user['role'],
                'volunteer_id' => $user['volunteer_id'],
            ];

            // Fetch NGO info if NGO role
            if ($user['role'] === 'ngo') {
                $ns = $db->prepare("SELECT * FROM ngos WHERE user_id = ?");
                $ns->bind_param('i', $user['id']);
                $ns->execute();
                $ngo = $ns->get_result()->fetch_assoc();
                $_SESSION['ngo'] = $ngo;
            }

            header("Location: /smartalloc/pages/" . $user['role'] . "_dashboard.php");
            exit;
        }
    } else {
        $error = 'Invalid email or password. Please try again.';
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Login - SmartAlloc</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --primary: #00D4AA;
    --primary-dark: #00A882;
    --secondary: #0A0A1A;
    --card-bg: rgba(255,255,255,0.04);
    --border: rgba(255,255,255,0.08);
    --text: #FFFFFF;
    --text-muted: rgba(255,255,255,0.45);
    --error: #FF4757;
    --glow: rgba(0,212,170,0.25);
  }

  body {
    background: #0A0A1A;
    min-height: 100vh;
    font-family: 'Space Grotesk', sans-serif;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text);
  }

  .bg-grid {
    position: fixed; inset: 0;
    background-image:
      linear-gradient(rgba(0,212,170,0.05) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,170,0.05) 1px, transparent 1px);
    background-size: 40px 40px;
  }

  .blob { position: fixed; border-radius: 50%; filter: blur(100px); opacity: 0.12; }
  .blob-1 { width: 500px; height: 500px; background: #00D4AA; top: -200px; right: -100px; }
  .blob-2 { width: 400px; height: 400px; background: #6C63FF; bottom: -150px; left: -100px; }

  .login-wrapper {
    width: 100%; max-width: 460px;
    padding: 20px;
    position: relative; z-index: 10;
    animation: slideUp 0.6s ease-out;
  }

  @keyframes slideUp {
    from { opacity: 0; transform: translateY(24px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .back-link {
    display: inline-flex; align-items: center; gap: 8px;
    color: var(--text-muted); font-size: 14px;
    text-decoration: none; margin-bottom: 32px;
    transition: color 0.2s;
  }
  .back-link:hover { color: var(--primary); }

  .logo-area {
    text-align: center; margin-bottom: 32px;
  }
  .logo-circle {
    width: 64px; height: 64px; border-radius: 20px;
    background: linear-gradient(135deg, var(--primary), #6C63FF);
    display: flex; align-items: center; justify-content: center;
    font-size: 28px; margin: 0 auto 16px;
    box-shadow: 0 0 30px var(--glow);
  }
  .app-name {
    font-family: 'Syne', sans-serif;
    font-size: 28px; font-weight: 800; letter-spacing: -1px;
  }
  .app-name span { color: var(--primary); }

  .card {
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
    border-radius: 24px;
    padding: 40px;
    backdrop-filter: blur(20px);
  }

  .card h2 {
    font-family: 'Syne', sans-serif;
    font-size: 26px; font-weight: 800;
    margin-bottom: 4px;
  }
  .card p {
    color: var(--text-muted); font-size: 14px;
    margin-bottom: 32px;
  }

  .form-group { margin-bottom: 20px; }
  .form-group label {
    display: block; font-size: 13px; font-weight: 500;
    color: var(--text-muted); margin-bottom: 8px;
    text-transform: uppercase; letter-spacing: 0.5px;
  }
  .form-group input {
    width: 100%;
    background: rgba(255,255,255,0.05);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 14px 16px;
    color: var(--text);
    font-size: 15px; font-family: inherit;
    transition: all 0.2s;
    outline: none;
  }
  .form-group input:focus {
    border-color: var(--primary);
    background: rgba(0,212,170,0.05);
    box-shadow: 0 0 0 3px var(--glow);
  }
  .form-group input::placeholder { color: var(--text-muted); }

  .optional-badge {
    font-size: 11px; color: var(--primary);
    background: rgba(0,212,170,0.1);
    padding: 2px 8px; border-radius: 20px;
    margin-left: 8px; font-weight: 400;
    text-transform: none; letter-spacing: 0;
  }

  .helper-text {
    font-size: 12px; color: var(--text-muted);
    margin-top: 6px;
  }

  .btn-login {
    width: 100%;
    background: linear-gradient(135deg, var(--primary), #00A882);
    border: none; border-radius: 12px;
    padding: 15px; color: #0A0A1A;
    font-size: 15px; font-weight: 700;
    font-family: inherit; cursor: pointer;
    transition: all 0.2s;
    margin-top: 8px;
    display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .btn-login:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 25px var(--glow);
  }

  .divider {
    display: flex; align-items: center; gap: 12px;
    margin: 24px 0; color: var(--text-muted); font-size: 13px;
  }
  .divider::before, .divider::after {
    content: ''; flex: 1; height: 1px;
    background: var(--border);
  }

  .register-link {
    text-align: center; font-size: 14px; color: var(--text-muted);
  }
  .register-link a {
    color: var(--primary); text-decoration: none; font-weight: 600;
  }
  .register-link a:hover { text-decoration: underline; }

  .error-box {
    background: rgba(255,71,87,0.1);
    border: 1px solid rgba(255,71,87,0.3);
    border-radius: 12px; padding: 12px 16px;
    color: var(--error); font-size: 14px;
    margin-bottom: 20px;
    display: flex; align-items: center; gap: 8px;
  }

  .demo-hints {
    margin-top: 20px;
    background: rgba(0,212,170,0.05);
    border: 1px solid rgba(0,212,170,0.15);
    border-radius: 12px;
    padding: 16px;
  }
  .demo-hints h4 { font-size: 12px; color: var(--primary); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
  .demo-row { display: flex; gap: 8px; align-items: center; font-size: 12px; color: var(--text-muted); margin-bottom: 6px; }
  .role-badge {
    padding: 2px 8px; border-radius: 6px; font-size: 11px; font-weight: 600;
    background: rgba(255,255,255,0.08); white-space: nowrap;
  }
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="blob blob-1"></div>
<div class="blob blob-2"></div>

<div class="login-wrapper">
  <a href="/smartalloc/index.php" class="back-link">← Back to Home</a>

  <div class="logo-area">
    <div class="logo-circle">🎯</div>
    <div class="app-name">Smart<span>Alloc</span></div>
  </div>

  <div class="card">
    <h2>Welcome Back!</h2>
    <p>Login to continue your journey</p>

    <?php if ($error): ?>
    <div class="error-box">⚠️ <?= htmlspecialchars($error) ?></div>
    <?php endif; ?>

    <?php if (isset($_GET['registered'])): ?>
    <div class="error-box" style="background:rgba(0,212,170,0.1);border-color:rgba(0,212,170,0.3);color:var(--primary);">
      ✅ Account created! Please login below.
    </div>
    <?php endif; ?>

    <form method="POST">
      <div class="form-group">
        <label>Email Address</label>
        <input type="email" name="email" placeholder="you@example.com" required
               value="<?= htmlspecialchars($_POST['email'] ?? '') ?>">
      </div>

      <div class="form-group">
        <label>Password</label>
        <input type="password" name="password" placeholder="••••••••••" required>
      </div>

      <div class="form-group">
        <label>Volunteer ID <span class="optional-badge">optional</span></label>
        <input type="text" name="volunteer_id" placeholder="e.g. VOL001">
        <div class="helper-text">Only required if you are a registered volunteer</div>
      </div>

      <button type="submit" class="btn-login">Login →</button>
    </form>

    <div class="divider">or</div>

    <div class="register-link">
      Don't have an account? <a href="/smartalloc/pages/register.php">Register here</a>
    </div>

    <div class="demo-hints">
      <h4>🔑 Demo Accounts</h4>
      <div class="demo-row"><span class="role-badge">👑 Admin</span> admin@smartalloc.com / admin123</div>
      <div class="demo-row"><span class="role-badge">👤 Volunteer</span> john@example.com / admin123</div>
      <div class="demo-row"><span class="role-badge">🏢 NGO</span> redcross@example.com / admin123</div>
    </div>
  </div>
</div>
</body>
</html>
