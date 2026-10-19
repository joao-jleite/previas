"""Gera uma prévia de site (uma página) por lead, a partir dos JSONs de pesquisa.

Uso: python gerar.py leads.json [leads2.json ...]
Saída: docs/<slug>/index.html (publicado no GitHub Pages do repo joao-jleite/previas)
e previas.json com {email: url} para o envio.
Só usa dados públicos do lead; nada de foto copiada (ícones e cores por segmento).
"""
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

BASE_URL = "https://joao-jleite.github.io/previas"
OUT = Path(__file__).parent / "docs"

# Paleta e textos por segmento (cor principal, cor de fundo suave, chamada do botão)
TEMAS = [
    (r"odonto|dent", ("#0e7490", "#ecfeff", "Agende sua avaliação", "🦷")),
    (r"fisio|pilates|yoga|funcional|academia|studio", ("#15803d", "#f0fdf4", "Agende uma aula experimental", "🧘")),
    (r"psico|nutri|podolog", ("#7c3aed", "#f5f3ff", "Agende sua consulta", "🌿")),
    (r"estétic|estetic|harmoniza|micropig|beleza|sobrancelha", ("#be185d", "#fdf2f8", "Agende sua avaliação", "✨")),
    (r"escola|berç|berc|infantil|idioma|inglês|ingles|reforço|reforco|música|musica|dança|danca|curso", ("#ea580c", "#fff7ed", "Agende uma visita", "🎒")),
    (r"pet|veterin", ("#0d9488", "#f0fdfa", "Fale com a gente", "🐾")),
    (r"advoca|contab|imobili", ("#1e3a8a", "#eff6ff", "Fale com o escritório", "⚖️")),
    (r"móve|move|marcen|arquit|interior", ("#78350f", "#fefce8", "Peça seu orçamento", "📐")),
    (r"buffet|evento|festa", ("#a21caf", "#fdf4ff", "Consulte datas disponíveis", "🎉")),
    (r"auto|mecân|mecan|oficina", ("#b91c1c", "#fef2f2", "Peça seu orçamento", "🔧")),
]
PADRAO = ("#334155", "#f8fafc", "Fale com a gente", "⭐")


def tema(segmento: str):
    s = (segmento or "").lower()
    for padrao, t in TEMAS:
        if re.search(padrao, s):
            return t
    return PADRAO


def slug(nome: str) -> str:
    s = unicodedata.normalize("NFKD", nome).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")[:50]


def so_digitos(tel: str) -> str:
    d = re.sub(r"\D", "", tel or "")
    if d and not d.startswith("55") and len(d) in (10, 11):
        d = "55" + d
    return d


def ig_url(ig: str) -> str:
    ig = (ig or "").strip()
    if not ig:
        return ""
    if ig.startswith("http"):
        return ig
    return "https://instagram.com/" + ig.lstrip("@")


def e(x) -> str:
    return html.escape(str(x or ""), quote=True)


def pagina(lead: dict) -> str:
    cor, fundo, cta, icone = tema(lead.get("segmento", ""))
    nome = lead["nome"]
    cidade = ", ".join(x for x in [lead.get("bairro"), lead.get("cidade")] if x)
    servicos = [s for s in (lead.get("servicos") or []) if s][:6]
    difs = [d for d in (lead.get("diferenciais") or []) if d][:4]
    tel = so_digitos(lead.get("whatsapp_ou_telefone", ""))
    wa = f"https://wa.me/{tel}?text=" + "Ol%C3%A1!%20Vim%20pelo%20site." if tel else ""
    ig = ig_url(lead.get("instagram", ""))
    end = lead.get("endereco") or ""
    mapa = "https://www.google.com/maps/search/?api=1&query=" + re.sub(r"\s+", "+", e(f"{nome} {end} {lead.get('cidade','')}")) if (end or lead.get("cidade")) else ""
    btn = f'<a class="btn" href="{wa}" target="_blank" rel="noopener">{e(cta)} pelo WhatsApp</a>' if wa else (
        f'<a class="btn" href="mailto:{e(lead.get("email"))}">{e(cta)}</a>')

    cards = "".join(f'<div class="card"><span class="ico"><svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="var(--c)" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="m8 12 3 3 5-6"/></svg></span><h3>{e(s)}</h3></div>' for s in servicos)
    lista_difs = "".join(f"<li>{e(d)}</li>" for d in difs)
    sec_difs = f'<section><h2>Por que escolher a {e(nome)}</h2><ul class="difs">{lista_difs}</ul></section>' if difs else ""
    contato = []
    if end:
        contato.append(f"<p><strong>Endereço:</strong> {e(end)}</p>")
    if tel:
        contato.append(f'<p><strong>WhatsApp:</strong> <a href="{wa}">{e(lead.get("whatsapp_ou_telefone"))}</a></p>')
    if ig:
        contato.append(f'<p><strong>Instagram:</strong> <a href="{e(ig)}" target="_blank" rel="noopener">{e(lead.get("instagram"))}</a></p>')
    if lead.get("email"):
        contato.append(f'<p><strong>E-mail:</strong> {e(lead["email"])}</p>')
    if mapa:
        contato.append(f'<p><a class="link" href="{mapa}" target="_blank" rel="noopener">Ver no mapa →</a></p>')

    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{e(nome)} — prévia de site</title>
