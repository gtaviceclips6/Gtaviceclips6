# GTA VICE CLIPS 6 - el bot de Telegram con MENÚ (se ejecuta cada 5 minutos)
#  - Apunta los botones ✅/❌ de cada vídeo.
#  - Menú fijo abajo con botones para lanzar todo a mano, ver el estado y cambiar ajustes.
#  - Si le mandas un ENLACE (X/Twitter, Twitch, Kick, TikTok, Instagram...), te devuelve el reel montado.
import os, re, json, time, datetime, pathlib
import requests
import tg, ajustes

REPO = os.environ.get("GITHUB_REPOSITORY", "gtaviceclips6/Gtaviceclips6")
GH = os.environ.get("GITHUB_TOKEN", "")
ENLACE = re.compile(r"https?://\S+", re.I)
LISTA = pathlib.Path("shorts/lista.jsonl")

# ---------- botones del menú (texto exacto que manda Telegram al pulsarlos) ----------
B_VIRALES, B_GTA = "🔥 Virales ya", "🎮 Clips GTA 6"
B_NOTICIAS, B_TENDENCIAS = "📰 Noticias GTA 6", "🌍 Tendencias España"
B_ENLACE, B_IDEAS = "🎬 Reel de un enlace", "💡 Ideas para hoy"
B_ESTADO, B_PENDIENTES = "📊 Estado", "📋 Pendientes"
B_TOP5, B_SIMULACRO = "🏆 TOP 5 semana", "🧪 Simulacro"
B_AJUSTES, B_AYUDA = "⚙️ Ajustes", "❓ Ayuda"
B_PAUSA, B_SEGUIR = "⏸ Pausar bot", "▶️ Reanudar bot"
B_NOTA = "🎯 Exigencia IA"
B_TOG_VIR, B_TOG_TEN, B_TOG_NOT = "🔥 Virales on/off", "🌍 Tendencias on/off", "📰 Noticias on/off"
B_VOLVER = "🔙 Menú principal"


def teclado(filas):
    return json.dumps({"keyboard": [[{"text": t} for t in f] for f in filas], "resize_keyboard": True,
                       "is_persistent": True, "input_field_placeholder": "Pega un enlace o elige una opción"})


def menu_principal():
    pausa = ajustes.leer()["pausa"]
    return teclado([[B_VIRALES, B_GTA], [B_NOTICIAS, B_TENDENCIAS], [B_ENLACE, B_IDEAS],
                    [B_ESTADO, B_PENDIENTES], [B_TOP5, B_SIMULACRO],
                    [B_SEGUIR if pausa else B_PAUSA, B_AJUSTES], [B_AYUDA]])


def menu_ajustes():
    return teclado([[B_NOTA], [B_TOG_VIR, B_TOG_TEN], [B_TOG_NOT], [B_VOLVER]])


def enviar(texto, teclado_=None):
    tg.tg("sendMessage", data={"chat_id": tg.chat_id(), "text": texto[:4000],
                               "reply_markup": teclado_ or menu_principal()})


class YaEnMarcha(Exception):
    pass


