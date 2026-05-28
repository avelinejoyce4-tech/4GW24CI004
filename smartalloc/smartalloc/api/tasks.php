<?php
// api/tasks.php
session_start();
require_once '../config/db.php';
header('Content-Type: application/json');

if (!isset($_SESSION['user'])) {
    echo json_encode(['error' => 'Unauthorized']); exit;
}

$user = $_SESSION['user'];
$db = getDB();
$action = $_POST['action'] ?? $_GET['action'] ?? '';

function jsonOut($data) { echo json_encode($data); exit; }

switch($action) {
    case 'create':
        $title = trim($_POST['title'] ?? '');
        $location = trim($_POST['location'] ?? '');
        $type = $_POST['problem_type'] ?? 'other';
        $urgency = intval($_POST['urgency'] ?? 3);
        $desc = trim($_POST['description'] ?? '');
        $vol_needed = intval($_POST['volunteers_needed'] ?? 5);

        if(empty($title) || empty($location)) jsonOut(['error'=>'Title and location required']);

        $stmt = $db->prepare("INSERT INTO tasks (title, description, location, problem_type, urgency, volunteers_needed, created_by) VALUES (?, ?, ?, ?, ?, ?, ?)");
        $stmt->bind_param('ssssiii', $title, $desc, $location, $type, $urgency, $vol_needed, $user['id']);
        if($stmt->execute()) {
            $task_id = $db->insert_id;
            // Notify admin
            $admin = $db->query("SELECT id FROM users WHERE role='admin' LIMIT 1")->fetch_assoc();
            if($admin) {
                $msg = "New task created: $title by {$user['name']}";
                $nq = $db->prepare("INSERT INTO notifications (user_id, message) VALUES (?,?)");
                $nq->bind_param('is', $admin['id'], $msg);
                $nq->execute();
            }
            jsonOut(['success'=>true, 'task_id'=>$task_id]);
        } else {
            jsonOut(['error'=>'Failed to create: '.$db->error]);
        }

    case 'update':
        $id = intval($_POST['id'] ?? 0);
        $title = trim($_POST['title'] ?? '');
        $location = trim($_POST['location'] ?? '');
        $type = $_POST['problem_type'] ?? 'other';
        $urgency = intval($_POST['urgency'] ?? 3);
        $desc = trim($_POST['description'] ?? '');
        $vol_needed = intval($_POST['volunteers_needed'] ?? 5);

        $stmt = $db->prepare("UPDATE tasks SET title=?, description=?, location=?, problem_type=?, urgency=?, volunteers_needed=? WHERE id=?");
        $stmt->bind_param('sssssii', $title, $desc, $location, $type, $urgency, $vol_needed, $id);
        if($stmt->execute()) jsonOut(['success'=>true]);
        else jsonOut(['error'=>$db->error]);

    case 'delete':
        $id = intval($_POST['id'] ?? $_GET['id'] ?? 0);
        $stmt = $db->prepare("DELETE FROM tasks WHERE id=?");
        $stmt->bind_param('i', $id);
        if($stmt->execute()) jsonOut(['success'=>true]);
        else jsonOut(['error'=>$db->error]);

    case 'assign':
        $task_id = intval($_POST['task_id'] ?? 0);
        $vol_id = intval($_POST['volunteer_id'] ?? 0);
        if(!$task_id || !$vol_id) jsonOut(['error'=>'Missing parameters']);

        // Check if already assigned
        $check = $db->prepare("SELECT id FROM assignments WHERE task_id=? AND volunteer_id=?");
        $check->bind_param('ii', $task_id, $vol_id);
        $check->execute();
        if($check->get_result()->num_rows > 0) jsonOut(['error'=>'Already assigned']);

        $stmt = $db->prepare("INSERT INTO assignments (task_id, volunteer_id, status) VALUES (?, ?, 'accepted')");
        $stmt->bind_param('ii', $task_id, $vol_id);
        if($stmt->execute()) {
            // Update task status
            $db->query("UPDATE tasks SET status='in-progress' WHERE id=$task_id AND status='open'");
            // Notify volunteer
            $task = $db->query("SELECT title FROM tasks WHERE id=$task_id")->fetch_assoc();
            $msg = "You have been assigned to: {$task['title']}";
            $nq = $db->prepare("INSERT INTO notifications (user_id, message) VALUES (?,?)");
            $nq->bind_param('is', $vol_id, $msg);
            $nq->execute();
            jsonOut(['success'=>true]);
        } else jsonOut(['error'=>$db->error]);

    case 'progress':
        $assign_id = intval($_POST['assign_id'] ?? 0);
        $progress = intval($_POST['progress'] ?? 0);
        $stmt = $db->prepare("UPDATE assignments SET progress=?, status='in-progress' WHERE id=?");
        $stmt->bind_param('ii', $progress, $assign_id);
        if($stmt->execute()) jsonOut(['success'=>true]);
        else jsonOut(['error'=>$db->error]);

    case 'complete':
        $assign_id = intval($_POST['assign_id'] ?? 0);
        $task_id = intval($_POST['task_id'] ?? 0);
        $stmt = $db->prepare("UPDATE assignments SET status='completed', progress=100, completed_at=NOW() WHERE id=?");
        $stmt->bind_param('i', $assign_id);
        $stmt->execute();
        // Check if all volunteers done
        $pending = $db->query("SELECT COUNT(*) as c FROM assignments WHERE task_id=$task_id AND status != 'completed'")->fetch_assoc()['c'];
        if($pending == 0) $db->query("UPDATE tasks SET status='completed' WHERE id=$task_id");
        jsonOut(['success'=>true]);

    case 'list':
        $status = $_GET['status'] ?? null;
        $type = $_GET['type'] ?? null;
        $q = "SELECT * FROM tasks WHERE 1";
        if($status) $q .= " AND status='".addslashes($status)."'";
        if($type) $q .= " AND problem_type='".addslashes($type)."'";
        $q .= " ORDER BY urgency DESC, created_at DESC";
        $result = $db->query($q)->fetch_all(MYSQLI_ASSOC);
        jsonOut(['success'=>true, 'tasks'=>$result]);

    default:
        jsonOut(['error'=>'Unknown action']);
}
?>