<style>
:root{{--c:{cor};--f:{fundo}}}
*{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:#1f2937;background:#fff;line-height:1.55}}
.aviso{{background:#111827;color:#e5e7eb;font-size:13px;text-align:center;padding:8px 16px}}
.aviso a{{color:#fff}}
header{{background:linear-gradient(135deg,var(--c),#111827);color:#fff;padding:72px 20px 80px;text-align:center}}
header h1{{font-size:clamp(30px,6vw,52px);margin:0 0 8px;letter-spacing:-.02em}}
header p{{margin:0 auto 28px;max-width:620px;opacity:.9;font-size:18px}}
.btn{{display:inline-block;background:#fff;color:var(--c);font-weight:700;padding:14px 26px;border-radius:999px;text-decoration:none;box-shadow:0 8px 24px rgba(0,0,0,.2)}}
main{{max-width:980px;margin:0 auto;padding:0 20px}}
section{{padding:56px 0;border-bottom:1px solid #eee}}
h2{{font-size:28px;margin:0 0 24px;color:#111827}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px}}
.card{{background:var(--f);border-radius:16px;padding:22px}}
.card h3{{margin:10px 0 0;font-size:17px}}.ico{{font-size:26px}}
.difs{{padding-left:20px;font-size:17px}}.difs li{{margin:6px 0}}
.contato{{background:var(--f);border-radius:16px;padding:24px}}
.contato p{{margin:8px 0}}a{{color:var(--c)}}.link{{font-weight:700}}
footer{{text-align:center;padding:32px 20px;color:#6b7280;font-size:14px}}
.wa{{position:fixed;right:18px;bottom:18px;background:#22c55e;color:#fff;border-radius:999px;padding:14px 18px;font-weight:700;text-decoration:none;box-shadow:0 8px 24px rgba(0,0,0,.25)}}
</style></head><body>
<div class="aviso">Prévia criada por João Leite para apresentar uma ideia à {e(nome)}. Não é o site oficial. Contato: <a href="mailto:joao.jleitewrk@gmail.com">joao.jleitewrk@gmail.com</a></div>
<header><h1>{e(nome)}</h1><p>{e(lead.get("segmento",""))}{(" em " + e(cidade)) if cidade else ""}</p>{btn}</header>
<main>
<section><h2>Nossos serviços</h2><div class="grid">{cards}</div></section>
{sec_difs}
<section><h2>Fale com a gente</h2><div class="contato">{"".join(contato)}</div></section>
</main>
<footer>{e(nome)} · {e(lead.get("cidade",""))}</footer>
{f'<a class="wa" href="{wa}" target="_blank" rel="noopener">WhatsApp</a>' if wa else ""}
</body></html>"""


def main(arquivos):
    OUT.mkdir(exist_ok=True)
    mapa_path = Path(__file__).parent / "previas.json"
    mapa = json.loads(mapa_path.read_text(encoding="utf-8")) if mapa_path.exists() else {}
    feitos = 0
    for arq in arquivos:
        try:
            leads = json.loads(Path(arq).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as err:
            print(f"ERRO lendo {arq}: {err}")
            continue
        for lead in leads:
            # Sem nome, e-mail ou serviços não dá para fazer uma prévia honesta
            if not lead.get("nome") or not lead.get("email") or len(lead.get("servicos") or []) < 2:
                print("pulado (dados insuficientes):", lead.get("nome"))
                continue
            s = slug(lead["nome"])
            (OUT / s).mkdir(exist_ok=True)
            (OUT / s / "index.html").write_text(pagina(lead), encoding="utf-8")
            mapa[lead["email"].lower()] = f"{BASE_URL}/{s}/"
            feitos += 1
    # Página raiz neutra, sem listar os negócios
    (OUT / "index.html").write_text('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title>Prévias</title><p>Prévias de sites — João Leite.</p>', encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    mapa_path.write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{feitos} prévias geradas; total no mapa: {len(mapa)}")


if __name__ == "__main__":
    main(sys.argv[1:])
