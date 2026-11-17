# Socket Chat Apps: TCP Client-Server + Multi-threaded UDP Chat

A TCP client-server chat and a multi-threaded UDP chat server for real-time two-way messaging, including with an Android phone running **UDP Monitor**.

Python 3.8+, standard library only (no `netifaces` or `fcntl`), so it runs on Linux, macOS and Windows.

| File | What it does |
|---|---|
| `tcp_server.py` | Multi-client TCP chat server. Each client gets its own thread, and messages are relayed to everyone. |
| `tcp_client.py` | TCP client. A receive thread and the input loop run side by side, so you can send and receive at the same time. |
| `udp_chat_server.py` | Two-way UDP chat with the UDP Monitor phone app (Question 2). |
| `udp_peer.py` | Stands in for the phone so you can test the UDP chat without one. |

## TCP chat

```bash
python tcp_server.py                          # terminal 1 (port 12001)
python tcp_client.py                          # terminal 2, same machine
python tcp_client.py <server-ip> 12001        # from another device on the network
```

- **Server console:** type to message all clients, `/users` lists who is online, `/quit` shuts the server down.
- **Client:** type to chat, `/quit` to leave.

## UDP chat with your phone

1. Put the phone and PC on the same network: same Wi-Fi, the phone's hotspot, or USB tethering.
2. Run `python udp_chat_server.py`. It prints the **Server IP** and **Port** (12000).
3. In UDP Monitor, set the **remote address/port** to that IP and port, and pick a **local port**.
4. Back on the PC, enter the phone's IPv4 (top-left of the app) and that local port.
   You can also leave the IP blank, and the server will reply to whoever messages it first.
5. Chat both ways. `/quit` exits.

**Test without a phone** (two terminals):

```bash
python udp_chat_server.py                     # enter 127.0.0.1 and 12345
python udp_peer.py 127.0.0.1 12000 12345
```

## How it works

- **TCP** is connection-oriented and is a byte stream. The server `listen()`s, `accept()`s each client and starts a thread for it. Because a single `recv()` may hold part of a message or several messages, each message ends with `\n` and the receiver buffers until it has a full line.
- **UDP** has no connection. Each `sendto()` is one datagram, addressed explicitly, and `recvfrom()` returns the data along with the sender's address. That address is how the server can auto-detect the phone.
- **Threading:** `recv`/`recvfrom` and `input()` both block, so receiving runs in a background thread while the main thread waits on the keyboard. That gives real-time two-way messaging. A `threading.Lock` keeps clients' messages from interleaving on screen, and a `threading.Event` signals shutdown.

## Fixes over the original `server.py`

| Original | Problem | Now |
|---|---|---|
| Interface found by the first name starting with `w` and an `ioctl` call | Breaks on USB tethering (`usb0`), Ethernet, macOS (`en0`) and Windows (no `fcntl`). Crashes if no `w*` interface exists. | Uses a routing-table lookup to find the IP, and binds to `0.0.0.0` so every interface works |
| `__del__` joins threads | `AttributeError` if `start()` never ran, and non-daemon threads stop Ctrl+C from exiting | `stop()` shuts down cleanly. `/quit`, Ctrl+C and EOF all work. |
| `data.decode()` | Crashes on bytes that aren't valid UTF-8 | `errors="replace"` |
| Phone IP/port typed blindly | A typo crashes `sendto` later | Input is validated, and auto-detect is available |
| No handling for Windows UDP quirk | `ConnectionResetError` from `recvfrom` after the phone app closes | Ignored, so receiving continues |

## Troubleshooting

- **Phone and PC can't reach each other:** campus or office Wi-Fi often blocks device-to-device traffic (client isolation). Use the phone's hotspot or USB tethering instead.
- **Nothing arrives on the PC:** allow Python through the firewall (Windows Defender Firewall, or `sudo ufw allow 12000/udp` on Linux).
- **"Address already in use":** another copy is still running. Close it or pass a different port, e.g. `python udp_chat_server.py 12005`.
