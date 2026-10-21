"""reg.py prox  -> imprime destinatário e URL do próximo da fila ainda não enviado
reg.py ok EMAIL -> registra envio confirmado em envios.json (data/hora local)"""
import json, sys, datetime
from pathlib import Path
R = Path(__file__).parent
def load(p, d):
    try: return json.loads((R / p).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError): return d
env = load("envios.json", []); feitos = {x["to"] for x in env}
fila = load("fila.json", [])
if sys.argv[1] == "prox":
    pend = [x for x in fila if x["to"] not in feitos]
    print(len(pend), "pendentes")
    if pend: print(pend[0]["to"]); print(pend[0]["compose_url"])
else:
    x = next(f for f in fila if f["to"] == sys.argv[2].lower())
    env.append({"to": x["to"], "nome": x["nome"], "assunto": x["assunto"],
                "quando": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), "status": "enviado",
                "variante": x.get("variante", ""), "previa": x.get("previa", "")})
    (R / "envios.json").write_text(json.dumps(env, ensure_ascii=False, indent=1), encoding="utf-8")
    print("registrado", len(env))
