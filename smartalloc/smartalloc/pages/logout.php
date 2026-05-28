<?php
// pages/logout.php
session_start();
session_destroy();
header('Location: /smartalloc/pages/login.php');
exit;
?>
