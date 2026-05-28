<?php
// pages/register.php
session_start();
require_once '../config/db.php';
$error = '';
$success = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $name = trim($_POST['name'] ?? '');
    $email = trim($_POST['email'] ?? '');
    $password = $_POST['password'] ?? '';
    $role = $_POST['role'] ?? 'volunteer';
    $phone = trim($_POST['phone'] ?? '');
    $location = trim($_POST['location'] ?? '');
    $skills = trim($_POST['skills'] ?? '');
    $org_name = trim($_POST['org_name'] ?? '');

    if (empty($name) || empty($email) || empty($password) || empty($role)) {
        $error = 'Please fill all required fields.';
    } elseif (strlen($password) < 6) {
        $error = 'Password must be at least 6 characters.';
    } else {
        $db = getDB();
        $check = $db->prepare("SELECT id FROM users WHERE email = ?");
        $check->bind_param('s', $email);
        $check->execute();
        if ($check->get_result()->num_rows > 0) {
            $error = 'Email already registered. Please login.';
        } else {
            $hashed = password_hash($password, PASSWORD_BCRYPT);
            $vol_id = ($role === 'volunteer') ? 'VOL' . strtoupper(substr(md5(microtime()), 0, 5)) : null;

            $stmt = $db->prepare("INSERT INTO users (name, email, password, role, volunteer_id, phone, location, skills) VALUES (?, ?, ?, ?, ?, ?, ?, ?)");
            $stmt->bind_param('ssssssss', $name, $email, $hashed, $role, $vol_id, $phone, $location, $skills);

            if ($stmt->execute()) {
                $new_id = $db->insert_id;
                if ($role === 'ngo' && !empty($org_name)) {
                    $ns = $db->prepare("INSERT INTO ngos (user_id, org_name, address) VALUES (?, ?, ?)");
                    $ns->bind_param('iss', $new_id, $org_name, $location);
                    $ns->execute();
                }
                header('Location: /smartalloc/pages/login.php?registered=1');
                exit;
            } else {
                $error = 'Registration failed. Please try again.';
            }
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Register - SmartAlloc</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  :root { --primary: #00D4AA; --border: rgba(255,255,255,0.08); --glow: rgba(0,212,170,0.25); }
  body { background: #0A0A1A; min-height: 100vh; font-family: 'Space Grotesk', sans-serif; display: flex; align-items: center; justify-content: center; color: #fff; padding: 20px; }
  .bg-grid { position: fixed; inset: 0; background-image: linear-gradient(rgba(0,212,170,0.05) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,170,0.05) 1px, transparent 1px); background-size: 40px 40px; }
  .blob { position: fixed; border-radius: 50%; filter: blur(100px); opacity: 0.1; }
  .blob-1 { width: 400px; height: 400px; background: #00D4AA; top: -100px; left: -100px; }
  .blob-2 { width: 300px; height: 300px; background: #6C63FF; bottom: -100px; right: -100px; }
  .register-wrapper { width: 100%; max-width: 500px; position: relative; z-index: 10; animation: slideUp 0.6s ease-out; }
  @keyframes slideUp { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: translateY(0); } }
  .back-link { display: inline-flex; align-items: center; gap: 8px; color: rgba(255,255,255,0.45); font-size: 14px; text-decoration: none; margin-bottom: 24px; transition: color 0.2s; }
  .back-link:hover { color: var(--primary); }
  .logo-area { text-align: center; margin-bottom: 24px; }
  .logo-circle { width: 56px; height: 56px; border-radius: 16px; background: linear-gradient(135deg, var(--primary), #6C63FF); display: flex; align-items: center; justify-content: center; font-size: 24px; margin: 0 auto 12px; box-shadow: 0 0 30px var(--glow); }
  .app-name { font-family: 'Syne', sans-serif; font-size: 24px; font-weight: 800; }
  .app-name span { color: var(--primary); }
  .card { background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 24px; padding: 36px; backdrop-filter: blur(20px); }
  .card h2 { font-family: 'Syne', sans-serif; font-size: 22px; font-weight: 800; margin-bottom: 4px; }
  .card p { color: rgba(255,255,255,0.45); font-size: 14px; margin-bottom: 28px; }
  .form-group { margin-bottom: 18px; }
  .form-group label { display: block; font-size: 12px; font-weight: 500; color: rgba(255,255,255,0.45); margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.5px; }
  .form-group input, .form-group select, .form-group textarea { width: 100%; background: rgba(255,255,255,0.05); border: 1px solid var(--border); border-radius: 10px; padding: 12px 14px; color: #fff; font-size: 14px; font-family: inherit; outline: none; transition: all 0.2s; }
  .form-group input:focus, .form-group select:focus, .form-group textarea:focus { border-color: var(--primary); background: rgba(0,212,170,0.05); box-shadow: 0 0 0 3px var(--glow); }
  .form-group select option { background: #1a1a2e; }
  .form-group input::placeholder, .form-group textarea::placeholder { color: rgba(255,255,255,0.25); }
  .role-selector { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin-bottom: 18px; }
  .role-option { display: none; }
  .role-option + label { display: flex; flex-direction: column; align-items: center; gap: 6px; padding: 16px 8px; background: rgba(255,255,255,0.03); border: 1px solid var(--border); border-radius: 12px; cursor: pointer; transition: all 0.2s; font-size: 13px; text-align: center; }
  .role-option:checked + label { border-color: var(--primary); background: rgba(0,212,170,0.08); color: var(--primary); }
  .role-emoji { font-size: 24px; }
  .btn-register { width: 100%; background: linear-gradient(135deg, var(--primary), #00A882); border: none; border-radius: 12px; padding: 14px; color: #0A0A1A; font-size: 15px; font-weight: 700; font-family: inherit; cursor: pointer; transition: all 0.2s; margin-top: 8px; }
  .btn-register:hover { transform: translateY(-2px); box-shadow: 0 8px 25px var(--glow); }
  .login-link { text-align: center; font-size: 14px; color: rgba(255,255,255,0.45); margin-top: 20px; }
  .login-link a { color: var(--primary); text-decoration: none; font-weight: 600; }
  .error-box { background: rgba(255,71,87,0.1); border: 1px solid rgba(255,71,87,0.3); border-radius: 10px; padding: 12px 16px; color: #FF4757; font-size: 14px; margin-bottom: 16px; }
  .optional { font-size: 11px; color: var(--primary); background: rgba(0,212,170,0.1); padding: 1px 7px; border-radius: 20px; margin-left: 6px; font-weight: 400; text-transform: none; letter-spacing: 0; }
  .ngo-fields { display: none; }
  .role-label { font-size: 12px; font-weight: 600; color: rgba(255,255,255,0.6); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 8px; }
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="blob blob-1"></div>
<div class="blob blob-2"></div>

<div class="register-wrapper">
  <a href="/smartalloc/pages/login.php" class="back-link">← Back to Login</a>

  <div class="logo-area">
    <div class="logo-circle">🎯</div>
    <div class="app-name">Smart<span>Alloc</span></div>
  </div>

  <div class="card">
    <h2>Create Account</h2>
    <p>Join the SmartAlloc community</p>

    <?php if ($error): ?>
    <div class="error-box">⚠️ <?= htmlspecialchars($error) ?></div>
    <?php endif; ?>

    <form method="POST" id="regForm">
      <div class="role-label">I am a...</div>
      <div class="role-selector">
        <input type="radio" name="role" id="r-volunteer" value="volunteer" class="role-option" checked>
        <label for="r-volunteer"><span class="role-emoji">👤</span>Volunteer</label>

        <input type="radio" name="role" id="r-ngo" value="ngo" class="role-option">
        <label for="r-ngo"><span class="role-emoji">🏢</span>NGO</label>

        <input type="radio" name="role" id="r-admin" value="admin" class="role-option">
        <label for="r-admin"><span class="role-emoji">👑</span>Admin</label>
      </div>

      <div class="form-group">
        <label>Full Name</label>
        <input type="text" name="name" placeholder="Your full name" required value="<?= htmlspecialchars($_POST['name'] ?? '') ?>">
      </div>

      <div class="form-group">
        <label>Email</label>
        <input type="email" name="email" placeholder="you@example.com" required value="<?= htmlspecialchars($_POST['email'] ?? '') ?>">
      </div>

      <div class="form-group">
        <label>Password</label>
        <input type="password" name="password" placeholder="Min 6 characters" required>
      </div>

      <div class="form-group">
        <label>Phone <span class="optional">optional</span></label>
        <input type="tel" name="phone" placeholder="+91 98765 43210" value="<?= htmlspecialchars($_POST['phone'] ?? '') ?>">
      </div>

      <div class="form-group">
        <label>Location / City</label>
        <input type="text" name="location" placeholder="e.g. Chennai, Tamil Nadu" value="<?= htmlspecialchars($_POST['location'] ?? '') ?>">
      </div>

      <div class="form-group" id="skills-field">
        <label>Skills <span class="optional">for volunteers</span></label>
        <input type="text" name="skills" placeholder="e.g. medical, driving, teaching" value="<?= htmlspecialchars($_POST['skills'] ?? '') ?>">
      </div>

      <div class="form-group ngo-fields" id="org-name-field">
        <label>Organisation Name</label>
        <input type="text" name="org_name" placeholder="e.g. Red Cross Society" value="<?= htmlspecialchars($_POST['org_name'] ?? '') ?>">
      </div>

      <button type="submit" class="btn-register">Create Account →</button>
    </form>

    <div class="login-link">Already have an account? <a href="/smartalloc/pages/login.php">Login</a></div>
  </div>
</div>

<script>
  const radios = document.querySelectorAll('input[name="role"]');
  const ngoFields = document.querySelector('.ngo-fields');
  const skillsField = document.getElementById('skills-field');

  radios.forEach(r => r.addEventListener('change', () => {
    const val = document.querySelector('input[name="role"]:checked').value;
    ngoFields.style.display = val === 'ngo' ? 'block' : 'none';
    skillsField.style.display = val === 'volunteer' ? 'block' : 'none';
  }));
</script>
</body>
</html>
