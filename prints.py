r"""Tira print de cada prévia com o Edge headless (tenta até 3 vezes por página).

Uso: python prints.py ALTURA slug1 slug2 ...  -> PNGs em %TEMP%\previas-prints
"""
import subprocess, sys, time
from pathlib import Path
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
DOCS = Path(r"C:\Users\joao-\prospeccao-previas\docs")
import tempfile
OUT = Path(tempfile.gettempdir()) / "previas-prints"; OUT.mkdir(exist_ok=True)
altura = sys.argv[1]
for s in sys.argv[2:]:
    png = OUT / f"{s}.png"
    for t in range(3):
        if png.exists(): break
        prof = OUT / f"perfil-{t}"  # perfil próprio evita conflito com um Edge já aberto
        try:
            subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--user-data-dir={prof}",
                            f"--window-size=1440,{altura}", "--virtual-time-budget=6000", f"--screenshot={png}",
                            (DOCS / s / "index.html").as_uri()], stdin=subprocess.DEVNULL, capture_output=True, timeout=60)
        except subprocess.TimeoutExpired:
            pass
        for _ in range(10):  # o Edge às vezes grava o arquivo logo depois de sair
            if png.exists(): break
            time.sleep(0.5)
    print(("ok " if png.exists() else "FALHOU ") + s)
