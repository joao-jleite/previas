"""Canal com o João pelo Telegram (20/10/2026): bot PRÓPRIO da prospecção, separado do Choppy (robô de trade).

Mesmo jeito do Choppy (Bot API direta, sem biblioteca), mas com token e chat próprios:
  setx PROSP_TG_TOKEN "123456:ABC..."   # token do bot criado no @BotFather (nunca vai para git nem chat)
  o João manda /start para o bot: o chat_id é descoberto e salvo em telegram_estado.json

  python telegram.py envia "Sertão do Cacau mandou o escopo. Qual valor passo?"
  python telegram.py respostas      # mensagens do João ainda não lidas pela rodada, em JSON (marca como lidas);
                                    # também ficam em telegram_respostas.json
Quem lê o bot é o ouvinte.py (sempre ligado, tarefa ProspBot-iniciar): responde ao João na hora e guarda cada
mensagem em telegram_entrada.json. Com o ouvinte desligado, o `respostas` lê o bot direto, como antes.
getUpdates é de um leitor só, por isso a trava (telegram_ouvinte.lock); o Choppy não é tocado.
"""
import json
import msvcrt
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime

AQUI = os.path.dirname(os.path.abspath(__file__))
ESTADO = os.path.join(AQUI, "telegram_estado.json")         # chat_id e offset do getUpdates
RESPOSTAS = os.path.join(AQUI, "telegram_respostas.json")   # tudo que o João escreveu (histórico)
ENVIADAS = os.path.join(AQUI, "telegram_enviadas.json")     # o que a prospecção mandou (histórico curto)
ENTRADA = os.path.join(AQUI, "telegram_entrada.json")       # caixa de entrada: o ouvinte grava, a rodada lê
TRAVA = os.path.join(AQUI, "telegram_ouvinte.lock")         # quem segura esta trava é o único leitor do bot
TRAVA_ENTRADA = os.path.join(AQUI, "telegram_entrada.lock")


class FalhaTelegram(Exception):
    """Rede fora, 401, 409... O ouvinte reconecta; na linha de comando vira SystemExit (a rodada registra e segue)."""


def env(nome):
    """Variável de ambiente; se o processo nasceu antes do setx, lê direto do registro do usuário."""
    v = os.environ.get(nome)
    if v:
        return v
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
            return winreg.QueryValueEx(k, nome)[0]
    except OSError:
        return None


def le(caminho, padrao):
    try:
        with open(caminho, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return padrao


def grava(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=1)


def tg(metodo, espera=20, **campos):
    token = env("PROSP_TG_TOKEN")
    if not token:
        raise FalhaTelegram("PROSP_TG_TOKEN não configurado")
    dados = urllib.parse.urlencode(campos).encode()
    try:
        with urllib.request.urlopen(f"https://api.telegram.org/bot{token}/{metodo}", dados, timeout=espera) as r:
            res = json.loads(r.read().decode())
    except Exception as e:                       # nunca põe str(e) aqui: a URL tem o token
        raise FalhaTelegram(f"Telegram falhou em {metodo}: {type(e).__name__} {getattr(e, 'code', '')}".strip())
    if not res.get("ok"):
        raise FalhaTelegram(f"Telegram recusou {metodo}: {res.get('description')}")
    return res["result"]


def trava(caminho=TRAVA, esperar=False):
    """Trava de arquivo (msvcrt): devolve o arquivo aberto, que segura a trava até ser fechado ou o processo morrer.
    esperar=False: None na hora se outro processo já tem. esperar=True: o Windows tenta por até ~10 s."""
    f = open(caminho, "a+")
    f.seek(0)                                    # trava sempre o byte 0, não o fim do arquivo
    try:
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK if esperar else msvcrt.LK_NBLCK, 1)
    except OSError:
        f.close()
        if esperar:
            raise
        return None
    return f


