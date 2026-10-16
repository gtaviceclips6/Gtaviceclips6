# GTA VICE CLIPS 6 - todo lo de Telegram: mensajes, videos con botones y lectura de los botones pulsados
import os, re, json, pathlib, datetime
import requests

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
CHAT_FILE = pathlib.Path("telegram_chat.txt")      # se guarda solo la primera vez
APROBADOS = pathlib.Path("aprobados.jsonl")        # clips que has marcado con ✅
DESCARTADOS = pathlib.Path("descartados.txt")      # clips que has marcado con ❌
MENSAJES = []                                       # textos que el dueño escribe al bot (enlaces y comandos)


def tg(metodo, **kw):
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/{metodo}", timeout=300, **kw)
    if not r.ok:
        print("Telegram:", r.text[:300])
    return r


def chat_id():
    global _CHAT
    if not _CHAT and CHAT_FILE.exists():
        _CHAT = CHAT_FILE.read_text().strip()
    if not _CHAT:
        upd = tg("getUpdates").json().get("result", [])
        ids = [u["message"]["chat"]["id"] for u in upd if "message" in u]
        ids += [u["callback_query"]["message"]["chat"]["id"] for u in upd if "callback_query" in u]
        _CHAT = str(ids[-1]) if ids else ""
    if _CHAT and not CHAT_FILE.exists():
        CHAT_FILE.write_text(_CHAT)
    return _CHAT


def sin_claves(txt):
    """Tapa cualquier clave o token antes de guardar un error (el repo es publico)."""
    txt = str(txt)
    for k in ("GEMINI_API_KEY", "TELEGRAM_BOT_TOKEN", "TWITCH_CLIENT_SECRET", "ANTHROPIC_API_KEY", "TWITCH_CLIENT_ID"):
        v = os.environ.get(k)
        if v and len(v) > 6:
            txt = txt.replace(v, "***")
    return re.sub(r"(key=|bot)[A-Za-z0-9_.:-]{20,}", r"\1***", txt)


def silencio():
    """De 0:00 a 9:00 (hora de Madrid) y en los simulacros, los avisos llegan sin sonar."""
    if os.environ.get("SIMULACRO") == "true":
        return True
    try:
        from zoneinfo import ZoneInfo
        h = datetime.datetime.now(ZoneInfo("Europe/Madrid")).hour
    except Exception:
        h = (datetime.datetime.utcnow().hour + 2) % 24
    return h < 9


def mensaje(texto):
    return tg("sendMessage", data={"chat_id": chat_id(), "text": texto[:4000],
                                   "disable_notification": str(silencio()).lower()})


def enviar_video(ruta, texto, clip_id):
    botones = {"inline_keyboard": [[{"text": "✅ Publicar", "callback_data": f"ok:{clip_id}"},
                                    {"text": "❌ Descartar", "callback_data": f"no:{clip_id}"}]]}
    with open(ruta, "rb") as f:
        r = tg("sendVideo", data={"chat_id": chat_id(), "caption": texto[:1024], "supports_streaming": "true",
                                  "disable_notification": str(silencio()).lower(),
                                  "reply_markup": json.dumps(botones)}, files={"video": f})
    if not r.ok:
        raise RuntimeError("Telegram no aceptó el vídeo: " + r.text[:150])


def aprobados():
    if not APROBADOS.exists():
        return []
    return [json.loads(l) for l in APROBADOS.read_text(encoding="utf-8").splitlines() if l.strip()]


def procesar_botones(upd=None):
    """Lee los botones pulsados y los apunta. Devuelve (aprobados, descartados) nuevos.
    Si se le pasan las actualizaciones (modo escucha), no vuelve a pedirlas ni las marca como leidas."""
    if not TOKEN:
        return 0, 0
    chat_id()   # guarda el chat antes de vaciar la cola
    propio = upd is None
    if propio:
        upd = tg("getUpdates", data={"allowed_updates": json.dumps(["message", "callback_query"])}).json().get("result", [])
    ya = {a["id"] for a in aprobados()}
    no = set(DESCARTADOS.read_text().split()) if DESCARTADOS.exists() else set()
    n_ok = n_no = 0
    for u in upd:
        m = u.get("message") or {}
        if m.get("text") and str(m.get("chat", {}).get("id")) == str(chat_id()):   # solo el dueño
            MENSAJES.append(m["text"])
        cq = u.get("callback_query")
        if not cq or ":" not in (cq.get("data") or ""):
            continue
        accion, cid = cq["data"].split(":", 1)
        msg = cq.get("message", {})
        if accion == "ok" and cid not in ya:
            with open(APROBADOS, "a", encoding="utf-8") as f:
                f.write(json.dumps({"id": cid, "fecha": datetime.datetime.utcnow().isoformat(timespec="minutes"),
                                    "publicado": False}) + "\n")
            ya.add(cid); n_ok += 1
            etiqueta = "✅ Aprobado: sale en unos minutos en las 3 redes"
        elif accion == "no" and cid not in no:
            with open(DESCARTADOS, "a") as f:
                f.write(cid + "\n")
            no.add(cid); n_no += 1
            etiqueta = "❌ Descartado"
        else:
            continue
        tg("answerCallbackQuery", data={"callback_query_id": cq["id"], "text": etiqueta})
        if msg:
            tg("editMessageReplyMarkup", data={"chat_id": msg["chat"]["id"], "message_id": msg["message_id"],
                                                "reply_markup": json.dumps({"inline_keyboard": [[
                                                    {"text": etiqueta, "callback_data": "x:0"}]]})})
    if upd and propio:   # marca todo como leido
        tg("getUpdates", data={"offset": upd[-1]["update_id"] + 1})
    return n_ok, n_no
