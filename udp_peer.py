"""
Stand-in for the UDP Monitor phone app, for testing udp_chat_server.py on
one machine (or from a second laptop on the same network).

Usage:  python udp_peer.py [server_ip] [server_port] [local_port]
        (defaults: 127.0.0.1, 12000, 12345; type /quit to exit)

In udp_chat_server.py, enter 127.0.0.1 and 12345 as the mobile IP/port,
or leave the IP blank to auto-detect.
"""

import socket
import sys
import threading

BUFFER_SIZE = 2048
ENCODING = "utf-8"
PROMPT = "🎤 "

print_lock = threading.Lock()


def show(text: str) -> None:
    with print_lock:
        print("\r" + " " * 60 + "\r" + text)
        print(PROMPT, end="", flush=True)


def main():
    server = (
        sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1",
        int(sys.argv[2]) if len(sys.argv) > 2 else 12000,
    )
    local_port = int(sys.argv[3]) if len(sys.argv) > 3 else 12345

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", local_port))
    sock.settimeout(0.5)
    running = threading.Event()
    running.set()

    def receive():
        while running.is_set():
            try:
                data, _ = sock.recvfrom(BUFFER_SIZE)
            except (socket.timeout, ConnectionResetError):
                continue
            except OSError:
                break
            show(f"📢 {data.decode(ENCODING, errors='replace')}")

    receiver = threading.Thread(target=receive, daemon=True)
    receiver.start()
    print(f"📱 Peer on port {local_port}, sending to {server[0]}:{server[1]}. /quit to exit.\n")

    while True:
        try:
            message = input(PROMPT)
        except (EOFError, KeyboardInterrupt):
            break
        if message.strip() == "/quit":
            break
        if message:
            sock.sendto(message.encode(ENCODING), server)

    running.clear()
    receiver.join()
    sock.close()
    print("\n👋 Bye!")


if __name__ == "__main__":
    main()
