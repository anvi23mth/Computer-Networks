"""
Multi-threaded TCP chat server.

* Every client connection is handled in its own thread, so many clients
  can chat at the same time.
* Messages are newline-terminated UTF-8 text. TCP is a byte stream, not a
  sequence of packets, so a delimiter is needed to know where one message
  ends and the next begins.
* The first line a client sends is its display name.
* A client's messages are shown on the server and relayed to every other
  client; anything typed on the server console goes to all clients.

Server commands:  /users  list connected clients
                  /quit   shut the server down

Usage:  python tcp_server.py [port]        (default port: 12001)
"""

import socket
import sys
import threading

HOST = "0.0.0.0"  # listen on every interface: Wi-Fi, hotspot, USB tethering, localhost
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


def get_local_ip() -> str:
    """IP address of the interface the OS would use for outgoing traffic.

    Connecting a UDP socket only looks up the routing table; no packet is sent.
    """
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return probe.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        probe.close()


def send_line(sock: socket.socket, text: str) -> None:
    """Send one message, terminated by a newline."""
    sock.sendall((text + "\n").encode(ENCODING))


def recv_lines(sock: socket.socket):
    """Yield complete messages from a TCP socket until the peer disconnects."""
    buffer = b""
    while True:
        chunk = sock.recv(BUFFER_SIZE)
        if not chunk:  # an empty read means the peer closed the connection
            return
        buffer += chunk
        # One recv() can hold several messages, or only part of one
        while b"\n" in buffer:
            line, buffer = buffer.split(b"\n", 1)
            yield line.decode(ENCODING, errors="replace").rstrip("\r")


class TCPChatServer:
    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.ip_address = get_local_ip()
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow an immediate restart on the same port after the server exits
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((HOST, self.port))
        self.clients = {}  # connection socket -> display name
        self.clients_lock = threading.Lock()  # guards self.clients across threads
        self.running = threading.Event()

    def start(self):
        self.socket.listen()
        self.running.set()
        self.print_details()
        threading.Thread(target=self.accept_clients, daemon=True).start()
        self.console()  # the main thread reads what the server operator types
        self.stop()

    def accept_clients(self):
        """Accept connections forever, starting one handler thread per client."""
        while self.running.is_set():
            try:
                conn, address = self.socket.accept()
            except OSError:
                break  # listening socket was closed during shutdown
            threading.Thread(
                target=self.handle_client, args=(conn, address), daemon=True
            ).start()

    def handle_client(self, conn: socket.socket, address):
        name = f"{address[0]}:{address[1]}"
        joined = False
        try:
            messages = recv_lines(conn)
            first = next(messages, None)
            if first is None:
                return  # disconnected before sending a name
            name = first.strip() or name

            with self.clients_lock:
                self.clients[conn] = name
                online = len(self.clients)
            joined = True
            show(f"🟢 {name} joined from {address[0]}:{address[1]}")
            send_line(conn, f"✅ Connected as {name} ({online} online). Type /quit to leave.")
            self.broadcast(f"🟢 {name} joined the chat", exclude=conn)

            for message in messages:
                if message.strip() == "/quit":
                    break
                if message:
                    show(f"📢 {name}: {message}")
                    self.broadcast(f"📢 {name}: {message}", exclude=conn)
        except OSError:
            pass  # connection reset, or closed during shutdown
        finally:
            with self.clients_lock:
                self.clients.pop(conn, None)
            conn.close()
            if joined and self.running.is_set():
                show(f"🔴 {name} left")
                self.broadcast(f"🔴 {name} left the chat")

    def broadcast(self, message: str, exclude=None):
        """Send a message to every connected client except `exclude`."""
        with self.clients_lock:
            targets = [conn for conn in self.clients if conn is not exclude]
        for conn in targets:
            try:
                send_line(conn, message)
            except OSError:
                pass  # that client's own thread will notice and clean up

    def console(self):
        """Read the server operator's input and send it to all clients."""
        while True:
            try:
                message = input(PROMPT)
            except (EOFError, KeyboardInterrupt):
                break
            command = message.strip()
            if command == "/quit":
                break
            if command == "/users":
                with self.clients_lock:
                    names = list(self.clients.values())
                print(f"👥 {len(names)} online: {', '.join(names) or '-'}")
            elif message:
                self.broadcast(f"🖥️  Server: {message}")

    def stop(self):
        self.running.clear()
        print("\n🛑 Shutting down...")
        self.broadcast("🛑 Server is shutting down")
        with self.clients_lock:
            connections = list(self.clients)
        for conn in connections:
            try:
                conn.shutdown(socket.SHUT_RDWR)  # wakes the handler thread blocked in recv()
            except OSError:
                pass
        try:
            self.socket.shutdown(socket.SHUT_RDWR)  # wakes accept() on Linux
        except OSError:
            pass
        self.socket.close()

    def print_details(self):
        print(f"✅ TCP chat server listening on port {self.port}")
        print(f"✅ Same machine   : python tcp_client.py 127.0.0.1 {self.port}")
        print(f"✅ Other devices  : python tcp_client.py {self.ip_address} {self.port}")
        print("ℹ️  Type to message everyone, /users to list clients, /quit to stop.\n")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    try:
        server = TCPChatServer(port)
    except OSError as error:
        print(f"❌ Could not start server on port {port}: {error}")
        sys.exit(1)
    server.start()
