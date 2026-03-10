#!/usr/bin/env python3

import socket
import hashlib
import argparse
import struct
import time


def recv_exact(sock, n):
    buf = b''
    while len(buf) < n:
        chunk = sock.recv(n - len(buf))
        if not chunk:
            return None
        buf += chunk
    return buf


def run_client(host, port, size_mb, bsize, method):
    total = size_mb * 1024 * 1024

    base = bytes(i % 256 for i in range(min(bsize, 65536)))
    tmpl = (base * (bsize // len(base) + 1))[:bsize]

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((host, port))
    print(f"[TCP Client] Conectat la {host}:{port}")
    print(f"[TCP Client] Transfer: {size_mb} MB | block={bsize} B | method={method}")

    h = hashlib.sha256()
    sent_b = 0
    sent_m = 0
    rem = total

    start = time.time()

    while rem > 0:
        clen = min(bsize, rem)
        data = tmpl[:clen]

        h.update(data)
        sock.sendall(struct.pack('!I', clen) + data)

        sent_b += clen
        sent_m += 1
        rem -= clen

        if method == 'stop-and-wait':
            ack = recv_exact(sock, 3)
            if ack != b'ACK':
                print(f"[TCP Client] ACK gresit: {ack}")

    sock.sendall(struct.pack('!I', 0))

    elapsed = time.time() - start
    tput = sent_b / elapsed / 1024 / 1024

    print(f"\n{'='*50}")
    print(f"[TCP Client] Protocol        : TCP")
    print(f"[TCP Client] Method          : {method}")
    print(f"[TCP Client] Block size      : {bsize} B")
    print(f"[TCP Client] Mesaje trimise  : {sent_m}")
    print(f"[TCP Client] Bytes trimisi   : {sent_b}")
    print(f"[TCP Client] Timp transfer   : {elapsed:.4f} s")
    print(f"[TCP Client] Throughput      : {tput:.2f} MB/s")
    print(f"[TCP Client] SHA-256         : {h.hexdigest()}")
    print(f"{'='*50}\n")

    sock.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',       default='127.0.0.1')
    ap.add_argument('--port',       type=int, default=5001)
    ap.add_argument('--size',       type=int, default=500)
    ap.add_argument('--block-size', type=int, default=1000, dest='block_size')
    ap.add_argument('--method',     choices=['streaming', 'stop-and-wait'], default='streaming')
    args = ap.parse_args()
    run_client(args.host, args.port, args.size, args.block_size, args.method)
