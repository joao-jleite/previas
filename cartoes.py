"""Gera o cartão de link (docs/<slug>/cartao.png, 1200x630) que o WhatsApp mostra junto do link da prévia.

Uso (na pasta prospeccao-previas):
  python cartoes.py --fila            só quem está pendente em whatsapp_fila.json
  python cartoes.py --celular         todo lead de leads/todos.json com celular público
  python cartoes.py slug1 slug2 ...   só esses
  (acrescente --refazer para gerar de novo quem já tem cartão)

O HTML do cartão vem de gerar.cartao(lead); a foto é do Edge em modo headless. Depois, publicar com
`git add docs && git commit && git push`, como as prévias.
"""
import json
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import gerar

PASTA = Path(__file__).resolve().parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def celular(texto):
    d = re.sub(r"\D", "", texto or "")
    if d and not d.startswith("55"):
        d = "55" + d
    return len(d) == 13 and d[4] == "9"


def fotografar(lead, tmp, refazer):
    s = gerar.slug(lead["nome"])
    destino = gerar.OUT / s / "cartao.png"
    if not destino.parent.exists():
        return s, "sem prévia"
    if destino.exists() and not refazer:
        return s, "já existe"
    origem = Path(tmp) / f"{s}.html"
    origem.write_bytes(gerar.cartao(lead).encode("utf-8"))
    try:
        # perfil próprio por cartão: várias instâncias headless no mesmo perfil travam umas às outras
        subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--window-size=1200,630",
                        "--virtual-time-budget=6000", f"--user-data-dir={Path(tmp) / ('p-' + s)}",
                        f"--screenshot={destino}", origem.as_uri()],
                       capture_output=True, timeout=90)
    except (subprocess.TimeoutExpired, OSError) as erro:
        return s, f"falhou ({type(erro).__name__})"
    return s, f"{destino.stat().st_size // 1024} KB" if destino.exists() else "falhou (sem arquivo)"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    refazer = "--refazer" in sys.argv
    leads = json.loads((PASTA / "leads" / "todos.json").read_text(encoding="utf-8"))
    if "--fila" in sys.argv:
        fila = json.loads((PASTA / "whatsapp_fila.json").read_text(encoding="utf-8"))
        emails = {(c.get("to") or "").lower() for c in fila if c.get("status") == "pendente"}
        leads = [x for x in leads if (x.get("email") or "").lower() in emails]
    elif "--celular" in sys.argv:
        leads = [x for x in leads if celular(x.get("whatsapp_ou_telefone"))]
    elif args:
        leads = [x for x in leads if gerar.slug(x["nome"]) in args]
    else:
        sys.exit(__doc__)
    if not Path(EDGE).exists():
        sys.exit(f"Edge não encontrado em {EDGE}")
    with tempfile.TemporaryDirectory() as tmp:
        with ThreadPoolExecutor(max_workers=3) as pool:
            resultados = list(pool.map(lambda x: fotografar(x, tmp, refazer), leads))
    falhas = [r for r in resultados if r[1].startswith("falhou")]
    for s, r in resultados:
        if not r.startswith("já"):
            print(f"{s}: {r}")
    print(f"{len(resultados)} leads · {len(falhas)} falha(s)")


if __name__ == "__main__":
    main()
