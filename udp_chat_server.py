"""
Multi-threaded UDP chat server for two-way messaging with a phone running
the UDP Monitor app. Use udp_peer.py to test without a phone.

How to connect:
  1. Put the phone and PC on the same network: the same Wi-Fi, the phone's
     hotspot, or USB tethering.
  2. Run this script. It prints the PC's IP address and port.
  3. In UDP Monitor, set the remote address/port to the PC's IP/port, and
     note the phone's IPv4 address (top-left) and its local port.
  4. Enter the phone's IP and port here, or leave the IP blank and the
     server picks up the phone's address from its first message.

Two threads run in parallel: a background thread blocks on recvfrom() and
prints whatever arrives, while the main thread reads the keyboard and
sends each line with sendto(). Type /quit to exit.

Usage:  python udp_chat_server.py [port]      (default port: 12000)
"""

import socket
import sys
import threading

DEFAULT_PORT = 12000
BUFFER_SIZE = 2048
ENCODING = "utf-8"
PROMPT = "🎤 "


class Server:
    def __init__(self, port: int = DEFAULT_PORT):
        self.port = port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # 0.0.0.0 = every interface, so it works however the phone is connected
        self.socket.bind(("0.0.0.0", self.port))
        # recvfrom() wakes up every 0.5 s so the receive thread can notice /quit
        self.socket.settimeout(0.5)
        self.ip_address = self.get_local_ip()
        self.client = None  # (phone_ip, phone_port)
        self.running = threading.Event()
        self.print_lock = threading.Lock()
        self.receive_thread = None

    @staticmethod
    def get_local_ip() -> str:
        """IP of the interface used for outgoing traffic.

        Works for Wi-Fi, hotspot and USB tethering on Linux, macOS and Windows.
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

    def show(self, text: str):
        """Print an incoming message without garbling the input prompt."""
        with self.print_lock:
            print("\r" + " " * 60 + "\r" + text)
            print(PROMPT, end="", flush=True)

    # Background thread: receive data from the phone and print it
    def receive(self):
        while self.running.is_set():
            try:
                data, address = self.socket.recvfrom(BUFFER_SIZE)
            except socket.timeout:
                continue  # nothing arrived; check self.running again
            except ConnectionResetError:
                continue  # Windows reports an ICMP "port unreachable" here; ignore it
            except OSError:
                break  # socket closed

            if self.client is None:  # auto-detect mode: reply to whoever writes first
                self.client = address
                self.show(f"📱 Phone detected at {address[0]}:{address[1]}")

            text = data.decode(ENCODING, errors="replace")
            sender = "" if address == self.client else f"  (from {address[0]}:{address[1]})"
            self.show(f"📢 {text}{sender}")

    # Main thread: send typed messages to the phone
    def send(self):
        while self.running.is_set():
            try:
                message = input(PROMPT)
            except (EOFError, KeyboardInterrupt):
                break
            if message.strip().lower() in ("/quit", "/exit"):
                break
            if not message:
                continue
            if self.client is None:
                print("⚠️  Phone address not known yet. Send a message from the phone first.")
                continue
            try:
                self.socket.sendto(message.encode(ENCODING), self.client)
            except OSError as error:
                print(f"❌ Send failed: {error}")

    def start(self):
        self.running.set()
        self.receive_thread = threading.Thread(target=self.receive, daemon=True)
        self.receive_thread.start()
        self.send()
        self.stop()

    def stop(self):
        self.running.clear()
        if self.receive_thread is not None:
            self.receive_thread.join()
        self.socket.close()
        print("\n👋 Chat closed.")

    # Tell the server the phone's IP address and local port
    def set_client(self, client_ip: str, client_port):
        socket.inet_aton(client_ip)  # raises OSError if the IP is malformed
        port = int(client_port)
        if not 0 < port < 65536:
            raise ValueError("port out of range")
        self.client = (client_ip, port)

    def print_details(self):
        print(f"✅ Server IP         : {self.ip_address}")
        print(f"✅ Server Port       : {self.port}")
        print("ℹ️  Enter these as the remote address/port in UDP Monitor.\n")


def ask_phone_address(server: Server):
    while True:
        ip = input("📱 Enter Mobile IP   (blank = auto-detect): ").strip()
        if not ip:
            print("⏳ Waiting for the first message from the phone...\n")
            return
        port = input("📱 Enter Mobile Port : ").strip()
        try:
            server.set_client(ip, port)
            print(f"✅ Chatting with {ip}:{port}. Type /quit to exit.\n")
            return
        except (OSError, ValueError):
            print("❌ Invalid IP or port, try again.")


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PORT
    try:
        server = Server(port)
    except OSError as error:
        print(f"❌ Could not start server on port {port}: {error}")
        sys.exit(1)

    server.print_details()
    try:
        ask_phone_address(server)
    except (EOFError, KeyboardInterrupt):
        server.socket.close()
        print("\n👋 Bye!")
        sys.exit(0)
    server.start()
