#!/home/m2usenet/venv/bin/python3
import sys
import email
import logging
import socks
import socket
import ssl

NNTP_SERVER = 'paganini.bofh.team'
NNTP_PORT = 563
TOR_PROXY = ('127.0.0.1', 9050)

def decode_payload(payload, charset):
    if payload is None:
        return ""
    if isinstance(payload, bytes):
        return payload.decode(charset, errors='replace')
    return payload

def send_via_tor(server, port, message):
    # Setup proxy SOCKS5 Tor
    socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
    socket.socket = socks.socksocket

    # Connect via SSL
    with socket.create_connection((server, port)) as sock:
        with ssl.create_default_context().wrap_socket(sock, server_hostname=server) as s:
            # Read welcome message
            welcome = s.recv(1024).decode('utf-8', 'replace')
            logging.info(f"Connected to NNTP: {welcome}")

            sfile = s = ssl.SSLSocket.makefile(s, "rwb", buffering=0)

            # Send POST command
            sfile.write(b"POST\r\n")
            response = sfile.readline().decode('utf-8')
            if not response.startswith("340"):
                logging.error("Server does not accept POST: " + response)
                return False

            # Send message content
            sfile.write(message.encode('utf-8') + b"\r\n.\r\n")
            post_response = sfile.readline().decode('utf-8')
            logging.info("Posting response: " + post_response)

            # Close connection
            sfile.write(b"QUIT\r\n")
            sfile.close()

def main():
    raw_email = sys.stdin.read()
    if not raw_email:
        logging.error("No message received from STDIN.")
        sys.exit(1)

    msg = email.message_from_string(raw_email)

    subject = msg.get('Subject', 'No Subject')
    from_addr = msg.get('From', 'anonimo@esempio.com')
    newsgroups = msg.get('Newsgroups', 'alt.test')
    references = msg.get('References', '')

    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == 'text/plain' and part.get_content_disposition() in (None, 'inline'):
                charset = part.get_content_charset() or 'utf-8'
                payload = part.get_payload(decode=True)
                body += decode_payload(payload, charset)
    else:
        charset = msg.get_content_charset() or 'utf-8'
        payload = msg.get_payload(decode=True)
        body = decode_payload(payload, charset)

    # Include explicit MIME headers and allow multiple newsgroups and References
    usenet_post = (
        f"Mime-Version: 1.0\n"
        f"Content-Type: text/plain; charset=UTF-8\n"
        f"Content-Transfer-Encoding: 8bit\n"
        f"From: {msg.get('From', 'anonimo@esempio.com')}\n"
        f"Newsgroups: {msg.get('Newsgroups', 'alt.test')}\n"
        f"Subject: {msg.get('Subject', 'No Subject')}\n"
    )

    if references:
        usenet_post += f"References: {references}\n"

    usenet_post += "\n" + body

    # Encode explicitly UTF-8
    usenet_post_utf8 = usenet_post.encode('utf-8', errors='replace').decode('utf-8')

    try:
        send_via_tor(NNTP_SERVER, NNTP_PORT, usenet_post_utf8)
    except Exception as e:
        logging.error(f"Error sending post: {e}")
        sys.exit(1)

if __name__ == '__main__':
    logging.basicConfig(filename='/tmp/mail2news.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')
    main()
