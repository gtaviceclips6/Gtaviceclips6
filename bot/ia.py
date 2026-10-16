# GTA VICE CLIPS 6 - textos escritos por IA (opcional)
# Lee lo que dice el streamer y escribe un titulo, un gancho y un comentario gracioso de ESE clip.
#  - GEMINI_API_KEY (gratis, Google AI Studio): se usa primero. Si se acaba el cupo gratis del dia, plantillas.
#  - ANTHROPIC_API_KEY (de pago, opcional).
#  - Sin ninguna clave: plantillas.
import os, json, re, pathlib, datetime
import requests
from config import MARCA

CLAVE = os.environ.get("ANTHROPIC_API_KEY", "")
GEMINI = os.environ.get("GEMINI_API_KEY", "")
MODELOS_GEMINI = [m for m in os.environ.get("MODELO_GEMINI", "gemini-3.5-flash-lite,gemini-3.8-flash,gemini-3.6-flash,gemini-flash-latest").split(",") if m]
MODELO = os.environ.get("MODELO_IA", "claude-haiku-5-5")

INSTRUCCIONES = "Eres el editor jefe de " + MARCA["handle"] + ", " + MARCA["descripcion_ia"] + """, que sube
clips cortos de streamers a TikTok, Instagram Reels y YouTube Shorts. Te paso 4 fotogramas del clip y lo que se dice.

1) JUZGA el clip con MUCHA exigencia. Solo vale si es una de estas dos cosas:
   - "gracioso": un momento que hace reir de verdad SIN necesitar contexto (reaccion exagerada, fail, broma buena,
     situacion absurda, susto, pique). Que el streamer simplemente hable o comente NO es gracioso.
   - "escena_guapa": una escena del juego espectacular a la vista (paisaje, atardecer, persecucion, explosion,
     momento cinematografico, graficos impresionantes).
   - "nada": todo lo demas (menus, pantallas de carga, conducir sin mas, charla normal, no pasa nada, hace falta contexto).
   "nota" de 1 a 10 = probabilidad de que se haga viral en TikTok/Reels en España (el clip puede ser de GTA o de cualquier otra cosa). Se duro: la mayoria de clips son 3-6.
2) Si vale, escribe los textos. Tono: colega y de risa (si es "gracioso") o de flipar (si es "escena_guapa"),
   español de España, sin insultar a nadie ni inventar cosas graves sobre el streamer.
   PROHIBIDO: bromas o palabras sobre orientacion sexual, genero, raza, religion, fisico, drogas o sexo, y tacos fuertes
   (las redes castigan esos videos). El humor va sobre la situacion, la reaccion o el juego. Nada de creditos.

Responde SOLO con un JSON con estas claves:
- "tipo": "gracioso" | "escena_guapa" | "nada"
- "nota": numero de 1 a 10
- "motivo": por que (max 15 palabras)
- "titulo": titulo corto y llamativo (max 45 caracteres), con el nombre del streamer si encaja
- "gancho": 2-4 palabras en mayusculas para los 2 primeros segundos (ej: "NO SE LO ESPERABA", "MIRA ESTO")
- "risa": arranque al estilo redes (ej: "JAJAJAJA 😂😂" si es gracioso, "QUÉ PASADA 😍🔥" si es escena guapa)
- "comentario": 1-2 frases comentando lo que pasa, como si te hubiera flipado o hecho mucha gracia
- "pregunta": pregunta corta para que la gente comente
- "hashtags": lista de 4-6 hashtags extra muy concretos de este clip (sin #gta6, ya se pone solo)"""


def _pedido(streamer, titulo, transcripcion):
    return (f"Streamer: {streamer}\nTitulo original del clip: {titulo}\n"
            f"Lo que dice en el clip: {transcripcion[:1500] or '(no habla)'}")


CLAVES_JSON = ("tipo", "nota", "motivo", "titulo", "gancho", "risa", "comentario", "pregunta", "hashtags")


def _leer_json(txt):
    datos = json.loads(re.search(r"\{.*\}", txt, re.S).group(0))
    t = {k: datos.get(k) for k in CLAVES_JSON}
    try:
        t["nota"] = float(t.get("nota") or 0)
    except (TypeError, ValueError):
        t["nota"] = 0
    return t


def _estado(txt):
    """Apunta como fue la ultima llamada a la IA (para revisar si algo falla)."""
    try:
        pathlib.Path("ia_estado.txt").write_text(f"{datetime.datetime.utcnow():%Y-%m-%d %H:%M} {txt}\n", encoding="utf-8")
    except Exception:
        pass


def gemini_post(modelo, cuerpo):
    """Llama a Gemini. Primero con la clave en la cabecera; si Google no la acepta asi, en la direccion.
    Nunca devuelve ni guarda la clave en los mensajes de error."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"
    import time
    for espera in (0, 6, 20):                       # Google saturado (503): esperamos un poco y reintentamos
        time.sleep(espera)
        r = requests.post(url, headers={"x-goog-api-key": GEMINI}, timeout=60, json=cuerpo)
        if r.status_code < 500:
            break
    if r.status_code in (401, 403):
        r = requests.post(url, params={"key": GEMINI}, timeout=60, json=cuerpo)
    return r


def _tapar(txt):
    return str(txt).replace(GEMINI, "***") if GEMINI else str(txt)


def con_gemini(streamer, titulo, transcripcion, fotos=()):
    fallos = []
    for modelo in MODELOS_GEMINI:
        try:
            r = gemini_post(modelo, {
                                  "systemInstruction": {"parts": [{"text": INSTRUCCIONES}]},
                                  "contents": [{"role": "user", "parts": [{"text": _pedido(streamer, titulo, transcripcion)}] + [
                                      {"inline_data": {"mime_type": "image/jpeg", "data": f}} for f in fotos]}],
                                  "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9}})
            if r.status_code in (401, 403):
                fallos.append(f"{modelo}={r.status_code} (clave no válida: hay que poner una nueva en GEMINI_API_KEY)"); break
            if r.status_code in (404, 400) or r.status_code >= 500:   # otro nombre o Google saturado: probamos el siguiente
                fallos.append(f"{modelo}={r.status_code}:{r.text[:120]}"); continue
            if r.status_code == 429:               # cupo gratis agotado por hoy
                _estado(f"Gemini {modelo}: cupo gratis agotado"); return None
            r.raise_for_status()
            txt = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
            _estado(f"Gemini {modelo}: OK")
            return _leer_json(txt)
        except Exception as e:
            fallos.append(f"{modelo}: {_tapar(e)}")
    _estado("Gemini sin respuesta: " + " | ".join(fallos))
    return None


def textos(streamer, titulo, transcripcion, fotos=()):
    """Juzga el clip y escribe sus textos. Devuelve dict (con tipo y nota) o None si no hay IA disponible."""
    if GEMINI:
        t = con_gemini(streamer, titulo, transcripcion, fotos)
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
