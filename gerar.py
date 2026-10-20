"""Gera uma prévia de site (uma página) por lead, a partir dos JSONs de pesquisa.

Uso: python gerar.py leads.json [leads2.json ...]
Saída: docs/<slug>/index.html (GitHub Pages do repo joao-jleite/previas)
e previas.json com {email: url} para o envio.
Usa só dados públicos do lead + fotos livres do Unsplash por segmento (nada copiado do negócio).
"""
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

BASE_URL = "https://joao-jleite.github.io/previas"
OUT = Path(__file__).parent / "docs"
IMG = "https://images.unsplash.com/photo-{}?auto=format&fit=crop&w={}&q=80"
STAR = "M12 2l2.4 6.6L21 9l-5 4.6L17.5 21 12 17.3 6.5 21 8 13.6 3 9l6.6-.4z"

# Configuração por segmento. A ordem importa: o primeiro padrão que casar vence
# (fisioterapia antes de pilates, para "Fisioterapia e Pilates" cair em fisio).
SEGMENTOS = [
    ("fisio", r"fisio|reabilita|ortoped|neurodesenv|quiropra|osteopat", dict(
        cor="#0f766e", escura="#134e4a", suave="#f0fdfa", fotos=["1649751361457-01d3a696c7e6", "1706353399656-210cca727a33"],
        titulo="Volte a se mover com confiança.",
        sobre="Cada tratamento começa com uma avaliação cuidadosa e segue um plano pensado para a sua rotina, com acompanhamento próximo em cada etapa da recuperação.",
        cta="Agendar avaliação", passos=["Fale com a equipe", "Avaliação inicial", "Plano de tratamento"],
        desc=["Avaliação completa e plano individual.", "Atendimento próximo, sessão a sessão.", "Foco na sua recuperação e autonomia.", "Técnicas atualizadas e cuidado humano."],
        icone="M13 4a2 2 0 1 1-4 0 2 2 0 0 1 4 0zM9 8h4l3 5-2 1-2-3v4l2 7h-2l-2-6-2 6H6l2-7z")),
    ("pilates", r"pilates|yoga|funcional|academia|treino", dict(
        cor="#4d7c0f", escura="#365314", suave="#f7fee7", fotos=["1717500252297-b09508db7ceb", "1552196527-bffef41ef674"],
        titulo="Movimento, força e equilíbrio para o seu dia a dia.",
        sobre="Aulas com atenção individual, turmas reduzidas e acompanhamento da sua evolução, para você treinar com segurança e prazer.",
        cta="Agendar aula experimental", passos=["Fale com a gente", "Aula experimental", "Escolha seu plano"],
        desc=["Turmas reduzidas e atenção individual.", "Exercícios adaptados ao seu momento.", "Evolução acompanhada de perto.", "Ambiente acolhedor e equipado."],
        icone="M13 4a2 2 0 1 1-4 0 2 2 0 0 1 4 0zM3 10h18v2h-7v10h-2v-6h-2v6H8V12H3z")),
    ("odonto", r"odonto|dent", dict(
        cor="#0369a1", escura="#0c4a6e", suave="#f0f9ff", fotos=["1629909613654-28e377c37b09", "1606811841689-23dfddce3e95"],
        titulo="Sorria com tranquilidade.",
        sobre="Atendimento cuidadoso, explicação clara de cada etapa e tratamento planejado para o seu sorriso, sem pressa e sem surpresas.",
        cta="Agendar avaliação", passos=["Fale com a clínica", "Avaliação", "Plano de tratamento"],
        desc=["Avaliação e plano claro.", "Conforto em cada etapa.", "Tecnologia a favor do seu sorriso.", "Acompanhamento após o tratamento."],
        icone="M7 3C5 3 3 5 3 8c0 4 2 5 2 9 0 2 1 4 2 4 2 0 1-6 5-6s3 6 5 6c1 0 2-2 2-4 0-4 2-5 2-9 0-3-2-5-4-5-2 0-3 1-5 1S9 3 7 3z")),
    ("psico", r"psic|terapeut", dict(
        cor="#6d28d9", escura="#4c1d95", suave="#f5f3ff", fotos=["1595846723416-99a641e1231a", "1673892990360-2168cc2c25d6"],
        titulo="Um espaço seguro para cuidar de você.",
        sobre="Atendimento acolhedor, sigiloso e no seu tempo, para você compreender melhor o que sente e encontrar novos caminhos.",
        cta="Agendar primeira conversa", passos=["Mande uma mensagem", "Primeira conversa", "Início do acompanhamento"],
        desc=["Escuta atenta e sem julgamentos.", "Atendimento sigiloso.", "Acompanhamento no seu tempo.", "Cuidado contínuo."],
        icone="M12 21s-8-5-8-11a5 5 0 0 1 8-4 5 5 0 0 1 8 4c0 6-8 11-8 11z")),
    ("nutri", r"nutri", dict(
        cor="#15803d", escura="#14532d", suave="#f0fdf4", fotos=["1490645935967-10de6ba17061", "1512621776951-a57141f2eefd"],
        titulo="Alimentação que cabe na sua rotina.",
        sobre="Planos alimentares individualizados, sem dietas impossíveis, com acompanhamento para você chegar ao seu objetivo de forma sustentável.",
        cta="Agendar consulta", passos=["Fale comigo", "Consulta e avaliação", "Plano e acompanhamento"],
        desc=["Plano alimentar individual.", "Metas realistas e acompanhamento.", "Orientação prática para o dia a dia.", "Retornos para ajustar o plano."],
        icone="M17 8C8 10 6 16 4 21l2 1 1-2.5c1 .5 2 .5 3 .5 9 0 11-14 11-14-1 2-8 2-13 6 3-3 7-4 9-5z")),
    ("podologia", r"podolog", dict(
        cor="#0e7490", escura="#164e63", suave="#ecfeff", fotos=["1675159364615-38e1f6b62282", "1611073615830-9f76902c10fe"],
        titulo="Cuidado especializado para os seus pés.",
        sobre="Atendimento com higiene rigorosa, materiais esterilizados e orientação para você caminhar com conforto todos os dias.",
        cta="Agendar atendimento", passos=["Fale com a gente", "Avaliação", "Tratamento e orientação"],
        desc=["Materiais esterilizados.", "Atendimento cuidadoso.", "Orientação para o dia a dia.", "Acompanhamento do tratamento."],
        icone=STAR)),
    ("estetica", r"estétic|estetic|harmoniza|micropig|sobrancelha|depila|bem.estar|clinic", dict(
        cor="#be185d", escura="#831843", suave="#fdf2f8", fotos=["1570172619644-dfd03ed5d881", "1552693673-1bf958298935"],
        titulo="Realce a sua beleza com quem entende de cuidado.",
        sobre="Protocolos personalizados, produtos de qualidade e um atendimento acolhedor, para você se sentir bem do primeiro contato ao resultado.",
        cta="Agendar avaliação", passos=["Fale com a gente", "Avaliação personalizada", "Seu protocolo"],
        desc=["Avaliação personalizada.", "Protocolos para o seu objetivo.", "Produtos e equipamentos de qualidade.", "Atendimento acolhedor."],
        icone=STAR)),
    ("beleza", r"salão|salao|cabelei|barbear|beleza|unha|manicure", dict(
        cor="#a21caf", escura="#701a75", suave="#fdf4ff", fotos=["1580618672591-eb180b1a973f", "1633681926022-84c23e8cb2d6"],
        titulo="Seu momento de cuidado começa aqui.",
        sobre="Profissionais atentos ao que você quer, ambiente confortável e atendimento com hora marcada, sem correria.",
        cta="Agendar horário", passos=["Chame no WhatsApp", "Escolha o horário", "Venha se cuidar"],
        desc=["Atendimento com hora marcada.", "Profissionais atentos.", "Produtos de qualidade.", "Ambiente confortável."],
        icone=STAR)),
    ("pet", r"\bpets?\b|veterin|animal|tosa", dict(
        cor="#0d9488", escura="#115e59", suave="#f0fdfa", fotos=["1632236542159-809925d85fc0", "1654895716780-b4664497420d"],
        titulo="Cuidado de verdade para quem é da família.",
        sobre="Atendimento carinhoso, profissionais que amam animais e um ambiente tranquilo para o seu pet se sentir em casa.",
        cta="Agendar atendimento", passos=["Chame no WhatsApp", "Agende o horário", "Traga seu pet"],
        desc=["Atendimento carinhoso.", "Profissionais dedicados.", "Ambiente limpo e tranquilo.", "Agendamento fácil."],
        icone="M5 10a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm14 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4zM9 7a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm6 0a2 2 0 1 0 0-4 2 2 0 0 0 0 4zm-3 4c-4 0-7 6-7 8s2 3 4 3 2-1 3-1 1 1 3 1 4-1 4-3-3-8-7-8z")),
    ("escola", r"escola|berç|berc|infantil|educa|creche|recrea|idioma|inglês|ingles|reforço|reforco|música|musica|dança|danca|curso", dict(
        cor="#c2410c", escura="#7c2d12", suave="#fff7ed", fotos=["1594608661623-aa0bd3a69d98", "1503676260728-1c00da094a0b"],
        titulo="Um lugar para crescer, brincar e aprender.",
        sobre="Uma rotina pensada para cada fase, equipe próxima das famílias e um ambiente seguro e acolhedor, onde cada criança é vista de verdade.",
        cta="Agendar uma visita", passos=["Fale com a escola", "Visite o espaço", "Garanta a vaga"],
        desc=["Rotina pensada para cada idade.", "Equipe próxima das famílias.", "Ambiente seguro e acolhedor.", "Aprender brincando."],
        icone="M12 3 1 9l11 6 9-4.9V17h2V9zM5 13v4c0 2 3 4 7 4s7-2 7-4v-4l-7 4z")),
    ("buffet", r"buffet|evento|festa|decora", dict(
        cor="#db2777", escura="#831843", suave="#fdf2f8", fotos=["1530103862676-de8c9debad1d", "1531956531700-dc0ee0f1f9a5"],
        titulo="A festa que você imaginou, do jeito que você sonhou.",
        sobre="Estrutura completa, equipe atenciosa e cuidado em cada detalhe, para você aproveitar a festa enquanto a equipe cuida do resto.",
        cta="Consultar datas", passos=["Conte sua ideia", "Monte seu pacote", "Aproveite a festa"],
        desc=["Estrutura completa.", "Equipe atenciosa do início ao fim.", "Pacotes para cada ocasião.", "Cuidado em cada detalhe."],
        icone=STAR)),
    ("moveis", r"móve|move|marcen|planejad|arquit|interior", dict(
        cor="#92400e", escura="#451a03", suave="#fffbeb", fotos=["1600489000022-c2086d79f9d4", "1622372738946-62e02505feb3"],
        titulo="Ambientes sob medida para o jeito que você vive.",
        sobre="Do projeto à instalação, cada peça é pensada para aproveitar o espaço com funcionalidade, durabilidade e acabamento de qualidade.",
        cta="Pedir orçamento", passos=["Conte o seu projeto", "Medição e proposta", "Produção e instalação"],
        desc=["Projeto sob medida.", "Materiais de qualidade.", "Acabamento cuidadoso.", "Instalação no prazo combinado."],
        icone="M3 3h18v18H3zm2 2v6h6V5zm8 0v14h6V5zM5 13v6h6v-6z")),
    ("auto", r"auto|mecân|mecan|oficina|funilar|carro|vidra", dict(
        cor="#b91c1c", escura="#450a0a", suave="#fef2f2", fotos=["1633014041037-f5446fb4ce99", "1567808291548-fc3ee04dbcf0"],
        titulo="Seu carro em boas mãos.",
        sobre="Serviço honesto, orçamento claro antes de começar e cuidado com cada detalhe, para você sair tranquilo e voltar quando precisar.",
        cta="Pedir orçamento", passos=["Chame no WhatsApp", "Orçamento sem surpresa", "Serviço e entrega"],
        desc=["Orçamento claro antes do serviço.", "Equipe experiente.", "Peças e produtos de qualidade.", "Atendimento ágil."],
        icone="M5 11l2-5h10l2 5h1v6h-2v2h-2v-2H8v2H6v-2H4v-6zm2.5 2a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm9 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3z")),
]
PADRAO = next(cfg for k, _, cfg in SEGMENTOS if k == "estetica")  # estética como visual neutro de serviço


