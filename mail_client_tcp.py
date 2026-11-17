import socket
import ssl
import base64
import os


SMTP_SERVER = "smtp.cc.iitk.ac.in"   # the smtp address of iik
SMTP_PORT = 25                       # 25 for smtp

USERNAME = "yourADDRESS"    #sender's address and  password
PASSWORD = "*******"

FROM_ADDR = USERNAME
TO_ADDR = "TOaddress"        #sender's address
CC_ADDR = "***"
BCC_ADDR = "***"

SUBJECT = "First mail"
BODY = "Hello!\nAll is well\n"

ATTACHMENT_PATH = r"address/of/your/file.file_type"          #You have to change according to your attachment location
BOUNDARY = "BOUNDARY12345"


def recv(sock):
    return sock.recv(1024).decode()

def send(sock, msg):
    print("C:", msg.strip())
    sock.sendall((msg + "\r\n").encode())


client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)      #Creating TCP socket and binding it
client.connect((SMTP_SERVER, SMTP_PORT))

print(recv(client))

# START SMTP
send(client, "EHLO localhost")
print(recv(client))

# Start TLS
send(client, "STARTTLS")
print(recv(client))

context = ssl.create_default_context()
client = context.wrap_socket(client, server_hostname=SMTP_SERVER)

send(client, "EHLO localhost")
print(recv(client))

# Authentication
send(client, "AUTH LOGIN")
print(recv(client))

send(client, base64.b64encode(USERNAME.encode()).decode())
print(recv(client))

send(client, base64.b64encode(PASSWORD.encode()).decode())
print(recv(client))

# MAIL FROM
send(client, f"MAIL FROM:{FROM_ADDR}")
print(recv(client))

# RCPT TO
send(client, f"RCPT TO:<{TO_ADDR}>")        #I am sending to only one address
print(recv(client))                              #If you  want to send it to cc,bcc then turn on a for loop for all addresses

# DATA
send(client, "DATA")
print(recv(client))

#Header
headers = f"""From: {FROM_ADDR}
To: {TO_ADDR}
Cc: {CC_ADDR}
Subject: {SUBJECT}
MIME-Version: 1.0
Content-Type: multipart/mixed; boundary={BOUNDARY}

"""

client.sendall(headers.encode())

#Body
body = f"""--{BOUNDARY}
Content-Type: text/plain

{BODY}
"""
client.sendall(body.encode())

#   Attachment
if os.path.exists(ATTACHMENT_PATH):
    with open(ATTACHMENT_PATH, "rb") as f:
        encoded = base64.b64encode(f.read()).decode()

    attachment = f"""
--{BOUNDARY}
Content-Type: application/octet-stream
Content-Disposition: attachment; filename="{os.path.basename(ATTACHMENT_PATH)}"
Content-Transfer-Encoding: base64

{encoded}
"""
    client.sendall(attachment.encode())

# END Message
client.sendall(f"\r\n--{BOUNDARY}--\r\n\r\n.\r\n".encode())     #At the end a '.' should be sent to end the message

print(recv(client))

send(client, "QUIT")         #At the end quit it
print(recv(client))

client.close()