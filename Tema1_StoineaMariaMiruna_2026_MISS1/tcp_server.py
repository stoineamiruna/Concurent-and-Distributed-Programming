#!/usr/bin/env python3

import socket
import hashlib
import argparse
import struct


def recv_exact(sock, n):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def run_server(host, port, method):
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(1)
    print(f"[TCP Server] Astept conexiune pe {host}:{port} | method={method}")

    conn, addr = srv.accept()
    print(f"[TCP Server] Client conectat: {addr}")

    h = hashlib.sha256()
    total_b = 0
    total_m = 0

    try:
        while True:
            hdr = recv_exact(conn, 4)
            if hdr is None:
                break
            mlen = struct.unpack('!I', hdr)[0]

            if mlen == 0:
                break

            data = recv_exact(conn, mlen)
            if data is None:
                break

            h.update(data)
            total_b += len(data)
            total_m += 1

            if method == 'stop-and-wait':
                conn.sendall(b'ACK')

    except Exception as e:
        print(f"[TCP Server] Eroare: {e}")
    finally:
        conn.close()
        srv.close()

    print(f"\n{'='*50}")
    print(f"[TCP Server] Protocol        : TCP")
    print(f"[TCP Server] Method          : {method}")
    print(f"[TCP Server] Mesaje primite  : {total_m}")
    print(f"[TCP Server] Bytes primiti   : {total_b}")
    print(f"[TCP Server] SHA-256         : {h.hexdigest()}")
    print(f"{'='*50}\n")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',   default='0.0.0.0')
    ap.add_argument('--port',   type=int, default=5001)
    ap.add_argument('--method', choices=['streaming', 'stop-and-wait'], default='streaming')
    args = ap.parse_args()
    run_server(args.host, args.port, args.method)
