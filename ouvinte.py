"""Ouvinte do bot da prospecção (20/10/2026): responde ao João NA HORA, como o Choppy faz no robô de trade.

Mesmo padrão do Choppy (long polling na Bot API, só o chat do João, IA para texto livre), com bot, token e
arquivos próprios. Nada do Choppy/fimate é usado.
  - status / ajuda: resposta fixa, sem IA, em ~1 s (envios de hoje e total, fila, interessados, recusas, último
    registro e instruções pendentes do RESPOSTAS.md);
  - qualquer outro texto: o Claude CLI (Haiku, sem ferramentas) responde com o contexto da prospecção
    (PLAYBOOK, RESPOSTAS, roteiros, envios). Se for uma decisão dele ("pode passar R$ 1.800 para a Thais"), ela vai
    para RESPOSTAS.md, seção "Instruções do João (Telegram)", como [pendente], para a rodada das 9h/13h/16h aplicar.
  - toda mensagem fica em telegram_entrada.json (com a resposta dada); `python telegram.py respostas` entrega à
    rodada as não lidas. O ouvinte é o único leitor do bot (trava telegram_ouvinte.lock).

Fica ligado sempre: tarefa ProspBot-iniciar (instala_ouvinte.ps1) no logon e a cada 5 min (se já estiver rodando, o
Agendador ignora; se caiu, sobe de novo). Rede fora: reconecta sozinho. Log em ouvinte.log.
  pythonw ouvinte.py                     # o que a tarefa chama (sem janela)
  python ouvinte.py --simula "texto"     # só imprime o que responderia: não lê nem manda Telegram, não grava nada
"""
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import unicodedata
from collections import Counter
from datetime import datetime, timedelta

import telegram as T   # tg, le, grava, trava, entrada_guarda, ESTADO, ENVIADAS, ENTRADA

AQUI = T.AQUI
LOG = os.path.join(AQUI, "ouvinte.log")
ENVIOS = os.path.join(AQUI, "envios.json")
FILA = os.path.join(AQUI, "fila.json")
PLAYBOOK = os.path.join(AQUI, "PLAYBOOK.md")
RESP_MD = os.path.join(AQUI, "RESPOSTAS.md")
MODELO = "claude-haiku-5-5"
ESCUTA_S = 50                        # long polling: o Telegram segura a conexão até chegar mensagem
SEM_JANELA = 0x08000000              # CREATE_NO_WINDOW: o claude.exe não abre console
RODADAS = (9, 13, 16)                # horários da rotina prospeccao-email-previas (dias úteis)
SECAO = "## Instruções do João (Telegram)"
EXPLICA = ("Decisões que o João mandou pelo bot (gravadas pelo ouvinte.py). A rodada aplica e troca [pendente] "
           "por [aplicada DD/MM HH:MM].")

AJUDA = ("Bot da prospecção. Pode escrever normal que eu entendo.\n"
         "- status: envios de hoje, fila, interessados e o último registro\n"
         "- ajuda: esta mensagem\n"
         "- qualquer pergunta sobre os contatos (ex.: a Thais respondeu?)\n"
         "- decisões (ex.: pode passar R$ 1.800 para a Thais): eu registro e a rodada das 9h/13h/16h aplica.\n"
         "E-mail para cliente só sai na rodada; por aqui eu não mando nada sozinho.")

