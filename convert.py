#!/home/m2usenet/venv/bin/python3
import sys
import email
import logging
import socks
import socket
from time import sleep
from stem import Signal
from stem.control import Controller
import hashlib
import time
import random

# Costanti di configurazione
NNTP_SERVER = 'peannyjkqwqfynd24p6dszvtchkq7hfkwymi5by5y332wmosy5dwfaqd.onion'
NNTP_PORT = 119  # Connessione in chiaro, senza SSL
TOR_PROXY = ('127.0.0.1', 9050)
MAX_POST_SIZE = 10240          # Dimensione massima del post in byte (10 KB)
DELAY_CROSSPOST = 2            # Delay in secondi se si tratta di crosspost
HASHCASH_BITS = 16             # Difficoltà del token hashcash

def generate_hashcash(resource, bits=HASHCASH_BITS):
    """
    Genera un token hashcash semplice.
    Formato: "1:bits:date:resource:::{rand}:{counter}"
    """
    version = "1"
    date = time.strftime("%y%m%d%H%M%S", time.gmtime())
    rand = ''.join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", k=8))
    counter = 0
    target = "0" * (bits // 4)  # per bits multipli di 4
    while True:
        stamp = f"{version}:{bits}:{date}:{resource}:::{rand}:{counter}"
        hash_val = hashlib.sha1(stamp.encode('utf-8')).hexdigest()
        if hash_val.startswith(target):
            return stamp
        counter += 1

def renew_tor_identity():
    """
    Richiede a Tor una nuova identità tramite Stem (NEWNYM).
    Assicurati che il ControlPort di Tor (di default 9051) sia abilitato e configurato.
    """
    try:
        with Controller.from_port(port=9051) as controller:
            # Usa l'autenticazione via cookie; il file cookie è solitamente /var/lib/tor/control_auth_cookie
            controller.authenticate(password='password-in-chiaro-nohash')
            controller.signal(Signal.NEWNYM)
            logging.info("Nuova identità Tor richiesta.")
            sleep(45)  # Attendi il cambio circuito
    except Exception as e:
        logging.error("Impossibile richiedere nuova identità Tor: " + str(e))

def decode_payload(payload, charset):
    if payload is None:
        return ""
    if isinstance(payload, bytes):
        return payload.decode(charset, errors='replace')
    return payload

def send_via_tor(server, port, message):
    # Imposta il proxy SOCKS5 per Tor con rdns=True (risoluzione DNS remota)
    socks.set_default_proxy(socks.SOCKS5, TOR_PROXY[0], TOR_PROXY[1], True)
    socket.socket = socks.socksocket

    # Crea direttamente una socket PySocks e connettiti (evita socket.create_connection)
    s = socks.socksocket()
    s.connect((server, port))    

    # Legge il messaggio di benvenuto del server NNTP
    welcome = s.recv(1024).decode('utf-8', 'replace')
    logging.info(f"Connesso a NNTP: {welcome}")

    sfile = s.makefile("rwb", buffering=0)

    # Invia il comando POST
    sfile.write(b"POST\r\n")
    response = sfile.readline().decode('utf-8')
    if not response.startswith("340"):
        logging.error("Il server non accetta il POST: " + response)
        return False

    # Invia il contenuto del post
    sfile.write(message.encode('utf-8') + b"\r\n.\r\n")
    post_response = sfile.readline().decode('utf-8')
    logging.info("Risposta al POST: " + post_response)

    # Chiude la connessione con il comando QUIT
    sfile.write(b"QUIT\r\n")
    sfile.close()
    s.close()

    return True

def main():
    raw_email = sys.stdin.read()
    if not raw_email:
        logging.error("Nessun messaggio ricevuto da STDIN.")
        sys.exit(1)

    msg = email.message_from_string(raw_email)

    # Recupera gli header necessari
    subject = msg.get('Subject', 'No Subject')
    from_addr = msg.get('From', 'anonimo@esempio.com')
    newsgroups = msg.get('Newsgroups', 'alt.test')
    references = msg.get('References', '')

    # Gestione dei newsgroups: limita a massimo 3
    groups = [g.strip() for g in newsgroups.split(',') if g.strip()]
    if len(groups) > 3:
        logging.info("Troppe newsgroups specificate, limitando a 3.")
        groups = groups[:3]
    newsgroups_limited = ', '.join(groups)

    # Se si tratta di crosspost (più di un newsgroup), inserisce un delay per evitare il ratelimit
    if len(groups) > 1:
        sleep(DELAY_CROSSPOST)

    # Estrae il corpo del messaggio in testo semplice
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

    # Forza il corpo a essere testo ASCII (eventuali caratteri non-ASCII vengono sostituiti)
    body_ascii = body.encode('ascii', errors='replace').decode('ascii')

    # Genera il token hashcash basato sul mittente
    hashcash_token = generate_hashcash(from_addr)

    # Costruisce il post Usenet con le intestazioni richieste
    usenet_post = (
        "Mime-Version: 1.0\n"
        "Content-Type: text/plain; charset=UTF-8\n"
        "Content-Transfer-Encoding: 7bit\n"
        f"From: {from_addr}\n"
        f"Newsgroups: {newsgroups_limited}\n"
        f"Subject: {subject}\n"
        f"X-Hashcash: {hashcash_token}\n"
    )
    if references:
        usenet_post += f"References: {references}\n"
    usenet_post += "\n" + body_ascii

    # Verifica che il post non superi la dimensione massima consentita
    if len(usenet_post.encode('utf-8')) > MAX_POST_SIZE:
        logging.error("Il post supera la dimensione massima consentita.")
        sys.exit(1)

    # Forza l'encoding in ASCII
    usenet_post_ascii = usenet_post.encode('ascii', errors='replace').decode('ascii')

    # Invio del post; se fallisce (ad es. errore 441), richiede nuova identità Tor e riprova
    success = send_via_tor(NNTP_SERVER, NNTP_PORT, usenet_post_ascii)
    if not success:
        logging.error("Invio del post fallito, richiedo nuova identità Tor e riprovo.")
        renew_tor_identity()
        success = send_via_tor(NNTP_SERVER, NNTP_PORT, usenet_post_ascii)
        if not success:
            logging.error("Invio del post fallito dopo il cambio di identità.")
            sys.exit(1)

if __name__ == '__main__':
    logging.basicConfig(filename='/tmp/mail2news.log', level=logging.INFO,
                        format='%(asctime)s %(levelname)s:%(message)s')
    main()