def lanzar(workflow, **inputs):
    """Lanza un trabajo en GitHub. Si ya lo pediste hace menos de 10 min, no lo repite."""
    clave = workflow + json.dumps(inputs, sort_keys=True)
    reg = pathlib.Path("lanzados.json")
    try:
        hechos = json.loads(reg.read_text())
    except Exception:
        hechos = {}
    hace = time.time() - hechos.get(clave, 0)
    if hace < 600:
        raise YaEnMarcha(int(hace // 60))
    hechos[clave] = time.time()
    reg.write_text(json.dumps(hechos))
    r = requests.post(f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow}/dispatches", timeout=30,
                      headers={"Authorization": f"Bearer {GH}", "Accept": "application/vnd.github+json"},
                      json={"ref": "main", "inputs": inputs})
    if not r.ok:
        raise RuntimeError(f"GitHub {r.status_code}: {r.text[:150]}")


def shorts():
    return [json.loads(l) for l in LISTA.read_text(encoding="utf-8").splitlines()] if LISTA.exists() else []


AYUDA = """🤖 GTA VICE CLIPS 6 · Menú

🔥 Virales ya → busco AHORA los clips que están explotando en Twitch (cualquier tema).
🎮 Clips GTA 6 → busco clips de GTA 6 de tus streamers y de todo Twitch.
📰 Noticias GTA 6 → miro si hay noticia oficial y te monto el vídeo «ÚLTIMA HORA».
🌍 Tendencias España → lo más buscado ahora en España → vídeo «VIRAL HOY».
🎬 Reel de un enlace → pega un enlace (X, Twitch, Kick, TikTok…) y te devuelvo el reel.
💡 Ideas para hoy → la IA te propone vídeos para petarlo hoy.
📊 Estado → cómo va el día · 📋 Pendientes → lo aprobado que va a salir.
🏆 TOP 5 semana → recopilación con lo mejor de la semana.
🧪 Simulacro → prueba completa con GTA 5 (no se publica nada).
⏸ Pausar → paro todo lo automático (lo que pidas a mano sigue funcionando).
⚙️ Ajustes → exigencia de la IA y qué buscar.

✅ / ❌ en cada vídeo → lo aprobado sale solo en las 3 redes en menos de 1 hora.
⚡ Respondo al momento. Las búsquedas tardan 5-15 min en terminar.
⚠️ Enlaces de YouTube no funcionan (bloquea descargas): usa el de X."""


def estado():
    hoy = datetime.datetime.utcnow().date().isoformat()
    de_hoy = [d for d in shorts() if (d.get("fecha") or "").startswith(hoy)]
    aprob = tg.aprobados()
    pend = [a for a in aprob if not a.get("publicado")]
    ia_p = pathlib.Path("ia_estado.txt")
    ia_txt = ia_p.read_text(encoding="utf-8").strip() if ia_p.exists() else ""
    ia_ok = "✅ funciona" if "OK" in ia_txt else ("⏳ cupo gratis agotado hasta mañana" if "cupo" in ia_txt
                                               else "⚠️ con problemas (" + ia_txt[17:70] + "…)")
    a = ajustes.leer()
    return (f"📊 Hoy\n\n🎬 Vídeos que te he mandado: {len(de_hoy)}\n✅ Aprobados pendientes de salir: {len(pend)}\n"
            f"🧠 IA: {ia_ok}\n\n⚙️ Bot: {'⏸ EN PAUSA' if a['pausa'] else '▶️ funcionando'} · exigencia {a['nota_minima'] or 7}/10\n"
            f"🔥 Virales: {'sí' if a['virales'] else 'no'} · 🌍 Tendencias: {'sí' if a['tendencias'] else 'no'} · "
            f"📰 Noticias: {'sí' if a['noticias_gta'] else 'no'}")


def pendientes():
    por_id = {d.get("id"): d for d in shorts()}
    pend = [a for a in tg.aprobados() if not a.get("publicado")]
    if not pend:
        return "📋 No hay nada aprobado pendiente. Todo lo que aprobaste ya está programado 👌"
    return "📋 Aprobados que van a salir (en menos de 1 hora):\n\n" + "\n".join(
        f"• {por_id.get(a['id'], {}).get('titulo', a['id'])}" for a in pend[:15])


def ideas():
    import ia
    if not ia.GEMINI:
        return "💡 Sin la IA no puedo darte ideas ahora."
    hoy = datetime.date.today()
    faltan = (datetime.date(2026, 11, 19) - hoy).days
    pedido = (f"Hoy es {hoy:%d/%m/%Y}; faltan {faltan} días para GTA 6 (19/11/2026). Eres el estratega de @gtaviceclips6, "
              "cuenta de humor y gaming para jóvenes de España en TikTok, Reels y Shorts. Propón 5 ideas de vídeos cortos "
              "para publicar HOY y crecer en seguidores: memes de GTA 6, situaciones con las que la gente se identifica, "
              "encuestas, comparativas, retos. Para cada una: título gancho, qué se ve (1 frase) y por qué puede ser viral. "
              "Nada de política, odio ni cosas falsas. Responde en español, formato lista corta, sin markdown.")
    for modelo in ia.MODELOS_GEMINI:
        r = ia.gemini_post(modelo, {"contents": [{"role": "user", "parts": [{"text": pedido}]}],
                                    "generationConfig": {"temperature": 1.0}})
        if r.ok:
            txt = "".join(p.get("text", "") for p in r.json()["candidates"][0]["content"]["parts"])
            return "💡 Ideas para hoy\n\n" + txt.replace("**", "").strip() + "\n\n👉 Dile a Claude cuál te gusta y te monta el vídeo."
    return "💡 La IA está saturada ahora mismo. Prueba en un rato."


def atender(texto):
    try:
        return _atender(texto)
    except YaEnMarcha as e:
        enviar(f"⏳ Ya estoy en ello (me lo pediste hace {e.args[0]} min). En cuanto termine te llega aquí 👌")


def _atender(texto):
    t = texto.strip()
    tl = t.lower()
    a = ajustes.leer()
    if tl.startswith(("/start", "/menu")):
        return enviar("🌴 Menú de GTA VICE CLIPS 6. Elige abajo 👇")
    if tl.startswith(("/ayuda", "/help")) or t == B_AYUDA:
        return enviar(AYUDA)
    if tl.startswith("/estado") or t == B_ESTADO:
        return enviar(estado())
    if t == B_PENDIENTES:
        return enviar(pendientes())
    if tl.startswith("/virales") or t == B_VIRALES:
        lanzar("virales.yml")
        return enviar("🔥 Buscando lo que está explotando ahora… En 10-15 min te llega lo bueno (si la IA lo ve gracioso).")
    if t == B_GTA:
        lanzar("cortar-shorts.yml", rango="", simulacro="false")
        return enviar("🎮 Buscando clips de GTA 6… En 10-20 min te llegan los buenos.")
    if t == B_NOTICIAS:
        lanzar("noticias.yml", modo="gta")
        return enviar("📰 Mirando noticias oficiales de GTA 6… Si hay algo importante, te llega el vídeo en 5 min.")
    if t == B_TENDENCIAS:
        lanzar("noticias.yml", modo="virales")
        return enviar("🌍 Mirando lo más buscado en España… Si hay algo divertido, te llega «VIRAL HOY» en 5 min.")
    if t == B_ENLACE:
        return enviar("🎬 Pega aquí el enlace (X, Twitch, Kick, TikTok, Instagram…).\n"
                      "Si quieres, escribe algo después para darme contexto. Ej.:\nhttps://x.com/... golazo en el último minuto")
    if t == B_IDEAS:
        return enviar(ideas())
    if t == B_TOP5:
        lanzar("recopilacion-semanal.yml")
        return enviar("🏆 Montando el TOP 5 de la semana… En 10-15 min te llega.")
    if t == B_SIMULACRO:
        lanzar("cortar-shorts.yml", rango="", simulacro="true")
        return enviar("🧪 Simulacro con GTA 5 en marcha. Los vídeos llegan marcados 🧪 y se descartan solos.")
    if t == B_PAUSA:
        ajustes.guardar(pausa=True)
        return enviar("⏸ Bot en pausa: no buscaré nada automático hasta que pulses ▶️ Reanudar.\n"
                      "(Lo que me pidas a mano sí lo hago. Lo ya aprobado sigue saliendo.)")
    if t == B_SEGUIR:
        ajustes.guardar(pausa=False)
        return enviar("▶️ ¡Vuelvo al trabajo! Busco clips, virales y noticias yo solo.")
    if t == B_AJUSTES:
        return enviar("⚙️ Ajustes\n\n" + estado().split("\n\n", 2)[-1], menu_ajustes())
    if t == B_VOLVER:
        return enviar("🌴 Menú principal 👇")
    if t == B_NOTA or tl.startswith("/nota"):
        num = re.search(r"\d+", t)
        if num and 3 <= int(num.group()) <= 10:
            ajustes.guardar(nota_minima=int(num.group()))
            return enviar(f"🎯 Hecho: solo te mando clips con nota {num.group()}/10 o más.", menu_ajustes())
        return enviar("🎯 ¿Cuánto de exigente quieres que sea la IA? (ahora: " + str(a["nota_minima"] or 7) + "/10)\n"
                      "5 = te llegan muchos clips · 7 = equilibrado · 9 = solo bombazos",
                      teclado([["/nota 5", "/nota 6", "/nota 7"], ["/nota 8", "/nota 9"], [B_VOLVER]]))
    for boton, clave, nombre in ((B_TOG_VIR, "virales", "🔥 Virales de Twitch"), (B_TOG_TEN, "tendencias", "🌍 Tendencias"),
                                 (B_TOG_NOT, "noticias_gta", "📰 Noticias de GTA 6")):
        if t == boton:
            nuevo = not a[clave]
            ajustes.guardar(**{clave: nuevo})
            return enviar(f"{nombre}: {'✅ activado' if nuevo else '⛔ desactivado'}", menu_ajustes())
    m = ENLACE.search(t)
    if m:
        url = m.group(0).rstrip(").,")
        if re.search(r"youtu\.?be", url):
            return enviar("⚠️ YouTube no deja descargar desde el bot. Busca el mismo vídeo en X (Twitter) y mándame ese enlace.")
        contexto = (t.replace(m.group(0), "").strip() or "Vídeo que me manda el dueño de la cuenta (puede ser de cualquier tema)")[:300]
        lanzar("escenas.yml", url=url, reels="4", contexto=contexto)
        return enviar("📩 ¡Recibido! Lo estoy montando. En 5-15 min te llega aquí con los botones ✅/❌.")
    enviar("🤔 No te he entendido. Usa el menú de abajo o pega un enlace.")


COMANDOS = [{"command": "menu", "description": "Abrir el menú"},
            {"command": "estado", "description": "Cómo va el día"},
            {"command": "virales", "description": "Buscar ya lo que está explotando"},
            {"command": "ayuda", "description": "Qué puedo hacer"}]


def main():
    if datetime.datetime.utcnow().minute < 5:          # una vez por hora basta para tener el menú "/" al día
        tg.tg("setMyCommands", data={"commands": json.dumps(COMANDOS)})
    aviso = pathlib.Path("menu_enviado.txt")
    if not aviso.exists():                              # la primera vez, te enseño el menú nuevo
        enviar("🌴 ¡Novedad! Ya tienes MENÚ: usa los botones de abajo 👇 (si no los ves, toca el icono ⌨️ junto al micro)")
        aviso.write_text("1")
    ok, no = tg.procesar_botones()
    print("Botones:", ok, no, "· mensajes:", len(tg.MENSAJES))
    for texto in tg.MENSAJES:
        try:
            atender(texto)
        except Exception as e:
            tg.mensaje(f"⚠️ No pude con eso: {tg.sin_claves(e)[:200]}")


if __name__ == "__main__":
    main()