def entrada_altera(fn):
    """Lê telegram_entrada.json, aplica fn(lista) e grava, com trava curta (ouvinte e rodada mexem no mesmo arquivo).
    Devolve o que fn devolver."""
    t = trava(TRAVA_ENTRADA, esperar=True)
    try:
        lst = le(ENTRADA, [])
        res = fn(lst)
        lidas = [x for x in lst if x.get("lida")]
        if len(lidas) > 150:                     # guarda só as 150 lidas mais recentes; não lidas nunca saem
            velhas = {id(x) for x in lidas[:-150]}
            lst = [x for x in lst if id(x) not in velhas]
        grava(ENTRADA, lst)
        return res
    finally:
        t.close()


def entrada_guarda(item):
    """Acrescenta (ou atualiza pelo message_id) uma mensagem do João na caixa de entrada."""
    def fn(lst):
        for x in lst:
            if x.get("id") == item.get("id"):
                x.update({k: v for k, v in item.items() if k != "lida"})
                return
        lst.append(item)
    entrada_altera(fn)


def busca(est):
    """Lê as mensagens novas. Sem chat salvo, o primeiro /start define quem é o João."""
    novas = []
    ups = tg("getUpdates", espera=30, offset=est.get("offset", 0), timeout=5, allowed_updates='["message"]')
    for u in ups:
        est["offset"] = u["update_id"] + 1
        m = u.get("message") or {}
        cid = str((m.get("chat") or {}).get("id", ""))
        texto = m.get("text") or ""
        if not est.get("chat") and texto.strip().startswith("/start"):
            est["chat"] = cid                    # só o 1º /start vale; depois disso, outros chats são ignorados
            tg("sendMessage", chat_id=cid, text="Pronto. A prospecção de sites vai falar com você por aqui.")
            continue
        if cid != est.get("chat") or not texto or texto.startswith("/start"):
            continue
        citada = (m.get("reply_to_message") or {}).get("text", "")
        novas.append({"quando": datetime.fromtimestamp(m.get("date", 0)).isoformat(timespec="seconds"),
                      "texto": texto, "sobre": citada[:1000], "id": m.get("message_id")})
    grava(ESTADO, est)
    return novas


def envia(texto):
    est = le(ESTADO, {})
    if not est.get("chat"):
        busca(est)                               # talvez o /start tenha chegado e ainda não foi lido
    if not est.get("chat"):
        raise SystemExit("sem chat: o João precisa mandar /start para o bot")
    r = tg("sendMessage", chat_id=est["chat"], text=texto.strip()[:4000])
    hist = le(ENVIADAS, [])
    hist.append({"id": r["message_id"], "quando": datetime.now().isoformat(timespec="seconds"), "texto": texto.strip()})
    grava(ENVIADAS, hist[-50:])
    print(f"enviado (message_id {r['message_id']})")


def respostas():
    t = trava()
    if t:                                        # ouvinte desligado: esta rodada lê o bot, como antes do ouvinte
        print("aviso: ouvinte.py não está rodando; lendo o bot direto (religar: schtasks /run /tn ProspBot-iniciar)",
              file=sys.stderr)
        try:
            est = le(ESTADO, {})
            novas = busca(est)
        finally:
            t.close()
        for n in novas:
            entrada_guarda(dict(n, resposta="", instrucao="", lida=False))
        if novas:
            # confirma para ele que chegou; a decisão é aplicada na rodada que está lendo agora
            tg("sendMessage", chat_id=est["chat"], text="Recebido. Já estou aplicando.",
               reply_to_message_id=novas[-1]["id"])

    def pega(lst):                               # todas as não lidas (do ouvinte ou da leitura acima), marca lidas
        pend = [x for x in lst if not x.get("lida")]
        for x in lst:
            x["lida"] = True
        return [{k: v for k, v in x.items() if k != "lida"} for x in pend]
    novas = entrada_altera(pega)
    if novas:
        hist = le(RESPOSTAS, [])
        grava(RESPOSTAS, hist + novas)
    print(json.dumps(novas, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    try:
        if len(sys.argv) >= 3 and sys.argv[1] == "envia":
            envia(" ".join(sys.argv[2:]))
        elif len(sys.argv) >= 2 and sys.argv[1] == "respostas":
            respostas()
        else:
            print(__doc__)
    except FalhaTelegram as e:
        raise SystemExit(str(e))
