"""Quem abriu a prévia e quem clicou em "quero este site" (contador na Cloudflare, pasta contador/).

Uso: python sinal.py          -> resumo do teste A/B + lista de leads quentes (JSON no fim)
Lê o D1 "previas-sinal" pelo wrangler já logado (sem chave no código) e cruza com envios.json.
"""
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

R = Path(__file__).parent


def carregar(p, padrao):
    try:
        return json.loads((R / p).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return padrao


def eventos():
    sql = "SELECT slug, tipo, count(*) n, max(quando) ultima FROM eventos GROUP BY slug, tipo"
    try:
        r = subprocess.run("npx --no-install wrangler d1 execute previas-sinal --remote --json --command \"" + sql + "\"",
                           cwd=R / "contador", capture_output=True, text=True, encoding="utf-8", timeout=120, shell=True)
        return json.loads(r.stdout)[0]["results"]
    except Exception as e:  # sem rede ou wrangler deslogado: a rodada segue sem o sinal
        sys.exit(f"sinal indisponível: {type(e).__name__}")


def main():
    previas = carregar("previas.json", {})
    por_slug = defaultdict(lambda: {"visita": 0, "clique": 0, "ultima": ""})
    for ev in eventos():
        d = por_slug[ev["slug"]]
        d[ev["tipo"]] = ev["n"]
        d["ultima"] = max(d["ultima"], ev["ultima"])
    ab = defaultdict(lambda: [0, 0, 0])  # variante -> [enviados, abriram a prévia, responderam]
    quentes = []
    for x in carregar("envios.json", []):
        slug = x.get("previa") or (previas.get(x["to"], "").rstrip("/").rsplit("/", 1)[-1])
        s = por_slug.get(slug, {"visita": 0, "clique": 0, "ultima": ""})
        respondeu = x.get("status") not in ("enviado", "devolvido")
        v = ab[x.get("variante") or "antigo"]
        v[0] += 1; v[1] += s["visita"] > 0; v[2] += respondeu
        # Quente: clicou em "quero este site" ou abriu 2+ vezes, e ainda não respondeu
        if not respondeu and (s["clique"] or s["visita"] >= 2):
            quentes.append({"to": x["to"], "nome": x["nome"], "visitas": s["visita"], "cliques": s["clique"], "ultima": s["ultima"]})
    for k, (n, viu, resp) in sorted(ab.items()):
        print(f"variante {k}: {n} enviados, {viu} abriram a prévia ({viu / n:.0%}), {resp} responderam")
    print(json.dumps(sorted(quentes, key=lambda q: (-q["cliques"], -q["visitas"])), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