SISTEMA = """Você é o assistente da prospecção de sites do João Leite (freelancer de sites, Embu das Artes/SP) e
conversa com ele pelo Telegram, no bot da prospecção. Ele manda prévias de site por e-mail frio para negócios locais;
uma rotina automática (dias úteis 9h, 13h e 16h) lê o Gmail, responde os contatos como se fosse ele, faz follow-up e
envia novos e-mails (até 40/dia). Você NÃO envia e-mails nem mexe em nada: só conversa e registra decisões.

Responda em português do Brasil, direto, curto (até 80 palavras), sem markdown, sem asteriscos. Use só os fatos
fornecidos; não invente nome, número, valor ou data. Se não souber, diga que não está nos registros.

Campo "instrucao": preencha só quando a mensagem dele for uma decisão ou ordem para a prospecção (valor ou desconto
para um contato, o que responder a alguém, mandar ou não mandar algo, não contatar alguém, pausar/retomar envios,
mudar o texto do e-mail, mudar o teto etc.). Escreva-a em uma frase autossuficiente para a rotina aplicar sem ver a
conversa: quem (nome do negócio e e-mail, se estiver nos registros), o quê e o valor. Na resposta, confirme em uma
frase o que ficou registrado e que a rodada das HORA aplica (use a próxima rodada dos fatos). Nunca diga que já
mandou e-mail. Se não der para saber a quem a decisão se refere ou ela estiver ambígua, deixe "instrucao" vazia e
pergunte. Pergunta, comentário ou agradecimento: "instrucao" vazia."""

SCHEMA = {"type": "object", "additionalProperties": False, "required": ["resposta", "instrucao"],
          "properties": {"resposta": {"type": "string"}, "instrucao": {"type": "string"}}}


def log(txt):
    """Log em arquivo (o pythonw não tem console). Passou de 1 MB: fica a metade mais nova."""
    try:
        if os.path.exists(LOG) and os.path.getsize(LOG) > 1_000_000:
            with open(LOG, encoding="utf-8", errors="replace") as f:
                resto = f.read()[-500_000:]
            with open(LOG, "w", encoding="utf-8") as f:
                f.write(resto)
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} {txt}\n")
    except OSError:
        pass                                      # log travado não derruba o ouvinte


def norm(txt):
    """minúsculas, sem acento e sem pontuação (para reconhecer os comandos)."""
    t = unicodedata.normalize("NFKD", txt.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9 ]+", " ", t).strip()


def le_txt(caminho, limite=40_000):
    try:
        with open(caminho, encoding="utf-8", errors="replace") as f:
            return f.read()[:limite]
    except OSError:
        return ""


# ------------------------------------------------------------------ fatos (status)
def proxima_rodada(agora):
    """Próximo horário da rotina (dias úteis 9h/13h/16h), em texto: 'hoje 13h', 'amanhã 9h', 'seg 9h'."""
    for dias in range(8):
        d = agora.date() + timedelta(days=dias)
        if d.weekday() >= 5:
            continue
        for h in RODADAS:
            if dias or h * 60 > agora.hour * 60 + agora.minute:
                quando = "hoje" if dias == 0 else "amanhã" if dias == 1 else ["seg", "ter", "qua", "qui", "sex"][d.weekday()]
                return f"{quando} {h}h"
    return "próximo dia útil 9h"


def instrucoes_pendentes(md):
    """Linhas [pendente] da seção de instruções do RESPOSTAS.md."""
    if SECAO not in md:
        return []
    trecho = md.split(SECAO, 1)[1].split("\n## ", 1)[0]
    return [l[2:].strip() for l in trecho.splitlines() if l.startswith("- ") and "[pendente]" in l]


def ultimo_registro(md):
    """1ª entrada de '## Rodadas' (o RESPOSTAS.md põe a mais recente no topo)."""
    trecho = md.split("## Rodadas", 1)[-1]
    for l in trecho.splitlines():
        if l.startswith("- "):
            return l[2:].strip()
    return ""


