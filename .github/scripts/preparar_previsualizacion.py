#!/usr/bin/env python3
"""Preparar una COPIA navegable y no indexable de la rama pruebas de CARACOLES.
No realiza cambios en el repositorio de producción.
"""
from pathlib import Path
import re
import shutil
import sys

site = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
if not (site / "index.html").is_file() or not (site / "assets/js/site.js").is_file():
    raise SystemExit("ERROR: la copia de la rama pruebas no contiene la web esperada")

# Nunca transferir el dominio ni publicar un sitemap de producción.
for name in (
    "CNAME", "sitemap.xml", "sw.js", "manifest.webmanifest",
    "README.md", "PRUEBA_URLS_DUDA.md", "SEO_CAPA_1_CAMBIOS.md",
):
    (site / name).unlink(missing_ok=True)
shutil.rmtree(site / ".github", ignore_errors=True)

preview_base = "https://caracoles-web.github.io/caracoles-pruebas"
project_prefix = "/caracoles-pruebas/"
production_hosts = (
    "https://www.asadorcaracoles.es",
    "https://asadorcaracoles.es",
    "http://www.asadorcaracoles.es",
    "http://asadorcaracoles.es",
)

# El registro del SW está en site.js; no permitir que se apropie de
# recursos de prueba ni comparta caché entre ciclos de pruebas.
script = site / "assets/js/site.js"
code = script.read_text(encoding="utf-8")
sw_registration = re.compile(
    r"(?m)^  if\('serviceWorker' in navigator &&[\s\S]*?^  \}\s*\n"
)
code, removed = sw_registration.subn("", code, count=1)
if removed != 1:
    raise SystemExit("ERROR: no se pudo aislar el service worker en site.js; revisar antes de publicar")
script.write_text(code, encoding="utf-8")

html_count = 0
for item in site.rglob("*"):
    if not item.is_file() or item.suffix.lower() not in {
        ".html", ".js", ".css", ".json", ".svg", ".xml", ".webmanifest"
    }:
        continue
    contents = item.read_text(encoding="utf-8")
    for host in production_hosts:
        contents = contents.replace(host, preview_base)

    # Las rutas absolutas a la raíz del dominio deben quedar en el subdirectorio
    # /caracoles-pruebas/ en el dominio github.io.
    contents = re.sub(
        r"""(?i)(\b(?:href|src|poster|action)\s*=\s*["'])/(?!/)([^"']*)""",
        lambda m: m.group(1) + project_prefix + m.group(2),
        contents,
    )

    if item.suffix.lower() == ".html":
        # No publicar etiquetas canonical/hreflang ni la verificación de Search Console.
        contents = re.sub(
            r"""(?is)<link\b(?=[^>]*\brel\s*=\s*["'](?:canonical|alternate|manifest)["'])[^>]*>\s*""",
            "", contents,
        )
        contents = re.sub(
            r"""(?is)<meta\b(?=[^>]*\bname\s*=\s*["'](?:robots|googlebot|google-site-verification)["'])[^>]*>\s*""",
            "", contents,
        )
        if not re.search(r"</head\s*>", contents, flags=re.IGNORECASE):
            raise SystemExit("ERROR: HTML sin etiqueta head: " + str(item))
        contents = re.sub(
            r"</head\s*>",
            '  <meta name="robots" content="noindex,nofollow,noarchive,nosnippet">\n</head>',
            contents,
            count=1,
            flags=re.IGNORECASE,
        )
        html_count += 1

    item.write_text(contents, encoding="utf-8")

# No emitir robots.txt en una subruta como si pudiera controlar el origen completo
# caracoles-web.github.io; el control efectivo está en las metaetiquetas por página.
(site / "robots.txt").unlink(missing_ok=True)
(site / ".nojekyll").write_text("", encoding="utf-8")

for html in site.rglob("*.html"):
    txt = html.read_text(encoding="utf-8")
    if 'content="noindex,nofollow,noarchive,nosnippet"' not in txt:
        raise SystemExit("ERROR: página sin noindex " + str(html))
if (site / "CNAME").exists() or (site / "sw.js").exists():
    raise SystemExit("ERROR: CNAME o sw.js no aislados")

print(f"PREVIEW OK: {html_count} páginas HTML aisladas; CNAME, sitemap, manifest y SW ausentes")
print("DESTINO PREVISTO:", preview_base + "/")