def segmento(lead: dict) -> dict:
    texto = f"{lead.get('segmento', '')} {lead.get('nome', '')}".lower()
    for _, padrao, cfg in SEGMENTOS:
        if re.search(padrao, texto):
            return cfg
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
    return ig if ig.startswith("http") else "https://instagram.com/" + ig.lstrip("@")


def frase(s: str) -> str:
    """Primeira letra maiúscula, resto como veio (preserva siglas)."""
    s = (s or "").strip().rstrip(".")
    return s[:1].upper() + s[1:]


def e(x) -> str:
    return html.escape(str(x or ""), quote=True)


def svg(path: str, size: int = 24) -> str:
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" aria-hidden="true"><path d="{path}" fill="currentColor"/></svg>'


WA = "M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2zm0 18.2a8.2 8.2 0 0 1-4.2-1.1l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.2-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.8 11.9 11.9 0 0 0 4.6 4c1.7.7 2.4.8 3.2.7.5-.1 1.5-.6 1.7-1.2.2-.6.2-1.1.2-1.2-.1-.1-.3-.2-.5-.3z"
TEL = "M6.6 10.8a15 15 0 0 0 6.6 6.6l2.2-2.2c.3-.3.7-.4 1-.2 1.1.4 2.3.6 3.6.6.6 0 1 .4 1 1V20c0 .6-.4 1-1 1A17 17 0 0 1 3 4c0-.6.4-1 1-1h3.5c.6 0 1 .4 1 1 0 1.3.2 2.5.6 3.6.1.3 0 .7-.2 1z"
CHECK = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="m5 12 4 4 10-10" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/></svg>'

