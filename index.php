<?php
if ($_SERVER["REQUEST_METHOD"] === "POST") {
    $from = $_POST["from"] ?? "";
    $newsgroups = $_POST["newsgroups"] ?? "";
    $subject = $_POST["subject"] ?? "";
    $references = $_POST["references"] ?? "";
    $body = $_POST["body"] ?? "";
    $pow_date = $_POST["pow_date"] ?? "";

    if (!empty($from) && !empty($newsgroups) && !empty($body) && !empty($pow_date)) {
        $msg  = "From: $from\n";
        $msg .= "Newsgroups: $newsgroups\n";
        if (!empty($subject))    $msg .= "Subject: $subject\n";
        if (!empty($references)) $msg .= "References: $references\n";
        $msg .= "X-PoW-Date: $pow_date\n";
        $msg .= "Content-Type: text/plain; charset=UTF-8\n";
        $msg .= "Mime-Version: 1.0\n";
        $msg .= "Content-Transfer-Encoding: 7bit\n\n";
        $msg .= $body;

        $script = '/home/m2usenet/m2usenet.py';

        $descriptorspec = [
            0 => ["pipe", "r"],
            1 => ["pipe", "w"],
            2 => ["pipe", "w"]
        ];

        $process = proc_open($script, $descriptorspec, $pipes);

        if (is_resource($process)) {
            fwrite($pipes[0], $msg);
            fclose($pipes[0]);

            $stdout = stream_get_contents($pipes[1]);
            $stderr = stream_get_contents($pipes[2]);
            fclose($pipes[1]);
            fclose($pipes[2]);

            $return_value = proc_close($process);

            if (!empty($stderr)) {
                $encoded = urlencode($stderr);
                header("Location: " . $_SERVER['PHP_SELF'] . "?status=error&msg=$encoded");
                exit;
            } else {
                $encoded = urlencode($stdout);
                header("Location: " . $_SERVER['PHP_SELF'] . "?status=ok&msg=$encoded");
                exit;
            }
        } else {
            $encoded = urlencode("Unable to execute mail2usenet script.");
            header("Location: " . $_SERVER['PHP_SELF'] . "?status=error&msg=$encoded");
            exit;
        }
    } else {
        $encoded = urlencode("All fields are required, including the proof-of-work date.");
        header("Location: " . $_SERVER['PHP_SELF'] . "?status=error&msg=$encoded");
        exit;
    }
}
?>

<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>mail2usenet gateway</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f6f8fa;
            color: #333;
            padding: 2rem;
        }
        header, footer {
            margin-bottom: 20px;
        }
        nav a {
            margin-right: 15px;
            text-decoration: none;
            color: #0366d6;
            font-weight: bold;
        }
        nav a:hover {
            text-decoration: underline;
        }
        h2 {
            color: #0366d6;
        }
        form {
            background: #ffffff;
            padding: 20px;
            border-radius: 6px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            max-width: 600px;
        }
        input[type="text"], textarea {
            width: 100%;
            padding: 10px;
            border: 1px solid #ccc;
            border-radius: 4px;
            margin-top: 6px;
            margin-bottom: 16px;
            resize: vertical;
        }
        input[type="submit"] {
            background-color: #0366d6;
            color: white;
            padding: 10px 18px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
        }
        input[type="submit"]:hover {
            background-color: #024f9d;
        }
        .info {
            background-color: #e9f5ff;
            border-left: 4px solid #0366d6;
            padding: 10px;
            margin-bottom: 20px;
        }
        .output, .error {
            margin-top: 30px;
            padding: 15px;
            border-radius: 4px;
            font-family: monospace;
        }
        .output {
            background-color: #e6ffed;
            border: 1px solid #2ecc71;
        }
        .error {
            background-color: #ffe6e6;
            border: 1px solid #e74c3c;
        }
        footer {
            margin-top: 40px;
            text-align: center;
        }
        .github-link img {
            height: 20px;
            vertical-align: middle;
        }
    </style>
</head>
<body>
    <header>
        <nav>
            <a href="https://m2usenet.virebent.art">Home</a>
        </nav>
    </header>

    <h2>Post to Usenet via mail2usenet gateway</h2>
    <div class="info">
        <p>This gateway requires a basic <strong>proof-of-work</strong> to reduce spam. Please provide the current UTC date and time as a token in the format <code>YYYYMMDDHHMM</code>.</p>
        <p>The system will use this value to generate and validate a Hashcash token automatically using your email address. <strong>Note:</strong> The token is only valid for a short time (±10 minutes). This ensures that tokens cannot be reused later and guarantees that the proof-of-work was performed just before sending. Make sure to provide the current UTC time in the format <code>YYYYMMDDHHMM</code>.</p>
        <p><strong>Current UTC time:</strong> <code><?php echo gmdate("YmdHi"); ?></code></p>
    </div>

    <?php if (isset($_GET['status']) && isset($_GET['msg'])): ?>
        <div class="<?php echo $_GET['status'] === 'ok' ? 'output' : 'error'; ?>">
            <strong><?php echo $_GET['status'] === 'ok' ? 'Response:' : 'Error:'; ?></strong><br>
            <?php echo nl2br(htmlspecialchars(urldecode($_GET['msg']))); ?>
        </div>
    <?php endif; ?>

    <form method="POST">
        From:<br>
        <input type="text" name="from" required><br>

        Newsgroups:<br>
        <input type="text" name="newsgroups" required><br>

        Subject:<br>
        <input type="text" name="subject"><br>

        References:<br>
        <input type="text" name="references"><br>

        Message:<br>
        <textarea name="body" rows="10" required></textarea><br>

        Proof-of-Work Date (UTC):<br>
        <input type="text" name="pow_date" placeholder="e.g. 202504041145" required><br>

        <input type="submit" value="Send Message">
    </form>

    <footer>
        <a class="github-link" href="https://github.com/gabrix73/mail2usenet.git" target="_blank">
            <img src="https://github.githubassets.com/images/modules/logos_page/GitHub-Mark.png" alt="GitHub Logo">
            View on GitHub
        </a>
    </footer>
</body>
</html>
