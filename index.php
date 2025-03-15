<?php
// Abilita la visualizzazione completa degli errori per il debug (solo in ambiente di test)
error_reporting(E_ALL);
ini_set('display_errors', 1);

$result = null;

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    // Decodifica corretta degli input per UTF-8
    $user_name  = html_entity_decode($_POST['user_name'], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $user_email = filter_input(INPUT_POST, 'user_email', FILTER_VALIDATE_EMAIL);
    $newsgroups = html_entity_decode($_POST['newsgroups'], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $subject    = html_entity_decode($_POST['subject'], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $message    = html_entity_decode($_POST['message'], ENT_QUOTES | ENT_HTML5, 'UTF-8');
    $references = html_entity_decode($_POST['references'], ENT_QUOTES | ENT_HTML5, 'UTF-8');

    if (!$user_name || !$user_email || !$newsgroups || !$subject || !$message) {
        $result = "<p style='color: red; text-align: center;'>Please fill in all required fields correctly.</p>";
    } else {
        // Imposta l'indirizzo di destinazione per Postfix
        $to = 'mail2news@localhost';

        // Costruisci gli header della mail
        $headers = "From: {$user_name} <{$user_email}>\r\n" .
                   "Mime-Version: 1.0\r\n" .
                   "Content-Type: text/plain; charset=UTF-8\r\n" .
                   "Content-Transfer-Encoding: 7bit\r\n" .
                   "X-No-archive: yes\r\n" .
                   "Newsgroups: {$newsgroups}\r\n";
        if ($references) {
            $headers .= "References: {$references}\r\n";
        }

        // Invia la mail usando la funzione nativa
        if (mail($to, $subject, $message, $headers)) {
            $result = "<p style='color: green; text-align: center;'>Post sent successfully!</p>";
        } else {
            $result = "<p style='color: red; text-align: center;'>Error sending the post.</p>";
        }
    }
}
?>
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Send Usenet Post</title>
  <style>
    body { 
      font-family: Arial, sans-serif; 
      background-color: #f5f5f5; 
      display: flex; 
      flex-direction: column; 
      align-items: center; 
      min-height: 100vh; 
      margin: 0; 
    }
    header { 
      width: 100%; 
      background-color: #4CAF50; 
      padding: 20px; 
      color: white; 
      text-align: center; 
    }
    .container { 
      width: 90%; 
      max-width: 600px; 
      background: white; 
      padding: 20px; 
      margin-top: 30px; 
      border-radius: 8px; 
      box-shadow: 0 2px 4px rgba(0,0,0,0.1); 
    }
    input, textarea { 
      width: 100%; 
      padding: 10px; 
      margin-top: 5px; 
      border: 1px solid #ccc; 
      border-radius: 4px; 
    }
    input[type="submit"] { 
      background: #4CAF50; 
      color: white; 
      cursor: pointer; 
      padding: 12px; 
      border: none; 
      border-radius: 4px; 
      margin-top: 15px; 
    }
    footer { 
      margin-top: 30px; 
      text-align: center; 
      color: #555; 
    }
    @media (max-width: 600px) { 
      .container { padding: 10px; } 
    }
  </style>
</head>
<body>
  <header>
    <nav>
      <a href="https://yamn.virebent.art/">HOME</a>
    </nav>
  </header>

  <div class="container">
    <h1>Send Usenet Post</h1>
    <?php if ($result !== null): ?>
        <?= $result ?>
        <p style="text-align: center;"><a href="https://m2usenet.virebent.art/">Back to Home</a></p>
    <?php else: ?>
    <form method="post">
      <label>User Name:</label>
      <input type="text" name="user_name" required>
      <label>Email:</label>
      <input type="email" name="user_email" required>
      <label>Newsgroups:</label>
      <input type="text" name="newsgroups" required>
      <label>Subject:</label>
      <input type="text" name="subject" required>
      <label>Message:</label>
      <textarea name="message" rows="10" required></textarea>
      <label>References:</label>
      <input type="text" name="references">
      <input type="submit" value="Send Post">
    </form>
    <?php endif; ?>
  </div>

  <footer>
    &copy; 2025 Fuck Design. All rights reserved.
  </footer>
</body>
</html>