def status():
    agora = datetime.now()
    envios = T.le(ENVIOS, [])
    fila = T.le(FILA, [])
    feitos = {x.get("to") for x in envios}
    pend = [x for x in fila if x.get("to") not in feitos]      # mesma conta do `reg.py prox`
    hoje = agora.strftime("%Y-%m-%d")
    st = Counter(x.get("status") for x in envios)
    inter = [x.get("nome", x.get("to")) for x in envios if x.get("status") == "interessado"]
    md = le_txt(RESP_MD, 200_000)
    ult = ultimo_registro(md)
    instr = instrucoes_pendentes(md)
    L = [f"Prospecção agora ({agora:%d/%m %H:%M}):",
         f"- Enviados hoje: {sum(1 for x in envios if str(x.get('quando', '')).startswith(hoje))} (teto 40) | total: {len(envios)}",
         f"- Na fila para enviar: {len(pend)}",
         f"- Interessados: {len(inter)}" + (f" ({', '.join(inter)})" if inter else ""),
         f"- Recusas: {st.get('nao_contatar', 0)} | devolvidos: {st.get('devolvido', 0)}",
         f"- Próxima rodada: {proxima_rodada(agora)}"]
    if instr:
        L.append(f"- Suas instruções esperando a rodada: {len(instr)}")
        L += [f"  • {i[:160]}" for i in instr[:5]]
    if ult:
        L.append(f"\nÚltimo registro: {ult[:300]}" + ("…" if len(ult) > 300 else ""))
    return "\n".join(L)


# ------------------------------------------------------------------ instruções -> RESPOSTAS.md
def registra_instrucao(instrucao, texto, quando):
    """Põe a decisão no topo da seção de instruções do RESPOSTAS.md (cria a seção antes de '## Rodadas')."""
    linha = f"- {quando:%Y-%m-%d %H:%M} [pendente] {instrucao.strip()} (ele escreveu: \"{texto.strip()[:300]}\")"
    md = le_txt(RESP_MD, 10_000_000)
    if not md:
        raise OSError("RESPOSTAS.md vazio ou ilegível")
    bloco = f"{EXPLICA}\n\n"
    if SECAO in md and bloco in md.split(SECAO, 1)[1]:
        ini = md.index(SECAO)
        pos = md.index(bloco, ini) + len(bloco)
        md = md[:pos] + linha + "\n" + md[pos:]
    elif SECAO in md:                             # alguém mexeu no texto explicativo: entra logo abaixo do título
        pos = md.index(SECAO) + len(SECAO)
        md = md[:pos] + "\n\n" + linha + md[pos:]
    else:
        novo = f"{SECAO}\n\n{bloco}{linha}\n\n"
        md = md.replace("## Rodadas", novo + "## Rodadas", 1) if "## Rodadas" in md else md + "\n" + novo
    tmp = RESP_MD + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(md)
    os.replace(tmp, RESP_MD)                      # troca atômica: a rodada nunca lê o arquivo pela metade


# ------------------------------------------------------------------ IA (Claude CLI)
def claude_exe():
    """O claude.exe nativo (o claude.cmd do npm quebraria as aspas do JSON ao passar pelo cmd)."""
    nativo = os.path.join(os.environ.get("APPDATA", ""), "npm", "node_modules", "@anthropic-ai", "claude-code",
                          "bin", "claude.exe")
    return nativo if os.path.exists(nativo) else shutil.which("claude")


def contexto(texto, citada):
    agora = datetime.now()
    roteiros = ""
    for nome in sorted(os.listdir(AQUI)):
        if nome.endswith("-ROTEIRO.md"):
            roteiros += f"\n### {nome}\n{le_txt(os.path.join(AQUI, nome), 8_000)}\n"
    enviadas = T.le(T.ENVIADAS, [])[-5:]
    conversa = [x for x in T.le(T.ENTRADA, []) if x.get("resposta")][-6:]
    partes = [f"Agora: {agora:%d/%m/%Y %H:%M} ({['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'][agora.weekday()]})",
              f"Fatos de agora:\n{status()}",
              f"PLAYBOOK.md (regras da prospecção):\n{le_txt(PLAYBOOK, 30_000)}",
              f"RESPOSTAS.md (registro de rodadas e respostas, mais recente no topo):\n{le_txt(RESP_MD, 40_000)}"]
    if roteiros:
        partes.append(f"Roteiros de fechamento:{roteiros}")
    if enviadas:
        partes.append("Últimas mensagens que a prospecção mandou para ele no Telegram:\n" + "\n---\n".join(
            f"[{m.get('quando', '')[5:16].replace('T', ' ')}] {m.get('texto', '')[:800]}" for m in enviadas))
    if conversa:
        partes.append("Conversa recente com ele aqui no bot:\n" + "\n".join(
            f"[{x.get('quando', '')[5:16].replace('T', ' ')}] João: {x['texto'][:400]}\nVocê: {x['resposta'][:400]}"
            for x in conversa))
    if citada:
        partes.append(f"Ele respondeu citando esta mensagem:\n{citada[:1500]}")
    partes.append(f"Mensagem dele agora: {texto[:2000]}")
    return "\n\n".join(partes)


