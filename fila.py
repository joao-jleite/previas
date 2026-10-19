"""Monta a fila de e-mails a partir dos leads aprovados e das prévias geradas.

Uso: python fila.py leads/aprovados.json
Saída: fila.json (to, assunto, corpo, compose_url), pulando quem já está em envios.json.
"""
import json
import re
import sys
import urllib.parse
from pathlib import Path

RAIZ = Path(__file__).parent
CONTA = 2  # índice da conta joao.jleitewrk no Gmail do Brave (mail/u/2)

CORPO = """{saudacao}

{gancho} {frase_site}

{link}

É só um rascunho, sem compromisso. Se gostarem, eu ajusto com as fotos, os textos e as cores de vocês e publico em domínio próprio.

Sou João Leite, desenvolvedor de sites aqui da Grande São Paulo. Dois trabalhos meus no ar: dermatechbrasil.com.br e dandrademoda.com.br.

Se não fizer sentido agora, é só me responder que não envio mais nada.

João Leite
joao.jleitewrk@gmail.com"""


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
        art = "do" if nome.split()[0].lower() in ("espaço", "studio", "estúdio", "centro", "consultório", "instituto", "ateliê", "buffet", "colégio", "núcleo") else "da"
        assunto = f"Fiz uma prévia do site {art} {nome}"
        corpo = CORPO.format(saudacao=l.get("saudacao") or f"Olá, equipe {art} {nome}!", gancho=l["gancho"].strip(), link=link,
                             frase_site=l.get("frase_site") or ("Como não encontrei um site próprio de vocês, montei uma prévia de como ele poderia ficar, com os serviços que vocês divulgam e o botão direto para o " + ("WhatsApp:" if len(re.sub(r"\D", "", l.get("whatsapp_ou_telefone") or "")) in (11, 13) else "contato:")))
        q = urllib.parse.urlencode({"view": "cm", "fs": "1", "to": to, "su": assunto, "body": corpo},
                                   quote_via=urllib.parse.quote)
        fila.append({"to": to, "nome": l["nome"], "assunto": assunto, "corpo": corpo,
                     "compose_url": f"https://mail.google.com/mail/u/{CONTA}/?{q}"})
    (RAIZ / "fila.json").write_text(json.dumps(fila, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(fila)} e-mails na fila")


if __name__ == "__main__":
    main(sys.argv[1])
