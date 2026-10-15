# GTA VICE CLIPS 6 - textos escritos por IA (opcional)
# Lee lo que dice el streamer y escribe un titulo, un gancho y un comentario gracioso de ESE clip.
#  - GEMINI_API_KEY (gratis, Google AI Studio): se usa primero. Si se acaba el cupo gratis del dia, plantillas.
#  - ANTHROPIC_API_KEY (de pago, opcional).
#  - Sin ninguna clave: plantillas.
import os, json, re, pathlib, datetime
import requests

CLAVE = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI = os.environ.get("GEMINI_API_KEY", "")
MODELOS_GEMINI = [m for m in os.environ.get("MODELO_GEMINI", "gemini-3.5-flash-lite,gemini-3.8-flash,gemini-3.6-flash,gemini-flash-latest").split(",") if m]
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


def _pedido(streamer, titulo, transcripcion):
    return (f"Streamer: {streamer}\nTitulo original del clip: {titulo}\n"
            f"Lo que dice en el clip: {transcripcion[:1500] or '(no habla)'}")


def _leer_json(txt):
    datos = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    return {k: datos.get(k) for k in ("titulo", "gancho", "risa", "comentario", "pregunta", "hashtags")}


def _estado(txt):
    """Apunta como fue la ultima llamada a la IA (para revisar si algo falla)."""
    try:
        pathlib.Path("ia_estado.txt").write_text(f"{datetime.datetime.utcnow():%Y-%m-%d %H:%M} {txt}\n", encoding="utf-8")
    except Exception:
        pass


def con_gemini(streamer, titulo, transcripcion):
    fallos = []
    for modelo in MODELOS_GEMINI:
        try:
            r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent",
                              params={"key": GEMINI}, timeout=60, json={
                                  "systemInstruction": {"parts": [{"text": INSTRUCCIONES}]},
                                  "contents": [{"role": "user", "parts": [{"text": _pedido(streamer, titulo, transcripcion)}]}],
                                  "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}})
            if r.status_code in (404, 400):        # modelo con otro nombre: probamos el siguiente
                fallos.append(f"{modelo}={r.status_code}:{r.text[:120]}"); continue
            if r.status_code == 429:               # cupo gratis agotado por hoy
                _estado(f"Gemini {modelo}: cupo gratis agotado"); return None
            r.raise_for_status()
            txt = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
            _estado(f"Gemini {modelo}: OK")
            return _leer_json(txt)
        except Exception as e:
            fallos.append(f"{modelo}: {e}")
    _estado("Gemini sin respuesta: " + " | ".join(fallos))
    return None


def textos(streamer, titulo, transcripcion):
    if GEMINI:
        t = con_gemini(streamer, titulo, transcripcion)
        if t:
            return t
    if not CLAVE:
        return None
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=60, headers={
            "x-api-key": CLAVE, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": MODELO, "max_tokens": 500, "system": INSTRUCCIONES, "messages": [{"role": "user",
                  "content": _pedido(streamer, titulo, transcripcion)}]})
        r.raise_for_status()
        txt = "".join(b.get("text", "") for b in r.json().get("content", []))
        return _leer_json(txt)
    except Exception as e:
        print("IA:", e)
        return None