def ia(texto, citada):
    """Claude CLI (assinatura do João, sem chave de API) com saída em JSON. Devolve (resposta, instrucao) ou None."""
    exe = claude_exe()
    if not exe:
        log("IA: claude.exe não encontrado")
        return None
    cmd = [exe, "-p", "--model", MODELO, "--effort", "low", "--no-session-persistence",
           "--tools", "", "--strict-mcp-config", "--setting-sources", "",   # sem ferramentas, MCP nem hooks: só texto
           "--system-prompt", SISTEMA, "--json-schema", json.dumps(SCHEMA), "--output-format", "json"]
    ini = time.time()
    try:
        r = subprocess.run(cmd, input=contexto(texto, citada).encode("utf-8"), capture_output=True, timeout=120,
                           creationflags=SEM_JANELA, cwd=AQUI)
        d = json.loads(r.stdout.decode("utf-8", errors="replace") or "{}")
        if d.get("is_error") or not (d.get("structured_output") or d.get("result")):
            log(f"IA: erro (rc {r.returncode}): {(d.get('result') or r.stderr.decode('utf-8', errors='replace'))[:200]}")
            return None
        so = d.get("structured_output") or json.loads(d["result"])
        log(f"IA: {time.time() - ini:.1f}s, US$ {d.get('total_cost_usd', 0):.4f}")
        return so.get("resposta", "").strip(), so.get("instrucao", "").strip()
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
        log(f"IA: falhou ({type(e).__name__}: {str(e)[:150]})")
        return None


# ------------------------------------------------------------------ mensagem -> resposta
def comando(texto):
    """Resposta fixa (sem IA) para status/ajuda; None se for texto livre."""
    t = norm(texto)
    if t in ("status", "estado", "resumo", "st") or texto.startswith("/status"):
        return status()
    if t in ("ajuda", "help", "comandos", "start", "menu") or texto.startswith(("/ajuda", "/help", "/start")):
        return AJUDA
    return None


def entende(texto, citada, quando, simula=False):
    """Devolve (resposta, instrucao). Comandos fixos primeiro; o resto vai para a IA."""
    fixo = comando(texto)
    if fixo is not None:
        return fixo, ""
    res = ia(texto, citada)
    if res is None:
        return (f"Não consegui pensar agora (a IA falhou). Sua mensagem ficou guardada e a rodada de "
                f"{proxima_rodada(datetime.now())} lê. Comandos que sempre funcionam: status, ajuda."), ""
    resp, instr = res
    if instr and not simula:
        try:
            registra_instrucao(instr, texto, quando)
            log(f"instrução registrada: {instr[:120]}")
        except OSError as e:
            log(f"instrução NÃO registrada no RESPOSTAS.md ({type(e).__name__}); fica só na entrada")
            resp += "\n\n(Não consegui gravar no RESPOSTAS.md, mas a rodada lê sua mensagem mesmo assim.)"
    return resp or "Anotado.", instr


def digitando(cid, parar):
    """Mostra 'digitando...' enquanto a IA pensa (o aviso do Telegram dura ~5 s)."""
    while not parar.is_set():
        try:
            T.tg("sendChatAction", espera=10, chat_id=cid, action="typing")
        except T.FalhaTelegram:
            pass
        parar.wait(4.5)


