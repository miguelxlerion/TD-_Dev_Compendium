#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mini-servidor de la plataforma Total Darkness.

Sirve la carpeta del proyecto Y expone un endpoint para regenerar el índice
desde el botón "Re-escanear" de la plataforma (el navegador no puede ejecutar
procesos locales por seguridad, por eso hace falta este puente).

Uso:
    python tools/server.py            # http://127.0.0.1:8080
    python tools/server.py 9000       # otro puerto
    npm run up                        # atajo

Endpoints:
    GET  /                            -> index.html (estáticos de la raíz)
    GET  /api/status                  -> {"html": n, "pdf": n, "generated": "..."}
    POST /api/regenerar               -> ejecuta build-manifest.py --update-index
                                        y devuelve {"ok": true, "html": n, "pdf": n, ...}

Solo escucha en 127.0.0.1 (tu máquina) y solo ejecuta el script del proyecto.
Sin dependencias: solo librería estándar.
"""
import json
import subprocess
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "tools" / "build-manifest.py"
MANIFEST = ROOT / "content" / "manifest.json"


def manifest_stats():
    try:
        data = json.loads(MANIFEST.read_text(encoding="utf-8"))
        pages = data.get("pages", [])
        imgdir = ROOT / "content" / "img"
        images = sum(1 for _ in imgdir.rglob("*") if _.is_file()) if imgdir.exists() else 0
        return {
            "html": sum(1 for p in pages if p.get("type") == "html"),
            "pdf": sum(1 for p in pages if p.get("type") == "pdf"),
            "imagenes": images,
            "generated": data.get("generated", ""),
        }
    except Exception as exc:
        return {"error": str(exc)}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, payload, code=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/api/status"):
            self._json({"ok": True, **manifest_stats()})
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.rstrip("/").endswith("/api/regenerar"):
            try:
                proc = subprocess.run(
                    [sys.executable, str(BUILD), "--update-index"],
                    cwd=str(ROOT),
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if proc.returncode != 0:
                    self._json({"ok": False, "error": proc.stderr[-2000:]}, 500)
                else:
                    self._json({"ok": True, "log": proc.stdout[-2000:], **manifest_stats()})
            except Exception as exc:  # noqa: BLE001
                self._json({"ok": False, "error": str(exc)}, 500)
        else:
            self._json({"ok": False, "error": "endpoint desconocido"}, 404)

    def log_message(self, fmt, *args):
        sys.stdout.write("[server] " + fmt % args + "\n")


class PlatformServer(ThreadingHTTPServer):
    # Estricto a propósito: http.server trae allow_reuse_address=True, que en
    # Windows permite "robar" un puerto ya ocupado. En False, ocupar un puerto
    # en uso falla con error en vez de crear dos servidores peleando por él.
    allow_reuse_address = False
    daemon_threads = True


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    srv = PlatformServer(("127.0.0.1", port), Handler)
    print(f"[server] TD Dev Compendium en http://127.0.0.1:{port}")
    print("[server] Botón 'Re-escanear' activo (POST /api/regenerar). Ctrl+C para detener.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] detenido.")


if __name__ == "__main__":
    main()
