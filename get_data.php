<?php
// Set response header to JSON
header('Content-Type: application/json');

// --- Database Configuration ---
$db_host = 'localhost';
$db_name = 'sae24';
$db_user = 'sae24';
$db_pass = 'leo';

try {
    // Establish database connection using PDO
    $pdo = new PDO("mysql:host=$db_host;dbname=$db_name;charset=utf8", $db_user, $db_pass);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Retrieve the last 50 positions for plotting
    $stmt = $pdo->prepare("SELECT pos_x, pos_y, timestamp FROM positions ORDER BY timestamp DESC LIMIT 50");
    $stmt->execute();
    
    // For chronological display
    $positions = array_reverse($stmt->fetchAll(PDO::FETCH_ASSOC));
    
    // Reformat data for JavaScript consumption
    $output = [];
    foreach ($positions as $row) {
        $output[] = [
            'x' => (float)$row['pos_x'],        // Convert to float
            'y' => (float)$row['pos_y'],        // Convert to float
            'time' => $row['timestamp']         // Keep timestamp as string
        ];
    }
    
    // Return JSON response
    echo json_encode($output);

} catch (PDOException $e) {
    // Return error response with HTTP 500 status
    http_response_code(500);
    echo json_encode(['error' => 'Database connection error: ' . $e->getMessage()]);
}
?>
