# GTA VICE CLIPS 6 - el bot de Telegram te entiende (se ejecuta cada 5 minutos)
#  - Apunta los botones ✅/❌.
#  - Si le mandas un ENLACE (X/Twitter, Twitch, Kick, TikTok, Instagram...), te devuelve el reel montado
#    (si es un clip corto) o los mejores momentos (si es un video largo).
#  - Comandos: /estado  /virales  /ayuda
import os, re, json, datetime, pathlib
import requests
import tg

REPO = os.environ.get("GITHUB_REPOSITORY", "gtaviceclips6/Gtaviceclips6")
GH = os.environ.get("GITHUB_TOKEN", "")
ENLACE = re.compile(r"https?://\S+", re.I)

AYUDA = """🤖 Así me usas:

📎 Mándame un enlace (X/Twitter, Twitch, Kick, TikTok, Instagram…)
   • Clip corto → te lo devuelvo montado con subtítulos y texto.
   • Vídeo largo → saco las mejores escenas.
   Puedes añadir un texto después del enlace para darme contexto.

✅ / ❌ en cada vídeo → lo aprobado se publica solo en las 3 redes.

/estado → cómo va el día
/virales → busco ahora mismo lo que está explotando
/ayuda → este mensaje

⚠️ Los enlaces de YouTube no funcionan (YouTube bloquea las descargas). Usa el de X."""


def lanzar(workflow, **inputs):
    r = requests.post(f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow}/dispatches", timeout=30,
                      headers={"Authorization": f"Bearer {GH}", "Accept": "application/vnd.github+json"},
                      json={"ref": "main", "inputs": inputs})
    if not r.ok:
        raise RuntimeError(f"GitHub {r.status_code}: {r.text[:150]}")


def estado():
    hoy = datetime.datetime.utcnow().date().isoformat()
    lista = pathlib.Path("shorts/lista.jsonl")
    shorts = [json.loads(l) for l in lista.read_text(encoding="utf-8").splitlines()] if lista.exists() else []
    de_hoy = [d for d in shorts if (d.get("fecha") or "").startswith(hoy)]
    aprob = tg.aprobados()
    pend = [a for a in aprob if not a.get("publicado")]
    publ_hoy = [a for a in aprob if a.get("publicado") and (a.get("fecha") or "").startswith(hoy)]
    ia_txt = pathlib.Path("ia_estado.txt").read_text(encoding="utf-8").strip()[:90] if pathlib.Path("ia_estado.txt").exists() else "?"
    ia_ok = "✅ funciona" if "OK" in ia_txt else ("⏳ cupo gratis agotado hasta mañana" if "cupo" in ia_txt else "⚠️ " + ia_txt[17:])
    return (f"📊 Hoy\n\n🎬 Vídeos que te he mandado: {len(de_hoy)}\n✅ Aprobados pendientes de salir: {len(pend)}\n"
            f"📤 Aprobados hoy y ya programados: {len(publ_hoy)}\n🧠 IA: {ia_ok}\n\n"
            "Lo aprobado sale solo en las 3 redes en menos de 1 hora.")


def atender(texto):
    t = texto.strip()
    if t.lower().startswith(("/start", "/ayuda", "/help")):
        return tg.mensaje(AYUDA)
    if t.lower().startswith("/estado"):
        return tg.mensaje(estado())
    if t.lower().startswith("/virales"):
        lanzar("virales.yml")
        return tg.mensaje("🔥 Buscando lo que está explotando ahora mismo… En 10-15 min te llega lo bueno.")
    m = ENLACE.search(t)
    if m:
        url = m.group(0).rstrip(").,")
        if re.search(r"youtu\.?be", url):
            return tg.mensaje("⚠️ YouTube no deja descargar desde el bot. Busca el mismo vídeo en X (Twitter) y mándame ese enlace.")
        contexto = (t.replace(m.group(0), "").strip() or "Vídeo que me manda el dueño de la cuenta (puede ser de cualquier tema)")[:300]
        lanzar("escenas.yml", url=url, reels="4", contexto=contexto)
        return tg.mensaje("📩 ¡Recibido! Lo estoy montando. En 5-15 min te llega aquí con los botones ✅/❌.")
    tg.mensaje("🤔 No te he entendido. Mándame un enlace o escribe /ayuda.")


MENU = [{"command": "estado", "description": "Cómo va el día"},
        {"command": "virales", "description": "Buscar ya lo que está explotando"},
        {"command": "ayuda", "description": "Qué puedo hacer"}]


def main():
    if datetime.datetime.utcnow().minute < 5:          # una vez por hora basta para tener el menú "/" al día
        tg.tg("setMyCommands", data={"commands": json.dumps(MENU)})
    ok, no = tg.procesar_botones()
    print("Botones:", ok, no, "· mensajes:", len(tg.MENSAJES))
    for texto in tg.MENSAJES:
        try:
            atender(texto)
        except Exception as e:
            tg.mensaje(f"⚠️ No pude con eso: {tg.sin_claves(e)[:200]}")


if __name__ == "__main__":
    main()