CSS = """
:root{--ink:#1c1917;--mut:#57534e;--line:#e7e5e4}
*{box-sizing:border-box}html{scroll-behavior:smooth}
body{margin:0;font-family:Inter,system-ui,sans-serif;color:var(--ink);background:#fff;line-height:1.6;-webkit-font-smoothing:antialiased}
h1,h2,h3{font-family:Fraunces,Georgia,serif;font-weight:600;letter-spacing:-.02em;line-height:1.12;margin:0}
a{color:inherit}img{display:block;max-width:100%}
.wrap{max-width:1160px;margin:0 auto;padding:0 24px}
.aviso{background:#1c1917;color:#d6d3d1;font-size:12.5px;text-align:center;padding:7px 16px}.aviso a{color:#fff}
nav{position:sticky;top:0;z-index:20;background:rgba(255,255,255,.9);backdrop-filter:blur(12px);border-bottom:1px solid var(--line)}
nav .wrap{display:flex;align-items:center;justify-content:space-between;height:68px;gap:16px}
.marca{display:flex;align-items:center;gap:10px;font-weight:600;text-decoration:none;font-size:16px;min-width:0}
.marca span{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.marca i{width:38px;height:38px;border-radius:50%;background:var(--c);color:#fff;display:grid;place-items:center;font:600 18px Fraunces,serif;font-style:normal;flex:none}
.links{display:flex;gap:28px;font-size:14.5px;color:var(--mut)}.links a{text-decoration:none}.links a:hover{color:var(--c)}
.btn{display:inline-flex;align-items:center;gap:9px;background:var(--c);color:#fff;text-decoration:none;font-weight:600;font-size:15px;padding:14px 24px;border-radius:999px;transition:transform .2s,box-shadow .2s;box-shadow:0 10px 24px -10px var(--c);white-space:nowrap}
.btn:hover{transform:translateY(-2px);box-shadow:0 16px 30px -12px var(--c)}
.btn.sm{padding:10px 18px;font-size:14px}.btn.lt{background:#fff;color:var(--d);box-shadow:none}
.ghost{display:inline-flex;align-items:center;padding:14px 22px;border-radius:999px;border:1.5px solid var(--line);text-decoration:none;font-weight:600;font-size:15px;background:#fff}
.hero{background:linear-gradient(180deg,var(--s),#fff 85%);padding:72px 0 88px}
.hero .wrap{display:grid;grid-template-columns:1.05fr 1fr;gap:56px;align-items:center}
.tag{display:inline-block;background:#fff;border:1px solid var(--line);color:var(--d);font-size:13px;font-weight:600;padding:6px 14px;border-radius:999px;margin-bottom:22px}
.hero h1{font-size:clamp(36px,5vw,60px)}
.hero p.lead{font-size:18.5px;color:var(--mut);margin:20px 0 30px;max-width:520px}
.acoes{display:flex;gap:12px;flex-wrap:wrap}
.chips{list-style:none;padding:0;margin:30px 0 0;display:grid;gap:10px}
.chips li{display:flex;gap:10px;align-items:center;font-size:15px}.chips svg{color:var(--c);flex:none}
.foto{position:relative}
.foto img{width:100%;aspect-ratio:1/1.05;object-fit:cover;border-radius:28px;box-shadow:0 30px 60px -30px rgba(0,0,0,.35)}
.selo{position:absolute;left:-22px;bottom:34px;background:#fff;border-radius:18px;padding:14px 18px;box-shadow:0 18px 40px -18px rgba(0,0,0,.3);display:flex;gap:12px;align-items:center;max-width:280px;font-size:14px;font-weight:500}
.selo b{width:40px;height:40px;border-radius:12px;background:var(--s);color:var(--c);display:grid;place-items:center;flex:none}
section{padding:96px 0}
.cab{max-width:640px;margin-bottom:48px}.cab small{color:var(--c);font-weight:600;letter-spacing:.08em;text-transform:uppercase;font-size:12.5px}
.cab h2{font-size:clamp(30px,3.6vw,42px);margin-top:10px}.cab p{color:var(--mut);font-size:17px;margin:14px 0 0}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:20px}
.card{border:1px solid var(--line);border-radius:22px;padding:28px;background:#fff;transition:transform .25s,box-shadow .25s,border-color .25s}
.card:hover{transform:translateY(-4px);box-shadow:0 24px 48px -28px rgba(0,0,0,.28);border-color:transparent}
.ic{width:52px;height:52px;border-radius:16px;background:var(--s);color:var(--c);display:grid;place-items:center;margin-bottom:20px}
.card h3{font-size:21px}.card p{color:var(--mut);margin:8px 0 0;font-size:15px}
.sobre{background:var(--s)}.sobre .wrap{display:grid;grid-template-columns:1fr 1.1fr;gap:64px;align-items:center}
.sobre img{width:100%;aspect-ratio:5/4;object-fit:cover;border-radius:28px}
.sobre ul{padding:0;list-style:none;margin:26px 0 0;display:grid;gap:12px}
.sobre li{background:#fff;border-radius:14px;padding:14px 18px;font-weight:500;border-left:4px solid var(--c)}
.passos{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}
.passo{padding:30px;border-radius:22px;background:#fafaf9;border:1px solid var(--line)}
.passo span{display:inline-grid;place-items:center;width:44px;height:44px;border-radius:50%;background:var(--c);color:#fff;font-weight:600;margin-bottom:18px}
.passo h3{font-size:21px}
.faixa{padding:0 0 96px}.faixa .box{background:linear-gradient(135deg,var(--c),var(--d));color:#fff;border-radius:32px;padding:56px;display:flex;justify-content:space-between;align-items:center;gap:28px;flex-wrap:wrap}
.faixa h2{font-size:clamp(28px,3.4vw,40px);max-width:560px}.faixa p{opacity:.85;margin:10px 0 0}
.contato .wrap{display:grid;grid-template-columns:1fr 1.25fr;gap:40px;align-items:stretch}
dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:14px 22px;font-size:16px}dt{color:var(--mut);font-size:14px;padding-top:2px}dd{margin:0;font-weight:500;word-break:break-word}
.mapa{border-radius:24px;overflow:hidden;min-height:340px;border:1px solid var(--line)}.mapa iframe{border:0;width:100%;height:100%;min-height:340px;display:block}
footer{border-top:1px solid var(--line);padding:34px 0;color:var(--mut);font-size:14px}footer .wrap{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.flt{position:fixed;right:22px;bottom:22px;width:60px;height:60px;border-radius:50%;background:#25d366;color:#fff;display:grid;place-items:center;box-shadow:0 14px 30px -10px rgba(0,0,0,.45);z-index:30}
.flt svg{width:30px;height:30px}
.rev{opacity:0;transform:translateY(18px);transition:opacity .7s ease,transform .7s ease}.rev.on{opacity:1;transform:none}
@media (max-width:900px){.hero .wrap,.sobre .wrap,.contato .wrap{grid-template-columns:1fr}.links{display:none}.passos{grid-template-columns:1fr}.selo{left:14px}.hero{padding:44px 0 64px}section{padding:72px 0}.faixa .box{padding:36px 28px}}
@media (max-width:520px){.wrap{padding:0 16px}nav .btn.sm{display:none}}
"""


