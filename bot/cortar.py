# Vice GTA6 Clips - cortador de shorts
# Lee clips.txt (enlaces a mano) y streamers.txt (busca clips de GTA en Twitch),
# corta cada uno en vertical con titulo, credito y subtitulos, y lo manda a Telegram.
import os, re, json, pathlib
import requests
from video import ejecutar, subtitulos, capa, montar, HANDLE
from fuentes import leer_lista, buscar_twitch, elegir_tramo, descargar

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")
MAX_CLIPS = int(os.environ.get("MAX_CLIPS", "5") or 5)   # clips como maximo por pasada
HECHOS = pathlib.Path("hechos.txt")
SHORTS = pathlib.Path("shorts")   # aqui se guarda cada short para programarlo en Metricool
TMP = pathlib.Path("tmp"); TMP.mkdir(exist_ok=True)


def tg(metodo, **kw):
    r = requests.post(f"https://api.telegram.org/bot{TOKEN}/{metodo}", timeout=300, **kw)
    if not r.ok:
        print("Telegram:", r.text[:300])
    return r


def chat_id():
    global CHAT
    if not CHAT:
        upd = tg("getUpdates").json().get("result", [])
        ids = [u["message"]["chat"]["id"] for u in upd if "message" in u]
        CHAT = str(ids[-1]) if ids else ""
    return CHAT


def texto_post(item, canal):
    tag = re.sub(r"\W", "", (item["streamer"] or "").lower())
    tit = item["titulo"] or "Reaccion a GTA 6"
    fuente = f"\n📺 Fuente: {canal}" if canal else ""
    return (f"{tit} 🌴🔥\n\n🎥 Clip de {item['streamer'] or 'su canal'} (todos los créditos para él/ella)"
            f"{fuente}\nSíguenos para no perderte nada de GTA 6 👉 {HANDLE}\n\n"
            f"#gta6 #gtavi #gta6españa #vicecity #leonida #rockstargames #streamerespañol #clipsdetwitch #videojuegos #gamingespañol" + (f" #{tag}" if tag else ""))


def procesar(item, n):
    meta = json.loads(ejecutar(["yt-dlp", "-J", "--no-playlist", item["url"]]))
    if not item["streamer"]:
        item["streamer"] = meta.get("uploader") or meta.get("channel") or ""
    if not item["titulo"]:
        item["titulo"] = meta.get("title", "")
    ini, dur, como = elegir_tramo(meta, item["inicio"], item["dur"])
    crudo, png, ass, final = TMP / f"c{n}.mp4", TMP / f"c{n}.png", TMP / f"c{n}.ass", TMP / f"short{n}.mp4"
    descargar(item, ini, dur, crudo)
    capa(item["titulo"], item["streamer"], png)
    hay_subs = subtitulos(crudo, ass)
    montar(crudo, png, ass if hay_subs else None, final, dur)
    canal = meta.get("channel") or meta.get("uploader") or ""
    pie = texto_post(item, canal)
    vistas = f" · 👀 {item['vistas']:,} visitas en Twitch".replace(",", ".") if item.get("vistas") else ""
    info = f"\n\n— Tramo: {int(ini // 60)}:{int(ini % 60):02d} ({int(dur)} s) · {como}{vistas}"
    with open(final, "rb") as f:
        r = tg("sendVideo", data={"chat_id": chat_id(), "caption": (pie + info)[:1024], "supports_streaming": "true"},
               files={"video": f})
    if not r.ok:
        raise RuntimeError("Telegram no aceptó el vídeo: " + r.text[:150])
    guardar(item, final, pie)


def guardar(item, final, pie):
    SHORTS.mkdir(exist_ok=True)
    nombre = re.sub(r"[^a-z0-9]+", "-", f"{item['streamer']}-{item['url'].rstrip('/').split('/')[-1]}".lower())[:80]
    (SHORTS / f"{nombre}.mp4").write_bytes(pathlib.Path(final).read_bytes())
    with open(SHORTS / "lista.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(archivo=f"{nombre}.mp4", url=item["url"], streamer=item["streamer"],
                                titulo=item["titulo"], texto=pie), ensure_ascii=False) + "\n")


def main():
    if not TOKEN or not chat_id():
        raise SystemExit("Falta el token o el chat de Telegram")
    hechos = set(HECHOS.read_text(encoding="utf-8").split()) if HECHOS.exists() else set()
    items, vistos = [], set()
    for it in leer_lista() + buscar_twitch():
        if it["url"] not in hechos and it["url"] not in vistos:
            vistos.add(it["url"]); items.append(it)
    if not items:
        if os.environ.get("EVENTO") != "schedule":   # en las pasadas automaticas no molesta
            tg("sendMessage", data={"chat_id": CHAT, "text": "🤖 No hay clips nuevos que cortar."})
        return
    pendientes = len(items) - MAX_CLIPS
    items = items[:MAX_CLIPS]
    aviso = f" (quedan {pendientes} para la próxima pasada)" if pendientes > 0 else ""
    tg("sendMessage", data={"chat_id": CHAT, "text": f"🤖 Empiezo a cortar {len(items)} clip(s){aviso}…"})
    bien = mal = 0
    for n, it in enumerate(items, 1):
        try:
            procesar(it, n); bien += 1
            hechos.add(it["url"])
        except Exception as e:
            mal += 1
            tg("sendMessage", data={"chat_id": CHAT, "text": f"❌ No pude con:\n{it['url']}\nMotivo: {e}"})
            hechos.add(it["url"])
        HECHOS.write_text("\n".join(sorted(hechos)) + "\n", encoding="utf-8")
    tg("sendMessage", data={"chat_id": CHAT, "text": f"✅ Terminado: {bien} short(s) listos, {mal} con error."})


if __name__ == "__main__":
    main()
