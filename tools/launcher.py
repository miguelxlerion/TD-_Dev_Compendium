#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lanzador avanzado de la plataforma Total Darkness.

Detecta puertos en uso y arranca los servicios en puertos libres:
  - Servidor de la plataforma (estáticos + POST /api/regenerar para el botón
    ⟳ Re-escanear) -> tools/server.py

Uso:
    python tools/launcher.py                  # puerto 8080 o el primero libre
    python tools/launcher.py --port 9000      # prefiere el 9000
    python tools/launcher.py --no-browser     # no abre el navegador solo
    Iniciar-Plataforma.bat                    # doble clic en Windows
    npm run up                                # atajo

Sin dependencias: solo librería estándar.
"""
import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SERVER = ROOT / "tools" / "server.py"
START_PORT = 8080
SCAN_COUNT = 20


def port_free(port: int) -> bool:
    """True si el puerto está libre en 127.0.0.1 (donde escucha el servidor)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def find_port(preferred: int):
    """Devuelve (puerto, ocupados). Busca el preferido y si no los siguientes."""
    occupied = []
    candidates = [preferred] + [p for p in range(START_PORT, START_PORT + SCAN_COUNT)
                                if p != preferred]
    for port in candidates:
        if port_free(port):
            return port, occupied
        occupied.append(port)
    raise RuntimeError(f"No hay puertos libres entre {START_PORT} y "
                       f"{START_PORT + SCAN_COUNT - 1}")


def wait_ready(port: int, timeout: float = 15.0):
    """Espera a que /api/status responda con la forma esperada.

    No basta con que el puerto responda: verifica que sea NUESTRO servidor
    (ok + conteos del índice) y no otro servicio ajeno en el mismo puerto.
    """
    url = f"http://127.0.0.1:{port}/api/status"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if isinstance(data, dict) and data.get("ok") is True and "html" in data:
                    return data
        except Exception:  # noqa: BLE001 - reintenta hasta el timeout
            time.sleep(0.3)
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="Lanzador de Total Darkness")
    parser.add_argument("--port", type=int, default=START_PORT,
                        help=f"puerto preferido (por defecto {START_PORT})")
    parser.add_argument("--no-browser", action="store_true",
                        help="no abrir el navegador automáticamente")
    args = parser.parse_args()

    print("=" * 60)
    print("  TD DEV COMPENDIUM · Lanzador de plataforma")
    print("=" * 60)

    try:
        port, occupied = find_port(args.port)
    except RuntimeError as exc:
        print(f"[ERROR] {exc}")
        return 1
    for taken in occupied:
        print(f"[puertos] {taken} en uso -> se omite")
    print(f"[puertos] usando puerto libre: {port}")

    env = dict(os.environ, PYTHONUNBUFFERED="1")
    proc = subprocess.Popen([sys.executable, str(SERVER), str(port)],
                            cwd=str(ROOT), env=env)
    try:
        status = wait_ready(port)
        if proc.poll() is not None or not status:
            print("[ERROR] el servidor no quedó sirviendo en el puerto "
                  f"{port} (¿lo ocupó otro programa a último momento?).")
            if proc.poll() is None:
                proc.terminate()
            return 1
        url = f"http://127.0.0.1:{port}/index.html"
        print(f"[ok] plataforma en {url}")
        if status.get("ok"):
            print(f"[ok] índice: {status.get('html', '?')} HTML + "
                  f"{status.get('pdf', '?')} PDF "
                  f"(botón ⟳ Re-escanear activo)")
        if not args.no_browser:
            webbrowser.open(url)
            print("[ok] navegador abierto")
        print("Pulsa Ctrl+C para detener el servidor.")
        proc.wait()
        return proc.returncode or 0
    except KeyboardInterrupt:
        print("\n[stop] deteniendo servidor...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[stop] listo.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