def pagina(lead: dict) -> str:
    c = segmento(lead)
    nome = lead["nome"]
    curto = lead.get("nome_email") or nome  # nome curto para títulos ("Clínica Ceccato")
    cidade = lead.get("cidade") or ""
    local = ", ".join(x for x in [lead.get("bairro"), cidade] if x)
    # "fisioterapia / estética" -> "Fisioterapia e estética" (barra e parênteses ficam feios no selo)
    seg_txt = frase(re.sub(r"\s*/\s*", " e ", re.sub(r"\s*\(.*?\)", "", lead.get("segmento") or "")))
    servicos = [frase(s) for s in (lead.get("servicos") or []) if s][:6]
    # Métrica de rede social (seguidores, check-ins) não é argumento de site: fica de fora
    # Aspas de citação da bio e parênteses explicativos não ficam bem no selo
    difs = [frase(re.sub(r"\s*\([^)]*\)", "", d).replace("'", "").replace('"', "")) for d in (lead.get("diferenciais") or []) if d and not re.search(r"seguidor|check-in|curtida|follower|cnpj|\bposts?\b|desconto|\bcita\b|evento de anivers", d, re.I)][:4]
    tel = so_digitos(lead.get("whatsapp_ou_telefone", ""))
    celular = len(tel) == 13  # 55 + DDD + 9 dígitos = celular/WhatsApp
    if celular:
        link = f"https://wa.me/{tel}?text=" + "Ol%C3%A1!%20Vim%20pelo%20site%20e%20gostaria%20de%20mais%20informa%C3%A7%C3%B5es."
        canal, icon = "WhatsApp", svg(WA, 20)
    elif tel:
        link, canal, icon = f"tel:+{tel}", "telefone", svg(TEL, 20)
    else:
        link, canal, icon = f"mailto:{lead.get('email', '')}", "e-mail", ""
    alvo = 'target="_blank" rel="noopener"' if link.startswith("http") else ""
    ig = ig_url(lead.get("instagram", ""))
    end = lead.get("endereco") or ""
    q = re.sub(r"\s+", "+", f"{curto} {end} {cidade}".strip())
    mapa = f"https://maps.google.com/maps?q={e(q)}&output=embed" if (end or cidade) else ""
    inicial = re.sub(r"[^A-Za-zÀ-ÿ]", "", curto)[:1].upper() or "•"
    f1, f2 = c["fotos"][0], c["fotos"][1]
    var = f"--c:{c['cor']};--d:{c['escura']};--s:{c['suave']}"
    # Artigo do nome: "da Clínica", "do Espaço"
    art = "do" if curto.split()[0].lower() in ("espaço", "studio", "estúdio", "centro", "consultório", "instituto", "ateliê", "buffet", "colégio", "núcleo") else "da"

    chips = "".join(f"<li>{CHECK}{e(d)}</li>" for d in difs[:3])
    cards = "".join(
        f'<article class="card rev"><span class="ic">{svg(c["icone"], 26)}</span>'
        f'<h3>{e(s)}</h3><p>{e(c["desc"][i % len(c["desc"])])}</p></article>'
        for i, s in enumerate(servicos))
    # Completa a lista do "Sobre" com os pontos do segmento quando há poucos diferenciais
    # Não repete frase que já apareceu nos cards de serviço
    usados = {c["desc"][i % len(c["desc"])] for i in range(len(servicos))}
    itens = (difs[1:] if len(difs) > 1 else []) + [d for d in c["desc"] if d not in difs and d not in usados]
    lista = "".join(f"<li>{e(d)}</li>" for d in itens[:3])
    passos = "".join(f'<div class="passo rev"><span>{i + 1}</span><h3>{e(p)}</h3></div>' for i, p in enumerate(c["passos"]))
    contato = []
    if end:
        contato.append(f"<dt>Endereço</dt><dd>{e(end)}</dd>")
    if tel:
        contato.append(f'<dt>{"WhatsApp" if celular else "Telefone"}</dt><dd><a href="{link}" {alvo}>{e(lead.get("whatsapp_ou_telefone"))}</a></dd>')
    if ig:
        contato.append(f'<dt>Instagram</dt><dd><a href="{e(ig)}" target="_blank" rel="noopener">{e(lead.get("instagram"))}</a></dd>')
    if lead.get("email"):
        contato.append(f'<dt>E-mail</dt><dd><a href="mailto:{e(lead["email"])}">{e(lead["email"])}</a></dd>')
    flutuante = f'<a class="flt" href="{link}" {alvo} aria-label="Fale pelo {canal}">{icon}</a>' if tel else ""
    # Selo da foto: prefere nota/tempo de casa; senão, a cidade. Não repete o que já está nos chips.
    forte = [d for d in difs if re.search(r"nota|avalia|anos|desde|★", d, re.I)]
    selo = forte[0] if forte else (f"Atendimento em {cidade}" if cidade else seg_txt)
    escola = c is next(cfg for k, _, cfg in SEGMENTOS if k == "escola")
    rot = "Turmas" if escola else "Serviços"
    tit_serv = "Uma proposta para cada fase" if escola else "O que oferecemos"
    sub_serv = "Do primeiro dia à rotina, tudo pensado para o desenvolvimento das crianças." if escola else "Atendimento pensado para você, do primeiro contato ao resultado."
    em_cidade = f" em {e(cidade)}" if cidade else ""

    return f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{e(curto)} | {e(seg_txt)}{em_cidade}</title>
