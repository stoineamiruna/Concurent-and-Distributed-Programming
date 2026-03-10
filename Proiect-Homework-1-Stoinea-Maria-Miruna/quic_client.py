#!/usr/bin/env python3

import asyncio
import hashlib
import struct
import argparse
import time

from aioquic.asyncio import connect
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, StreamDataReceived


class QUICClient(QuicConnectionProtocol):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rbuf  = b''
        self._acks  = asyncio.Queue()

    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, StreamDataReceived):
            self._rbuf += event.data
            while len(self._rbuf) >= 3:
                if self._rbuf[:3] == b'ACK':
                    self._acks.put_nowait(True)
                    self._rbuf = self._rbuf[3:]
                else:
                    self._rbuf = self._rbuf[1:]

    async def transfer(self, size_mb, bsize, method):
        total  = size_mb * 1024 * 1024
        base   = bytes(i % 256 for i in range(min(bsize, 65536)))
        tmpl   = (base * (bsize // len(base) + 1))[:bsize]
        sid    = self._quic.get_next_available_stream_id()

        h      = hashlib.sha256()
        sent_b = 0
        sent_m = 0
        rem    = total

        start = time.time()

        while rem > 0:
            clen = min(bsize, rem)
            data = tmpl[:clen]
            h.update(data)

            self._quic.send_stream_data(sid, struct.pack('!I', clen) + data)
            self.transmit()

            sent_b += clen
            sent_m += 1
            rem    -= clen

            if method == 'stop-and-wait':
                try:
                    await asyncio.wait_for(self._acks.get(), timeout=5.0)
                except asyncio.TimeoutError:
                    print(f"[QUIC Client] Timeout ACK mesaj {sent_m}")

        self._quic.send_stream_data(sid, struct.pack('!I', 0), end_stream=True)
        self.transmit()

        await asyncio.sleep(1.5)

        elapsed = time.time() - start
        tput = sent_b / elapsed / 1024 / 1024 if elapsed > 0 else 0

        print(f"\n{'='*50}")
        print(f"[QUIC Client] Protocol        : QUIC")
        print(f"[QUIC Client] Method          : {method}")
        print(f"[QUIC Client] Block size      : {bsize} B")
        print(f"[QUIC Client] Mesaje trimise  : {sent_m}")
        print(f"[QUIC Client] Bytes trimisi   : {sent_b}")
        print(f"[QUIC Client] Timp transfer   : {elapsed:.4f} s")
        print(f"[QUIC Client] Throughput      : {tput:.2f} MB/s")
        print(f"[QUIC Client] SHA-256         : {h.hexdigest()}")
        print(f"{'='*50}\n")


async def main_async(host, port, size_mb, bsize, method, cafile):
    import ssl
    cfg = QuicConfiguration(is_client=True, alpn_protocols=['pcd-transfer'])
    cfg.verify_mode = ssl.CERT_NONE

    print(f"[QUIC Client] Conectare la {host}:{port} ...")

    async with connect(host, port, configuration=cfg, create_protocol=QUICClient) as client:
        await client.transfer(size_mb, bsize, method)
        client.close()
        await asyncio.sleep(0.5)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',       default='127.0.0.1')
    ap.add_argument('--port',       type=int, default=5003)
    ap.add_argument('--size',       type=int, default=500)
    ap.add_argument('--block-size', type=int, default=1000, dest='block_size')
    ap.add_argument('--method',     choices=['streaming', 'stop-and-wait'], default='streaming')
    ap.add_argument('--cafile',     default='cert.pem')
    args = ap.parse_args()
    asyncio.run(main_async(args.host, args.port, args.size, args.block_size, args.method, args.cafile))


if __name__ == '__main__':
    main()