def trata(u, est):
    m = u.get("message") or {}
    cid = str((m.get("chat") or {}).get("id", ""))
    texto = (m.get("text") or "").strip()
    if not est.get("chat") and texto.startswith("/start"):
        est["chat"] = cid                         # só o 1º /start vale (igual ao telegram.py)
        T.tg("sendMessage", chat_id=cid, text="Pronto. A prospecção de sites vai falar com você por aqui.\n\n" + AJUDA)
        log("chat do João definido pelo /start")
        return
    if not cid or cid != est.get("chat"):
        log("mensagem de outro chat ignorada")
        return
    if not texto:
        T.tg("sendMessage", chat_id=cid, text="Por enquanto só entendo texto.", reply_to_message_id=m.get("message_id"))
        return
    quando = datetime.fromtimestamp(m.get("date", time.time()))
    citada = (m.get("reply_to_message") or {}).get("text", "")
    item = {"quando": quando.isoformat(timespec="seconds"), "texto": texto, "sobre": citada[:1000],
            "id": m.get("message_id"), "resposta": "", "instrucao": "", "lida": False}
    livre = comando(texto) is None                # status/ajuda não interessam à rodada
    if livre:
        T.entrada_guarda(item)                    # antes de responder: se cair no meio, a rodada ainda vê a mensagem
    log(f"recebida: {texto[:60]!r}")
    ini = time.time()
    parar = threading.Event()
    threading.Thread(target=digitando, args=(cid, parar), daemon=True).start()
    try:
        resp, instr = entende(texto, citada, quando)
    except Exception as e:                        # nunca deixa o João sem resposta
        log(f"erro ao responder ({type(e).__name__}: {str(e)[:150]})")
        resp, instr = "Tive um erro com essa mensagem. Ela ficou guardada para a rodada. Tente: status", ""
    finally:
        parar.set()
    T.tg("sendMessage", chat_id=cid, text=resp[:4000], reply_to_message_id=m.get("message_id"))
    log(f"respondida em {time.time() - ini:.1f}s" + (" (com instrução)" if instr else ""))
    if livre:
        T.entrada_guarda(dict(item, resposta=resp[:2000], instrucao=instr))


# ------------------------------------------------------------------ laço
def main():
    trava = T.trava()
    if not trava:
        log("outro ouvinte já está rodando: saindo")
        return 0
    log(f"ouvinte ligado (pid {os.getpid()})")
    est = T.le(T.ESTADO, {})
    falhas = 0
    while True:
        try:
            ups = T.tg("getUpdates", espera=ESCUTA_S + 20, offset=est.get("offset", 0), timeout=ESCUTA_S,
                       allowed_updates='["message"]')
            if falhas:
                log(f"Telegram de volta depois de {falhas} falha(s)")
            falhas = 0
        except T.FalhaTelegram as e:              # rede fora, PC acordando, 409, 5xx: espera e tenta de novo
            falhas += 1
            if falhas in (1, 5) or falhas % 60 == 0:
                log(f"{e} (falha {falhas}; tentando de novo)")
            time.sleep(min(60, 3 * falhas))
            continue
        except Exception as e:                    # qualquer outra coisa: não morre
            log(f"erro inesperado no getUpdates ({type(e).__name__}: {str(e)[:150]})")
            time.sleep(10)
            continue
        for u in ups:
            est["offset"] = u["update_id"] + 1
            T.grava(T.ESTADO, est)                # antes de tratar: uma mensagem que derruba o ouvinte não volta em loop
            try:
                trata(u, est)
            except Exception as e:
                log(f"erro ao tratar update ({type(e).__name__}: {str(e)[:150]})")
            T.grava(T.ESTADO, est)


if __name__ == "__main__":
    if "--simula" in sys.argv:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        txt = sys.argv[sys.argv.index("--simula") + 1]
        r, i = entende(txt, "", datetime.now(), simula=True)
        print(r + (f"\n\n[instrução que seria registrada] {i}" if i else ""))
        sys.exit(0)
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(0)
