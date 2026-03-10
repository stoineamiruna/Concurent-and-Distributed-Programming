#!/usr/bin/env python3

import socket
import hashlib
import argparse
import struct

HDR_FMT  = '!IIH'
HDR_SIZE = struct.calcsize(HDR_FMT)
END_SEQ  = 0xFFFFFFFF
MAX_PKT  = 65535 + HDR_SIZE


def run_server(host, port, method):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4 * 1024 * 1024)
    sock.bind((host, port))
    sock.settimeout(15.0)
    print(f"[UDP Server] Astept pe {host}:{port} | method={method}")

    chunks   = {}
    tot_exp  = None
    cli_addr = None
    total_b  = 0
    total_m  = 0

    try:
        while True:
            try:
                pkt, addr = sock.recvfrom(MAX_PKT)
            except socket.timeout:
                print("[UDP Server] Timeout.")
                break

            if cli_addr is None:
                cli_addr = addr
                print(f"[UDP Server] Client: {addr}")

            if len(pkt) < HDR_SIZE:
                continue

            seq, tot, dlen = struct.unpack(HDR_FMT, pkt[:HDR_SIZE])
            data = pkt[HDR_SIZE: HDR_SIZE + dlen]

            if seq == END_SEQ:
                tot_exp = tot
                break

            tot_exp = tot
            if seq not in chunks:
                chunks[seq]  = data
                total_b += len(data)
                total_m += 1

            if method == 'stop-and-wait':
                sock.sendto(struct.pack('!I', seq), addr)

    except Exception as e:
        print(f"[UDP Server] Eroare: {e}")

    h = hashlib.sha256()
    recv_cnt = len(chunks)
    lost = 0

    if tot_exp is not None:
        lost = tot_exp - recv_cnt
        for i in range(tot_exp):
            if i in chunks:
                h.update(chunks[i])
    else:
        for i in sorted(chunks.keys()):
            h.update(chunks[i])

    print(f"\n{'='*50}")
    print(f"[UDP Server] Protocol        : UDP")
    print(f"[UDP Server] Method          : {method}")
    print(f"[UDP Server] Mesaje primite  : {total_m}")
    print(f"[UDP Server] Bytes primiti   : {total_b}")
    print(f"[UDP Server] Pachete pierdute: {lost} / {tot_exp}")
    print(f"[UDP Server] SHA-256         : {h.hexdigest()}")
    print(f"{'='*50}\n")

    sock.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',   default='0.0.0.0')
    ap.add_argument('--port',   type=int, default=5002)
    ap.add_argument('--method', choices=['streaming', 'stop-and-wait'], default='streaming')
    args = ap.parse_args()
    run_server(args.host, args.port, args.method)
