"""
TCP chat client for tcp_server.py.

A background thread prints incoming messages while the main thread reads
the keyboard, so sending and receiving happen at the same time.

Usage:  python tcp_client.py [server_ip] [port]
        (defaults: 127.0.0.1 and 12001; type /quit to leave)
"""

import socket
import sys
import threading

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 12001
BUFFER_SIZE = 2048
ENCODING = "utf-8"
PROMPT = "🎤 "

print_lock = threading.Lock()


def show(text: str) -> None:
    """Print a message from a background thread without garbling the input prompt."""
    with print_lock:
        print("\r" + " " * 60 + "\r" + text)
        print(PROMPT, end="", flush=True)


def send_line(sock: socket.socket, text: str) -> None:
    """Send one message, terminated by a newline."""
    sock.sendall((text + "\n").encode(ENCODING))


def recv_lines(sock: socket.socket):
    """Yield complete messages from a TCP socket until the peer disconnects."""
    buffer = b""
    while True:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:
            return
        buffer += chunk
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            yield line.decode(ENCODING, errors="replace").rstrip("\r")


class TCPChatClient:
    def __init__(self, host: str, port: int, name: str):
        self.address = (host, port)
        self.name = name
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connected = threading.Event()

    def start(self):
        self.socket.settimeout(5)  # don't hang forever on a wrong IP
        self.socket.connect(self.address)  # TCP three-way handshake happens here
        self.socket.settimeout(None)
        self.connected.set()
        send_line(self.socket, self.name)  # first line = display name
        threading.Thread(target=self.receive, daemon=True).start()
        self.send()
        self.stop()

    def receive(self):
        """Background thread: print everything the server sends."""
        try:
            for message in recv_lines(self.socket):
                show(message)
        except OSError:
            pass
        if self.connected.is_set():  # the server went away (we didn't quit)
            self.connected.clear()
            show("🔌 Disconnected from server. Press Enter to exit.")

    def send(self):
        """Main thread: read the keyboard and send each line."""
        while self.connected.is_set():
            try:
                message = input(PROMPT)
            except (EOFError, KeyboardInterrupt):
                break
            if not self.connected.is_set() or message.strip() == "/quit":
                break
            if message:
                try:
                    send_line(self.socket, message)
                except OSError:
                    print("❌ Connection lost.")
                    break

    def stop(self):
        if self.connected.is_set():
            self.connected.clear()
            try:
                send_line(self.socket, "/quit")  # tell the server we're leaving
            except OSError:
                pass
        try:
            self.socket.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.socket.close()
        print("\n👋 Bye!")


if __name__ == "__main__":
    host = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_HOST
    port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
    try:
        name = input("👤 Your name: ").strip() or "anonymous"
    except (EOFError, KeyboardInterrupt):
        sys.exit(0)

    client = TCPChatClient(host, port, name)
    try:
        client.start()
    except OSError as error:  # connection refused, timed out, unreachable...
        print(f"❌ Could not connect to {host}:{port}: {error}")
        sys.exit(1)
