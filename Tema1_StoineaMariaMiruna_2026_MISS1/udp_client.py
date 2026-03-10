#!/usr/bin/env python3

import socket
import hashlib
import argparse
import struct
import time

HDR_FMT    = '!IIH'
HDR_SIZE   = struct.calcsize(HDR_FMT)
END_SEQ    = 0xFFFFFFFF
MAX_RETRY  = 10
ACK_TO     = 1.0


def run_client(host, port, size_mb, bsize, method):
    if bsize > 65507 - HDR_SIZE:
        bsize = 65507 - HDR_SIZE

    total   = size_mb * 1024 * 1024
    n_chunks = (total + bsize - 1) // bsize

    base = bytes(i % 256 for i in range(min(bsize, 65536)))
    tmpl = (base * (bsize // len(base) + 1))[:bsize]

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    if method == 'stop-and-wait':
        sock.settimeout(ACK_TO)

    print(f"[UDP Client] Trimit la {host}:{port}")
    print(f"[UDP Client] {size_mb} MB | block={bsize} B | chunks={n_chunks} | method={method}")

    h      = hashlib.sha256()
    sent_b = 0
    sent_m = 0
    rem    = total
    seq    = 0
    lost   = 0

    start = time.time()

    while rem > 0:
        clen = min(bsize, rem)
        data = tmpl[:clen]
        hdr  = struct.pack(HDR_FMT, seq, n_chunks, clen)
        pkt  = hdr + data

        h.update(data)

        if method == 'streaming':
            sock.sendto(pkt, (host, port))
            sent_b += clen
            sent_m += 1
        else:
            ok = False
            for _ in range(MAX_RETRY):
                sock.sendto(pkt, (host, port))
                try:
                    ack, _ = sock.recvfrom(4)
                    if len(ack) == 4 and struct.unpack('!I', ack)[0] == seq:
                        ok = True
                        break
                except socket.timeout:
                    pass

            if not ok:
                print(f"[UDP Client] Pachet {seq} pierdut!")
                lost += 1

            sent_b += clen
            sent_m += 1

        rem -= clen
        seq += 1

    end_pkt = struct.pack(HDR_FMT, END_SEQ, n_chunks, 0)
    sock.sendto(end_pkt, (host, port))

    elapsed = time.time() - start
    tput = sent_b / elapsed / 1024 / 1024 if elapsed > 0 else 0

    print(f"\n{'='*50}")
    print(f"[UDP Client] Protocol        : UDP")
    print(f"[UDP Client] Method          : {method}")
    print(f"[UDP Client] Block size      : {bsize} B")
    print(f"[UDP Client] Mesaje trimise  : {sent_m}")
    print(f"[UDP Client] Bytes trimisi   : {sent_b}")
    print(f"[UDP Client] Timp transfer   : {elapsed:.4f} s")
    print(f"[UDP Client] Throughput      : {tput:.2f} MB/s")
    if method == 'stop-and-wait':
        print(f"[UDP Client] Pachete pierdute: {lost}")
    print(f"[UDP Client] SHA-256         : {h.hexdigest()}")
    print(f"{'='*50}\n")

    sock.close()


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',       default='127.0.0.1')
    ap.add_argument('--port',       type=int, default=5002)
    ap.add_argument('--size',       type=int, default=500)
    ap.add_argument('--block-size', type=int, default=1000, dest='block_size')
    ap.add_argument('--method',     choices=['streaming', 'stop-and-wait'], default='streaming')
    args = ap.parse_args()
    run_client(args.host, args.port, args.size, args.block_size, args.method)
