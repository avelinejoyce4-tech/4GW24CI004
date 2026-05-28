<?php
// index.php - Splash Screen
session_start();
if (isset($_SESSION['user'])) {
    $role = $_SESSION['user']['role'];
    header("Location: /smartalloc/pages/{$role}_dashboard.php");
    exit;
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SmartAlloc - Smart Resource Allocation</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Syne:wght@700;800&display=swap" rel="stylesheet">
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }

  :root {
    --primary: #00D4AA;
    --secondary: #1A1A2E;
    --accent: #FF6B35;
    --text: #FFFFFF;
    --glow: rgba(0,212,170,0.4);
  }

  body {
    background: #0A0A1A;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Space Grotesk', sans-serif;
    overflow: hidden;
  }

  .bg-grid {
    position: fixed;
    inset: 0;
    background-image:
      linear-gradient(rgba(0,212,170,0.06) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,212,170,0.06) 1px, transparent 1px);
    background-size: 40px 40px;
    animation: gridMove 20s linear infinite;
  }

  @keyframes gridMove {
    0% { transform: translateY(0); }
    100% { transform: translateY(40px); }
  }

  .blob {
    position: fixed;
    border-radius: 50%;
    filter: blur(80px);
    opacity: 0.15;
    animation: blobFloat 8s ease-in-out infinite;
  }
  .blob-1 { width: 400px; height: 400px; background: var(--primary); top: -100px; left: -100px; }
  .blob-2 { width: 300px; height: 300px; background: #6C63FF; bottom: -50px; right: -50px; animation-delay: -4s; }

  @keyframes blobFloat {
    0%, 100% { transform: translateY(0) scale(1); }
    50% { transform: translateY(-30px) scale(1.05); }
  }

  .splash-container {
    text-align: center;
    position: relative;
    z-index: 10;
    animation: fadeIn 0.8s ease-out;
  }

  @keyframes fadeIn {
    from { opacity: 0; transform: translateY(30px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .logo-ring {
    width: 120px;
    height: 120px;
    margin: 0 auto 24px;
    position: relative;
  }

  .logo-ring svg {
    animation: spin 8s linear infinite;
  }

  @keyframes spin {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
  }

  .logo-icon {
    position: absolute;
    inset: 20px;
    background: linear-gradient(135deg, var(--primary), #6C63FF);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 36px;
    box-shadow: 0 0 40px var(--glow);
  }

  .app-name {
    font-family: 'Syne', sans-serif;
    font-size: 52px;
    font-weight: 800;
    color: white;
    letter-spacing: -2px;
    line-height: 1;
  }

  .app-name span {
    color: var(--primary);
    text-shadow: 0 0 30px var(--glow);
  }

  .tagline {
    color: rgba(255,255,255,0.5);
    font-size: 16px;
    font-weight: 300;
    margin-top: 8px;
    letter-spacing: 3px;
    text-transform: uppercase;
  }

  .loading-bar {
    width: 200px;
    height: 2px;
    background: rgba(255,255,255,0.1);
    border-radius: 2px;
    margin: 40px auto 0;
    overflow: hidden;
  }

  .loading-fill {
    height: 100%;
    background: linear-gradient(90deg, var(--primary), #6C63FF);
    border-radius: 2px;
    animation: load 2.5s ease-in-out forwards;
  }

  @keyframes load {
    from { width: 0%; }
    to { width: 100%; }
  }

  .dots {
    display: flex;
    gap: 8px;
    justify-content: center;
    margin-top: 16px;
  }

  .dot {
    width: 6px; height: 6px;
    background: var(--primary);
    border-radius: 50%;
    animation: bounce 1.4s ease-in-out infinite;
    opacity: 0.4;
  }
  .dot:nth-child(2) { animation-delay: 0.2s; }
  .dot:nth-child(3) { animation-delay: 0.4s; }

  @keyframes bounce {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40% { transform: scale(1); opacity: 1; }
  }
</style>
</head>
<body>
<div class="bg-grid"></div>
<div class="blob blob-1"></div>
<div class="blob blob-2"></div>

<div class="splash-container">
  <div class="logo-ring">
    <svg viewBox="0 0 120 120" width="120" height="120">
      <circle cx="60" cy="60" r="54" fill="none" stroke="rgba(0,212,170,0.3)" stroke-width="2" stroke-dasharray="8 4"/>
    </svg>
    <div class="logo-icon">🎯</div>
  </div>
  <div class="app-name">Smart<span>Alloc</span></div>
  <div class="tagline">Smart Resource Allocation</div>
  <div class="loading-bar"><div class="loading-fill"></div></div>
  <div class="dots">
    <div class="dot"></div>
    <div class="dot"></div>
    <div class="dot"></div>
  </div>
</div>

<script>
  setTimeout(() => {
    window.location.href = '/smartalloc/pages/login.php';
  }, 3000);
</script>
</body>
</html>
