#!/usr/bin/env python3
"""Fortran Compute Claw — persistent daemon for room tensor operations.

Listens on :4081. Any layer in any language sends tile batches,
gets back contracted results. The stemcell, always hot.
"""

import ctypes
import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional

FORT_LIB = os.path.join(os.path.dirname(__file__), "libplato_math.so")
PORT = 4081

lib = None  # loaded on start

def load_fortran() -> Optional[ctypes.CDLL]:
    if not os.path.exists(FORT_LIB):
        return None
    lib = ctypes.CDLL(FORT_LIB)
    
    lib.contract_tiles.argtypes = [
        ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
        ctypes.c_float,
    ]
    lib.spline_interp.argtypes = [
        ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(ctypes.c_int32),
        ctypes.c_int32, ctypes.c_float,
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.batch_gradient.argtypes = [
        ctypes.POINTER(ctypes.c_int32), ctypes.c_int32,
        ctypes.POINTER(ctypes.c_int32),
    ]
    lib.get_physics.argtypes = [
        ctypes.POINTER(ctypes.c_float), ctypes.POINTER(ctypes.c_float),
        ctypes.POINTER(ctypes.c_int32),
    ]
    return lib

def make_tiles(arr):
    """Convert list of ints to ctypes array"""
    n = len(arr)
    return (ctypes.c_int32 * n)(*arr)

class ClawHandler(BaseHTTPRequestHandler):
    def _json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("X-Fortran-Claw", "hot")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        return json.loads(self.rfile.read(length))
    
    def do_GET(self):
        p = self.path
        if p == "/":
            lat = ctypes.c_float(0)
            fl = ctypes.c_float(0)
            sd = ctypes.c_int32(0)
            lib.get_physics(ctypes.byref(lat), ctypes.byref(fl), ctypes.byref(sd))
            self._json({
                "service": "Fortran Compute Claw",
                "port": PORT,
                "physics": {
                    "latency_ns": lat.value,
                    "flops": fl.value,
                    "simd_bits": sd.value,
                },
                "endpoints": {
                    "GET /": "physics + help",
                    "POST /contract": "room_a, room_b, threshold → similar tiles",
                    "POST /spline": "before, after, n, mu → interpolated",
                    "POST /gradient": "tiles, n → delta array",
                }
            })
        elif p == "/physics":
            lat = ctypes.c_float(0)
            fl = ctypes.c_float(0)
            sd = ctypes.c_int32(0)
            lib.get_physics(ctypes.byref(lat), ctypes.byref(fl), ctypes.byref(sd))
            self._json({"latency_ns": lat.value, "flops": fl.value, "simd_bits": sd.value})
        else:
            self._json({"error": "not found"}, 404)
    
    def do_POST(self):
        p = self.path
        body = self._read_body()
        
        if p == "/contract":
            a = make_tiles(body.get("room_a", []))
            b = make_tiles(body.get("room_b", []))
            na = body.get("na", len(a))
            nb = body.get("nb", len(b))
            thresh = ctypes.c_float(body.get("threshold", 0.3))
            result = (ctypes.c_int32 * (na * nb))()
            nresult = ctypes.c_int32(0)
            lib.contract_tiles(a, na, b, nb, result, ctypes.byref(nresult), thresh)
            self._json({
                "nresult": nresult.value,
                "results": [result[i] for i in range(nresult.value)],
            })
        
        elif p == "/spline":
            before = make_tiles(body.get("before", []))
            after = make_tiles(body.get("after", []))
            n = body.get("n", len(before))
            mu = ctypes.c_float(body.get("mu", 0.5))
            result = (ctypes.c_int32 * n)()
            lib.spline_interp(before, after, n, mu, result)
            self._json({"result": [result[i] for i in range(n)]})
        
        elif p == "/gradient":
            tiles = make_tiles(body.get("tiles", []))
            n = body.get("n", len(tiles))
            grads = (ctypes.c_int32 * n)()
            lib.batch_gradient(tiles, n, grads)
            self._json({"gradients": [grads[i] for i in range(n)]})
        
        else:
            self._json({"error": "not found"}, 404)
    
    def log_message(self, fmt, *args):
        sys.stderr.write(f"[CLAW] {args[0] if args else ''} {args[1] if len(args)>1 else ''}\n")

def main():
    global lib
    lib = load_fortran()
    if not lib:
        print("❌ Fortran library not found. Run 'make' first.")
        sys.exit(1)
    
    server = HTTPServer(("0.0.0.0", PORT), ClawHandler)
    print(f"🔩 Fortran Compute Claw on :{PORT}")
    print(f"   Physics: 12ns latency, 1.2e+10 FLOPS, 16-bit SIMD")
    print(f"   Endpoints: /contract  /spline  /gradient  /physics")
    
    # Keep the python process alive for systemd
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("\n🔩 Claw stopped.")

if __name__ == "__main__":
    main()
