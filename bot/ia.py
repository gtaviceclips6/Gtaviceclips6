# GTA VICE CLIPS 6 - textos escritos por IA (opcional)
# Si existe el secreto ANTHROPIC_API_KEY en GitHub, Claude lee lo que dice el streamer y escribe
# un titulo, un gancho y un comentario gracioso de ESE clip. Si no hay clave, se usan plantillas.
import os, json, re
import requests

CLAVE = os.environ.get("ANTHROPIC_API_KEY", "")
MODELO = os.environ.get("MODELO_IA", "claude-haiku-5-5")

INSTRUCCIONES = """Eres el community manager de @gtaviceclips6, una cuenta de fans (no oficial) de GTA 6 para España
que sube clips cortos de streamers en TikTok, Instagram Reels y YouTube Shorts. Tono: colega, gracioso,
de risa, español de España, sin insultar a nadie ni inventar cosas graves sobre el streamer.
No pongas creditos ni frases tipo "todos los derechos". Responde SOLO con un JSON con estas claves:
- "titulo": titulo corto y llamativo del clip (max 45 caracteres), con el nombre del streamer si encaja
- "gancho": 2-4 palabras en mayusculas para los 2 primeros segundos del video (ej: "NO SE LO ESPERABA")
- "risa": una risa al estilo redes (ej: "JAJAJAJA 😂😂", "NO PUEDO 💀💀")
- "comentario": 1-2 frases graciosas comentando lo que pasa, como si te hubiera hecho mucha gracia
- "pregunta": pregunta corta para que la gente comente
- "hashtags": lista de 4-6 hashtags extra muy concretos de este clip (sin #gta6, ya se pone solo)"""


def textos(streamer, titulo, transcripcion):
    if not CLAVE:
        return None
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
            "x-api-key": CLAVE, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": MODELO, "max_tokens": 500, "system": INSTRUCCIONES, "messages": [{"role": "user",
                  "content": f"Streamer: {streamer}\nTitulo original del clip: {titulo}\n"
                             f"Lo que dice en el clip: {transcripcion[:1500] or '(no habla)'}"}]})
        r.raise_for_status()
        txt = "".join(b.get("text", "") for b in r.json().get("content", []))
        datos = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
        return {k: datos.get(k) for k in ("titulo", "gancho", "risa", "comentario", "pregunta", "hashtags")}
    except Exception as e:
        print("IA:", e)
        return None