<meta name="description" content="{e(curto)}: {e(seg_txt)}{em_cidade}. {e(c['cta'])} pelo {canal}.">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body style="{var}">
<div class="aviso">Prévia de site criada por João Leite para {"o" if art == "do" else "a"} {e(curto)}. Não é o site oficial. <a href="mailto:joao.jleitewrk@gmail.com">joao.jleitewrk@gmail.com</a></div>
<nav><div class="wrap"><a class="marca" href="#inicio"><i>{e(inicial)}</i><span>{e(curto)}</span></a>
<div class="links"><a href="#servicos">{rot}</a><a href="#sobre">Sobre</a><a href="#como">Como funciona</a><a href="#contato">Contato</a></div>
<a class="btn sm" href="{link}" {alvo}>{e(c['cta'])}</a></div></nav>
<header class="hero" id="inicio"><div class="wrap">
<div><span class="tag">{e(seg_txt)}{(" · " + e(local)) if local else ""}</span>
<h1>{e(c['titulo'])}</h1>
<p class="lead">{e(seg_txt)} com atenção de verdade{em_cidade}. Fale com a equipe {art} {e(curto)} pelo {canal} e tire suas dúvidas em poucos minutos.</p>
<div class="acoes"><a class="btn" href="{link}" {alvo}>{icon}{e(c['cta'])}</a><a class="ghost" href="#servicos">Ver {rot.lower()}</a></div>
{f'<ul class="chips">{chips}</ul>' if chips else ''}</div>
<div class="foto"><img src="{IMG.format(f1, 1100)}" alt="" loading="eager">
<div class="selo"><b>{svg(STAR, 20)}</b>{e(selo)}</div></div>
</div></header>
<section id="servicos"><div class="wrap"><div class="cab"><small>{rot}</small><h2>{tit_serv}</h2><p>{sub_serv}</p></div>
<div class="grid">{cards}</div></div></section>
<section class="sobre" id="sobre"><div class="wrap"><img class="rev" src="{IMG.format(f2, 1000)}" alt="" loading="lazy">
<div class="rev"><div class="cab" style="margin:0"><small>Sobre {"o" if art == "do" else "a"} {e(curto)}</small><h2>Cuidado de perto, do jeito que deve ser</h2><p>{e(c['sobre'])}</p></div>{f'<ul>{lista}</ul>' if lista else ''}</div></div></section>
<section id="como"><div class="wrap"><div class="cab"><small>Como funciona</small><h2>Simples do começo ao fim</h2></div><div class="passos">{passos}</div></div></section>
<div class="faixa"><div class="wrap"><div class="box rev"><div><h2>{e(c['cta'])} hoje mesmo</h2><p>Resposta rápida pelo {canal}.</p></div><a class="btn lt" href="{link}" {alvo}>{icon}{e(c['cta'])}</a></div></div></div>
<section class="contato" id="contato" style="padding-top:0"><div class="wrap"><div><div class="cab"><small>Contato</small><h2>Fale com a gente</h2></div><dl>{"".join(contato)}</dl></div>
{f'<div class="mapa"><iframe src="{mapa}" loading="lazy" title="Mapa"></iframe></div>' if mapa else ''}</div></section>
<footer><div class="wrap"><span>© 2026 {e(curto)}{(" · " + e(cidade)) if cidade else ""}</span><span>Prévia por João Leite</span></div></footer>
{flutuante}
<script>const io=new IntersectionObserver(es=>es.forEach(x=>{{if(x.isIntersecting){{x.target.classList.add('on');io.unobserve(x.target)}}}}),{{threshold:.12}});document.querySelectorAll('.rev').forEach(el=>io.observe(el));</script>
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
            # Sem nome, e-mail ou ao menos um serviço não dá para fazer uma prévia honesta
            if not lead.get("nome") or not lead.get("email") or not lead.get("servicos"):
                print("pulado (dados insuficientes):", lead.get("nome"))
                continue
            s = slug(lead["nome"])  # slug fixo: links já enviados continuam valendo
            (OUT / s).mkdir(exist_ok=True)
            (OUT / s / "index.html").write_text(pagina(lead), encoding="utf-8")
            mapa[lead["email"].lower()] = f"{BASE_URL}/{s}/"
            feitos += 1
    (OUT / "index.html").write_text('<!doctype html><meta charset="utf-8"><meta name="robots" content="noindex"><title>Prévias</title><p>Prévias de sites — João Leite.</p>', encoding="utf-8")
    (OUT / ".nojekyll").write_text("")
    mapa_path.write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{feitos} prévias geradas; total no mapa: {len(mapa)}")


if __name__ == "__main__":
    main(sys.argv[1:])
