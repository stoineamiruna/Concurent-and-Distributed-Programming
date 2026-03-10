#!/usr/bin/env python3

import asyncio
import hashlib
import struct
import argparse

from aioquic.asyncio import serve
from aioquic.asyncio.protocol import QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.quic.events import QuicEvent, StreamDataReceived, ConnectionTerminated


class QUICServer(QuicConnectionProtocol):

    def __init__(self, *args, method='streaming', **kwargs):
        super().__init__(*args, **kwargs)
        self._method  = method
        self._bufs    = {}
        self._h       = hashlib.sha256()
        self._total_b = 0
        self._total_m = 0
        self._done    = False

    def quic_event_received(self, event: QuicEvent):
        if isinstance(event, StreamDataReceived):
            sid = event.stream_id
            self._bufs.setdefault(sid, b'')
            self._bufs[sid] += event.data
            self._proc(sid, event.end_stream)
        elif isinstance(event, ConnectionTerminated):
            if not self._done:
                self._finish()

    def _proc(self, sid, end=False):
        buf = self._bufs[sid]

        while len(buf) >= 4:
            mlen = struct.unpack('!I', buf[:4])[0]

            if mlen == 0:
                self._bufs[sid] = buf[4:]
                self._finish()
                return

            if len(buf) < 4 + mlen:
                break

            data = buf[4: 4 + mlen]
            buf  = buf[4 + mlen:]

            self._h.update(data)
            self._total_b += mlen
            self._total_m += 1

            if self._method == 'stop-and-wait':
                self._quic.send_stream_data(sid, b'ACK')
                self.transmit()

        self._bufs[sid] = buf

        if end and not self._done:
            self._finish()

    def _finish(self):
        if self._done:
            return
        self._done = True

        print(f"\n{'='*50}")
        print(f"[QUIC Server] Protocol        : QUIC")
        print(f"[QUIC Server] Method          : {self._method}")
        print(f"[QUIC Server] Mesaje primite  : {self._total_m}")
        print(f"[QUIC Server] Bytes primiti   : {self._total_b}")
        print(f"[QUIC Server] SHA-256         : {self._h.hexdigest()}")
        print(f"{'='*50}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--host',   default='0.0.0.0')
    ap.add_argument('--port',   type=int, default=5003)
    ap.add_argument('--method', choices=['streaming', 'stop-and-wait'], default='streaming')
    ap.add_argument('--cert',   default='cert.pem')
    ap.add_argument('--key',    default='key.pem')
    args = ap.parse_args()

    cfg = QuicConfiguration(is_client=False, alpn_protocols=['pcd-transfer'])
    cfg.load_cert_chain(args.cert, args.key)

    def make_proto(*a, **kw):
        return QUICServer(*a, method=args.method, **kw)

    loop = asyncio.get_event_loop()

    async def start():
        sv = await serve(args.host, args.port, configuration=cfg, create_protocol=make_proto)
        print(f"[QUIC Server] Ascult pe {args.host}:{args.port} | method={args.method}")
        return sv

    loop.run_until_complete(start())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n[QUIC Server] Oprit.")


if __name__ == '__main__':
    main()
