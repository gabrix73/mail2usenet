#!/home/m2usenet/venv/bin/python3
import sys
import email
import socks
import socket
import hashlib
import time
import random
from datetime import datetime, timedelta
import logging.handlers
from email.utils import formatdate  # Per header Date in stile RFC 2822

# AUMENTATO DA 16 A 26
HASHCASH_BITS = 16

NNTP_SERVER = 'peannyjkqwqfynd24p6dszvtchkq7hfkwymi5by5y332wmosy5dwfaqd.onion'
NNTP_PORT = 119
TOR_PROXY = ('127.0.0.1', 9050)
MAX_POST_SIZE = 10240
DELAY_CROSSPOST = 2

def generate_and_verify_hashcash(date_str, resource, bits=HASHCASH_BITS):
    version = "1"
    rand = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=8))
    counter = 0
    # Calcola quanti caratteri di 0 sono richiesti all'inizio dell'hash
    target = "0" * (bits // 4)
    while counter < 2_000_000:  # semplice limite di sicurezza
        stamp = f"{version}:{bits}:{date_str}:{resource}:::{rand}:{counter}"
        hash_val = hashlib.sha1(stamp.encode('utf-8')).hexdigest()
        if hash_val.startswith(target):
            return stamp
        counter += 1
    return None

def decode_payload(payload, charset):
    if payload is None:
        return ""
    if isinstance(payload, bytes):
        return payload.decode(charset, errors='replace')
    return payload

def send_via_tor(server, port, message, message_id):
    # Forza l'uso di Tor come proxy SOCKS5
    socks.set_default_proxy(socks.SOCKS5, TOR_PROXY[0], TOR_PROXY[1], True)
    socket.socket = socks.socksocket

    s = socks.socksocket()
    s.connect((server, port))
    welcome = s.recv(1024).decode('utf-8', 'replace')
    logger.info(f"Connected to NNTP: {welcome.strip()}")

    # Usa IHAVE
    sfile = s.makefile("rwb", buffering=0)
    ihave_cmd = f"IHAVE {message_id}\r\n".encode('utf-8')
    sfile.write(ihave_cmd)

    response = sfile.readline().decode('utf-8')
    logger.info("IHAVE response: " + response.strip())

    if not response.startswith("335"):
        logger.error("IHAVE rejected or failed: " + response.strip())
        return False

    sfile.write(message.encode('utf-8') + b"\r\n.\r\n")
    post_response = sfile.readline().decode('utf-8')
    logger.info("IHAVE post result: " + post_response.strip())

    sfile.write(b"QUIT\r\n")
    sfile.close()
    s.close()

    return post_response.startswith("235")

def main():
    raw_email = sys.stdin.read()
    if not raw_email:
        logger.error("No message received from STDIN.")
        sys.exit(1)

    msg = email.message_from_string(raw_email)
    subject = msg.get('Subject', 'No Subject')
    from_addr = msg.get('From', 'anon@unknown')
    newsgroups = msg.get('Newsgroups', 'alt.test')
    references = msg.get('References', '')
    pow_date = msg.get('X-PoW-Date', '').strip()

    # Verifica data PoW
    if not pow_date or len(pow_date) != 12:
        logger.error("Missing or invalid X-PoW-Date field.")
        sys.exit(1)

    # Finestra ±10 minuti
    try:
        pow_time = datetime.strptime(pow_date, "%Y%m%d%H%M")
        now_utc = datetime.utcnow()
        if abs((now_utc - pow_time).total_seconds()) > 600:
            logger.error("Proof-of-work timestamp too old or too far in the future.")
            sys.exit(1)
    except Exception:
        logger.error("Invalid PoW date format.")
        sys.exit(1)

    # Generazione e verifica Hashcash
    token = generate_and_verify_hashcash(pow_date, from_addr)
    if not token:
        logger.error("Failed Hashcash proof-of-work.")
        sys.exit(1)

    groups = [g.strip() for g in newsgroups.split(',') if g.strip()]
    if len(groups) > 3:
        logger.info("Too many newsgroups specified, limiting to 3.")
        groups = groups[:3]
    newsgroups_limited = ', '.join(groups)

    if len(groups) > 1:
        time.sleep(DELAY_CROSSPOST)

    # Estrai corpo
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

    body_ascii = body.encode('ascii', errors='replace').decode('ascii')

    # Costruisce un Message-ID univoco
    message_id = f"<{int(time.time())}.{random.randint(1000,9999)}@mail2usenet.local>"

    # Header standard + user-agent + date
    from email.utils import formatdate
    date_header = formatdate(localtime=False, usegmt=True)

    headers = [
        f"Message-ID: {message_id}",
        f"Date: {date_header}",
        f"From: {from_addr}",
        f"Newsgroups: {newsgroups_limited}",
        f"Subject: {subject}",
        f"Path: mail2usenet",
        "Organization: m2usenet gateway",
        f"X-Hashcash: {token}",
        "X-No-Archive: Yes",
        "Mime-Version: 1.0",
        "Content-Type: text/plain; charset=UTF-8",
        "Content-Transfer-Encoding: 7bit",
        "User-Agent: m2usenet v0.1.0"
    ]
    if references:
        headers.append(f"References: {references}")

    usenet_post = "\r\n".join(headers) + "\r\n\r\n" + body_ascii.strip()

    if len(usenet_post.encode('utf-8')) > MAX_POST_SIZE:
        logger.error("Post exceeds maximum allowed size.")
        sys.exit(1)

    success = send_via_tor(NNTP_SERVER, NNTP_PORT, usenet_post, message_id)
    if not success:
        logger.error("IHAVE post failed.")
        sys.exit(1)

if __name__ == '__main__':
    syslog = logging.handlers.SysLogHandler(address='/dev/log')
    formatter = logging.Formatter('%(name)s: %(levelname)s %(message)s')
    syslog.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    logger.addHandler(syslog)

    main()
    sys.exit(0)
