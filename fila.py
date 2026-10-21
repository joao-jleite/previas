"""Monta a fila de e-mails a partir dos leads aprovados e das prévias geradas.

Uso: python fila.py leads/aprovados.json
Saída: fila.json (to, assunto, corpo, compose_url), pulando quem já está em envios.json.
"""
import json
import re
import sys
import urllib.parse
import zlib
from pathlib import Path

RAIZ = Path(__file__).parent
CONTA = 2  # índice da conta joao.jleitewrk no Gmail do Brave (mail/u/2)

CORPO = """{saudacao}

{gancho} {frase_site}

{link}

Trata-se apenas de um rascunho, sem compromisso. Caso a ideia seja do interesse de vocês, adapto a página com as fotos, os textos e a identidade visual de vocês e a publico em domínio próprio.

Sou desenvolvedor de sites na Grande São Paulo. Entre os trabalhos que tenho publicados estão dermatechbrasil.com.br e dandrademoda.com.br.

Caso não seja do interesse no momento, basta responder a este e-mail e não enviarei novas mensagens.

Atenciosamente,

João Leite
Desenvolvimento de Sites | Grande São Paulo
WhatsApp: (11) 96155-1602
E-mail: joao.jleitewrk@gmail.com"""


def periodo() -> str:
    import datetime
    h = datetime.datetime.now().hour
    return "Bom dia" if h < 12 else ("Boa tarde" if h < 18 else "Boa noite")


def carregar(p: Path, padrao):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return padrao


def main(arq):
    leads = carregar(Path(arq), [])
    previas = carregar(RAIZ / "previas.json", {})
    enviados = {x["to"].lower() for x in carregar(RAIZ / "envios.json", [])}
    fila = []
    for l in leads:
        to = (l.get("email") or "").strip().lower()
        link = previas.get(to)
        # Só entra quem tem prévia publicada, gancho revisado e não recebeu nada ainda
        if not to or not link or to in enviados or not l.get("gancho"):
            continue
        nome = l.get("nome_email") or l["nome"]
        # Artigo pelo primeiro termo do nome (Espaço/Studio/Centro... são masculinos)
        art = l_art if (l_art := l.get("artigo")) in ("do", "da") else "do" if nome.split()[0].lower() in ("espaço", "studio", "estúdio", "centro", "consultório", "instituto", "ateliê", "buffet", "colégio", "núcleo") else "da"
        # Teste A/B do assunto (21/10): metade fixa por e-mail; a variante vai para envios.json via reg.py
        variante = "AB"[zlib.crc32(to.encode()) % 2]
        primeiro = re.match(r"Olá,\s+([A-ZÀ-Ú][\wÀ-ú]+)", l.get("saudacao") or "")
        if variante == "A":
            assunto = f"Fiz uma prévia do site {art} {nome}"
        elif primeiro:
            assunto = f"{primeiro.group(1)}, montei uma prévia do seu site"
        else:
            assunto = f"Prévia do novo site {art} {nome}"
        corpo = CORPO.format(saudacao=l.get("saudacao") or f"Olá, equipe {art} {nome}.", gancho=l["gancho"].strip(), link=link,
                             frase_site=l.get("frase_site") or ("Como não encontrei um site próprio de vocês, montei uma prévia de como ele poderia ficar, com os serviços que vocês divulgam e o botão direto para o " + ("WhatsApp:" if len(re.sub(r"\D", "", l.get("whatsapp_ou_telefone") or "")) in (11, 13) else "contato:")))
        if (l.get("uf") or "SP").upper() != "SP":
            # Lead de fora de SP: "Grande São Paulo" soaria distante; o trabalho é remoto
            corpo = corpo.replace("Sou desenvolvedor de sites na Grande São Paulo.", "Sou desenvolvedor de sites em São Paulo e atendo clientes de todo o Brasil, com todo o processo feito a distância.")
            corpo = corpo.replace("Desenvolvimento de Sites | Grande São Paulo", "Desenvolvimento de Sites | Atendimento em todo o Brasil")
        if l.get("saudacao"):
            # Profissional autônomo: trata por "você" no corpo inteiro
            for a, b in (("site próprio de vocês", "site próprio"), ("serviços que vocês divulgam", "serviços que você divulga"),
                         ("com o que vocês divulgam", "com o que você divulga"), ("do interesse de vocês", "do seu interesse"),
                         ("com as fotos, os textos e a identidade visual de vocês", "com as suas fotos, os seus textos e a sua identidade visual")):
                corpo = corpo.replace(a, b)
        q = urllib.parse.urlencode({"view": "cm", "fs": "1", "to": to, "su": assunto, "body": corpo},
                                   quote_via=urllib.parse.quote)
        fila.append({"to": to, "nome": l["nome"], "assunto": assunto, "corpo": corpo, "variante": variante,
                     "previa": link.rstrip("/").rsplit("/", 1)[-1],
                     "compose_url": f"https://mail.google.com/mail/u/{CONTA}/?{q}"})
    (RAIZ / "fila.json").write_text(json.dumps(fila, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(fila)} e-mails na fila")


if __name__ == "__main__":
    main(sys.argv[1])
