<?php
// api/ai_parse.php - Calls Anthropic API to extract structured need data
session_start();
require_once '../config/db.php';
header('Content-Type: application/json');

if (!isset($_SESSION['user'])) {
    echo json_encode(['error' => 'Unauthorized']); exit;
}

$input = json_decode(file_get_contents('php://input'), true);
$text = trim($input['text'] ?? '');

if(empty($text)) {
    echo json_encode(['error' => 'No text provided']); exit;
}

// Call Anthropic API
$api_key = ANTHROPIC_API_KEY;

$prompt = "You are a humanitarian data extraction assistant. Extract structured information from this field report or need description.

Text: \"$text\"

Extract and return ONLY a valid JSON object with these exact fields:
{
  \"title\": \"Short descriptive title for this need (max 10 words)\",
  \"location\": \"Specific location mentioned or 'Not specified'\",
  \"problem_type\": \"one of: food, medical, shelter, water, education, other\",
  \"urgency\": number from 1 to 5 (5=critical emergency, 4=high, 3=medium, 2=low, 1=minimal),
  \"estimated_people\": \"number or range of people affected, or 'Unknown'\",
  \"description\": \"Clean one-sentence summary of the need\",
  \"keywords\": [\"up to 5 relevant keywords\"]
}

Rules:
- urgency 5: life-threatening, no food/water for 24h+, medical emergency
- urgency 4: severe need, large number affected, deadline today
- urgency 3: moderate need, needs attention within days
- urgency 2: low urgency, planning stage
- Return ONLY the JSON, no other text, no markdown.";

$payload = json_encode([
    'model' => 'claude-sonnet-4-20250514',
    'max_tokens' => 500,
    'messages' => [['role' => 'user', 'content' => $prompt]]
]);

$ch = curl_init('https://api.anthropic.com/v1/messages');
curl_setopt_array($ch, [
    CURLOPT_RETURNTRANSFER => true,
    CURLOPT_POST => true,
    CURLOPT_POSTFIELDS => $payload,
    CURLOPT_HTTPHEADER => [
        'Content-Type: application/json',
        'x-api-key: ' . $api_key,
        'anthropic-version: 2023-06-01'
    ],
    CURLOPT_TIMEOUT => 15
]);

$response = curl_exec($ch);
$http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

if(!$response || $http_code !== 200) {
    // Fallback: rule-based parsing
    $parsed = ruleBased($text);
    echo json_encode(['success' => true, 'parsed' => $parsed, 'source' => 'rule-based']);
    exit;
}

$data = json_decode($response, true);
$content = $data['content'][0]['text'] ?? '';

// Clean up response (remove markdown if any)
$content = preg_replace('/```json|```/', '', $content);
$content = trim($content);

$parsed = json_decode($content, true);
if(!$parsed || !isset($parsed['title'])) {
    $parsed = ruleBased($text);
    echo json_encode(['success' => true, 'parsed' => $parsed, 'source' => 'rule-based-fallback']);
    exit;
}

echo json_encode(['success' => true, 'parsed' => $parsed, 'source' => 'ai']);

function ruleBased($text) {
    $lower = strtolower($text);
    $types = ['food','medical','shelter','water','education'];
    $problem_type = 'other';
    foreach($types as $t) { if(strpos($lower,$t)!==false) { $problem_type=$t; break; } }
    // Urgency keywords
    $urgency = 3;
    if(preg_match('/urgent|critical|emergency|immediately|life.threaten|dying|no food|no water/i',$text)) $urgency=5;
    elseif(preg_match('/severe|desperate|serious|today|hours/i',$text)) $urgency=4;
    elseif(preg_match('/need|require|request|help/i',$text)) $urgency=3;
    elseif(preg_match('/plan|future|soon|week/i',$text)) $urgency=2;
    // Numbers
    preg_match('/(\d+)\s*(?:families|people|persons|adults|children|kids)/i',$text,$nm);
    $people = isset($nm[1]) ? $nm[1].' people' : 'Unknown';
    // Location
    preg_match('/(?:near|at|in|around)\s+([A-Z][a-zA-Z\s]{2,30}?)(?:\.|,|$)/m',$text,$lm);
    $location = isset($lm[1]) ? trim($lm[1]) : 'Location not specified';
    $title = ucfirst($problem_type).' Need - '.$location;
    return compact('title','location','problem_type','urgency','estimated_people','description') + [
        'estimated_people'=>$people,
        'description'=>substr($text,0,150),
        'keywords'=>[$problem_type,'volunteer','help','community']
    ];
}
?>
