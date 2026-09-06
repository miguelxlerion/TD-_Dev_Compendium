#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga las imágenes remotas de content/*.html a content/img/<pagina>/ y
reescribe los <img/srcset/video/poster> a rutas locales.

Por qué existe: las guías generadas por IA apuntan a URLs firmadas temporales
(ej. cdn.qwenlm.ai?...key=eyJ...) que caducan y dejan las imágenes rotas.
Al localizarlas, la plataforma funciona offline y para siempre.

Uso:
    python tools/localizar-imagenes.py
    python tools/localizar-imagenes.py --page pipeline-personajes-unity-v3.html

Reejecutable: omite URLs que ya fueron localizadas.
Sin dependencias: solo librería estándar.
"""
import argparse
import html as ihtml
import mimetypes
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
IMGROOT = CONTENT / "img"

PATTERNS = [
    (re.compile(r'(<img[^>]+src=")([^"]+)(")', re.I), "img src"),
    (re.compile(r'(<source[^>]+src=")([^"]+)(")', re.I), "source src"),
    (re.compile(r'(<video[^>]+src=")([^"]+)(")', re.I), "video src"),
    (re.compile(r'(<video[^>]+poster=")([^"]+)(")', re.I), "video poster"),
    (re.compile(r'srcset="([^"]+)"', re.I), "srcset"),
]

EXT_BY_TYPE = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp",
    "image/gif": ".gif", "image/svg+xml": ".svg", "image/avif": ".avif",
    "video/mp4": ".mp4", "video/webm": ".webm",
}


def download(url: str, dest: Path) -> bool:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as exc:
        print(f"    [x] {url[:80]}... -> {exc}")
        return False
    if not data:
        print(f"    [x] {url[:80]}... -> vacío")
        return False
    ctype = (resp.headers.get_content_type() or "").lower()
    ext = EXT_BY_TYPE.get(ctype) or mimetypes.guess_extension(ctype) or ""
    if not ext or len(ext) > 5:
        m = re.search(r"\.([a-zA-Z0-9]{3,4})(?:[?#]|$)", url)
        ext = f".{m.group(1).lower()}" if m else ".png"
    dest = dest.with_suffix(ext)
    dest.write_bytes(data)
    print(f"    [ok] {dest.name} ({len(data)//1024} KB, {ctype or 'tipo desc.'})")
    return True


def localize_page(path: Path) -> tuple[int, int]:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    slug = path.stem
    target_dir = IMGROOT / slug
    target_dir.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    counter = [0]

    def local_name() -> Path:
        counter[0] += 1
        return target_dir / f"{counter[0]:02d}"

    def fix_url(url: str) -> str:
        nonlocal ok, fail
        url = ihtml.unescape(url.strip())
        if not url.startswith(("http://", "https://")):
            return url  # ya es local o data:
        dest = local_name()
        if download(url, dest):
            ok += 1
            # re-descubre la extensión real escrita por download()
            written = sorted(target_dir.glob(f"{counter[0]:02d}.*"))
            rel = f"img/{slug}/{written[-1].name}" if written else f"img/{slug}/{dest.name}"
            return rel
        fail += 1
        return url  # se deja la remota si falló la descarga

    def repl_src(m):
        return m.group(1) + fix_url(m.group(2)) + m.group(3)

    for pattern, kind in PATTERNS:
        if kind == "srcset":
            def repl_srcset(m):
                parts = []
                for piece in m.group(1).split(","):
                    piece = piece.strip()
                    if not piece:
                        continue
                    bits = piece.split()
                    bits[0] = fix_url(bits[0])
                    parts.append(" ".join(bits))
                return 'srcset="' + ", ".join(parts) + '"'
            raw = pattern.sub(repl_srcset, raw)
        else:
            raw = pattern.sub(repl_src, raw)

    if ok:
        path.write_text(raw, encoding="utf-8")
    return ok, fail


def main() -> int:
    parser = argparse.ArgumentParser(description="Localiza imágenes remotas")
    parser.add_argument("--page", help="solo esta página de content/")
    args = parser.parse_args()

    pages = [CONTENT / args.page] if args.page else sorted(CONTENT.glob("*.html"))
    total_ok = total_fail = 0
    for page in pages:
        if not page.exists():
            print(f"[x] no existe {page}")
            continue
        print(f"== {page.name} ==")
        ok, fail = localize_page(page)
        total_ok += ok
        total_fail += fail
        if not ok and not fail:
            print("    (sin imágenes remotas)")
    print(f"\n[resumen] {total_ok} localizadas, {total_fail} fallidas")
    return 1 if total_fail else 0


if __name__ == "__main__":
    sys.exit(main())
