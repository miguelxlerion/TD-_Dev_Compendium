#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Regenera content/manifest.json escaneando content/*.html y docs/*.pdf.

Uso:
    python tools/build-manifest.py
    python tools/build-manifest.py --update-index   # además refresca el manifest embebido en index.html

Cómo funciona la auto-integración:
  1. Copia tu nueva-guia.html en content/ (PDFs en docs/).
  2. Ejecuta este script. Detecta <title>, primer párrafo, <h1>/<h2> y
     palabras clave para asignar categoría, descripción y etiquetas.
  3. Recarga index.html: la página aparece sola en su categoría y en el buscador.

Respeta ediciones manuales: si el manifest ya tiene una entrada para el mismo
archivo, conserva title/short/description/category/tags/badge/featured.
"""
import json, re, sys, hashlib, html as ihtml
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
DOCS = ROOT / "docs"
MANIFEST = CONTENT / "manifest.json"
INDEX = ROOT / "index.html"

CATEGORIES = [
  {"id": "personajes", "name": "Personajes & Pipeline 3D",
   "description": "Diseño, modelado, texturizado, rigging, animación e integración en Unity — de concepto a motor.",
   "icon": "users", "color": "violet"},
  {"id": "texturizado", "name": "Texturizado & Optimización",
   "description": "Atlas textures, PBR, Substance, memoria y rendimiento en Unity 3D.",
   "icon": "layers", "color": "amber"},
  {"id": "automatizacion", "name": "Automatización, Scripts & Plugins",
   "description": "Python, MAXScript, UXP, Blender e integración inter-app para producción AAA.",
   "icon": "bot", "color": "cyan"},
  {"id": "programacion", "name": "Programación & Gameplay",
   "description": "Sistemas core de Total Darkness: movimiento híbrido, narrativa, QTE, combate y ritmo.",
   "icon": "gamepad-2", "color": "emerald"},
  {"id": "biblioteca", "name": "Biblioteca PDF · Diseño",
   "description": "Documentos de diseño y arquitectura del proyecto Total Darkness en PDF.",
   "icon": "library", "color": "rose"},
]

KEYWORDS = {
  "texturizado": ["atlas", "textur", "substance", "pbr", "optimiz", "memoria", "rendimiento"],
  "automatizacion": ["script", "plugin", "python", "maxscript", "blender", "zbrush", "automat", "uxp", "pipeline xrerion", "xrerion"],
  "programacion": ["programaci", "gameplay", "qte", "combate", "narrativ", "karma", "movimiento", "shooter", "fatality", "ritmo", "sistemas core"],
  "personajes": ["personaje", "modelado", "rigging", "pipeline", "unity", "aaa", "animaci", "concepto"],
}

def clean(t: str) -> str:
    t = re.sub(r"<script[\s\S]*?</script>", " ", t, flags=re.I)
    t = re.sub(r"<style[\s\S]*?</style>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = ihtml.unescape(t)
    return re.sub(r"\s+", " ", t).strip()

def extract_meta(path: Path):
    raw = path.read_text(encoding="utf-8", errors="ignore")
    m = re.search(r"<title>(.*?)</title>", raw, re.I | re.S)
    title = clean(m.group(1)) if m else path.stem.replace("-", " ").replace("_", " ")
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", raw, re.I | re.S)
    h1t = clean(h1.group(1))[:120] if h1 else ""
    ps = [clean(x) for x in re.findall(r"<p[^>]*>(.*?)</p>", raw, re.I | re.S)]
    desc = next((p for p in ps if len(p) > 60), (ps[0] if ps else ""))[:280]
    h2s = [clean(x)[:80] for x in re.findall(r"<h2[^>]*>(.*?)</h2>", raw, re.I | re.S)][:8]
    nav = [clean(x)[:40] for x in re.findall(r"<a[^>]*>(.*?)</a>", raw, re.I | re.S)][:12]
    blob = f"{title} {h1t} {desc} {' '.join(h2s)} {' '.join(nav)}".lower()
    return title, h1t, desc, blob

def guess_category(blob: str, filename: str) -> str:
    scores = {c: sum(1 for k in keys if k in blob) for c, keys in KEYWORDS.items()}
    scores["personajes"] += sum(1 for k in ["unity", "personajes"] if k in filename.lower())
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "personajes"

def slugify(name: str) -> str:
    s = name.lower()
    rep = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n", "ü": "u"}
    for a, b in rep.items():
        s = s.replace(a, b)
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return re.sub(r"-+", "-", s) or "pagina"

def load_previous():
    if MANIFEST.exists():
        try:
            data = json.loads(MANIFEST.read_text(encoding="utf-8"))
            return {p.get("file"): p for p in data.get("pages", [])}, data.get("version", 1)
        except Exception:
            pass
    return {}, 1

def localizar_imagenes():
    """Descarga las imágenes remotas de content/*.html a content/img/.

    Idempotente: las páginas sin URLs remotas no se tocan. Si algo falla,
    solo avisa — el índice se genera igual. Se omite con --sin-imagenes.
    """
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "localizar_imagenes", str(ROOT / "tools" / "localizar-imagenes.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        total_ok = total_fail = 0
        for page in sorted(CONTENT.glob("*.html")):
            ok, fail = mod.localize_page(page)
            total_ok += ok
            total_fail += fail
        print(f"[img] {total_ok} localizadas, {total_fail} fallidas")
        return total_ok, total_fail
    except Exception as exc:  # noqa: BLE001
        print(f"[img] omitido: {exc}")
        return 0, 0


def main():
    prev, version = load_previous()
    if "--sin-imagenes" not in sys.argv:
        localizar_imagenes()
    pages = []
    seen_hash = set()

    def fresh(path: Path) -> bool:
        """Detecta contenido duplicado: si otro archivo ya tiene estos mismos
        bytes, se omite (evita que una copia con distinto nombre aparezca dos
        veces en la plataforma). Se priorizan los ya integrados en el índice."""
        digest = hashlib.md5(path.read_bytes()).hexdigest()
        if digest in seen_hash:
            print(f"[dup] {path.name} duplicado: se omite (mismo contenido ya integrado)")
            return False
        seen_hash.add(digest)
        return True

    html_files = sorted(CONTENT.glob("*.html"))
    # Primero los ya conocidos (conservan su curaduría y ganan el desempate),
    # después los nuevos.
    html_files.sort(key=lambda f: f"content/{f.name}" not in prev)
    for f in html_files:
        if f.name.lower() == "manifest.json":
            continue
        if not fresh(f):
            continue
        rel = f"content/{f.name}"
        title, h1t, desc, blob = extract_meta(f)
        cat = guess_category(blob, f.name)
        pid = slugify(f.stem)[:60]
        tags = sorted({k for keys in KEYWORDS.values() for k in keys if k in blob})
        entry = {
            "id": pid,
            "title": title or f.stem,
            "short": (h1t or title)[:60],
            "file": rel,
            "type": "html",
            "category": cat,
            "description": desc or title,
            "tags": tags[:10] or [cat, "guia"],
        }
        if rel in prev:  # respetar curaduría manual
            old = prev[rel]
            for k in ("id", "title", "short", "description", "category", "tags", "badge", "featured", "topic"):
                if old.get(k) not in (None, "", []):
                    entry[k] = old[k]
        pages.append(entry)

    for f in sorted(DOCS.glob("*.pdf")):
        if not fresh(f):
            continue
        rel = f"docs/{f.name}"
        stem = f.stem.replace("-", " ").replace("_", " ")
        title = " ".join(w.capitalize() for w in stem.split())
        blob = stem.lower()
        topic = guess_category(blob, f.name)
        entry = {
            "id": slugify("pdf-" + f.stem)[:60],
            "title": title, "short": title[:60], "file": rel,
            "type": "pdf", "category": "biblioteca", "topic": topic,
            "description": f"Documento de diseño: {title}.",
            "tags": ["pdf", topic],
        }
        if rel in prev:
            old = prev[rel]
            for k in ("id", "title", "short", "description", "category", "tags", "badge", "featured", "topic"):
                if old.get(k) not in (None, "", []):
                    entry[k] = old[k]
        pages.append(entry)

    manifest = {
        "version": version,
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "tools/build-manifest.py",
        "categories": CATEGORIES,
        "pages": pages,
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[ok] {MANIFEST} -> {len([p for p in pages if p['type']=='html'])} HTML + {len([p for p in pages if p['type']=='pdf'])} PDF")

    if "--update-index" in sys.argv and INDEX.exists():
        txt = INDEX.read_text(encoding="utf-8")
        emb = json.dumps(manifest, ensure_ascii=False, indent=2)
        new = re.sub(r'(<script type="application/json" id="manifest-embedded">)[\s\S]*?(</script>)',
                     lambda m: m.group(1) + "\n" + emb + "\n" + m.group(2), txt, count=1)
        INDEX.write_text(new, encoding="utf-8")
        print("[ok] manifest embebido en index.html actualizado")

if __name__ == "__main__":
    main()
