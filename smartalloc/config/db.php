<?php
// =============================================
// SmartAlloc - Database Configuration
// File: config/db.php
// =============================================

define('DB_HOST', 'localhost');
define('DB_USER', 'root');        // Your WAMP MySQL username (default: root)
define('DB_PASS', '');            // Your WAMP MySQL password (default: empty)
define('DB_NAME', 'smartalloc');

// Anthropic API Key for AI features
define('ANTHROPIC_API_KEY', 'your-anthropic-api-key-here'); // Replace with your key

function getDB() {
    static $conn = null;
    if ($conn === null) {
        $conn = new mysqli(DB_HOST, DB_USER, DB_PASS, DB_NAME);
        if ($conn->connect_error) {
            die(json_encode(['error' => 'DB Connection failed: ' . $conn->connect_error]));
        }
        $conn->set_charset('utf8');
    }
    return $conn;
}

// Session helper
function getCurrentUser() {
    if (session_status() === PHP_SESSION_NONE) session_start();
    return $_SESSION['user'] ?? null;
}

function requireLogin($role = null) {
    if (session_status() === PHP_SESSION_NONE) session_start();
    if (!isset($_SESSION['user'])) {
        header('Location: /smartalloc/pages/login.php');
        exit;
    }
    if ($role && $_SESSION['user']['role'] !== $role) {
        header('Location: /smartalloc/pages/login.php?error=unauthorized');
        exit;
    }
}
?>
