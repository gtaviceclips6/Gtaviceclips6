# Vice GTA6 Clips - de donde salen los clips (clips.txt y Twitch) y que tramo cortar
import os, re, json, pathlib, datetime
from video import ejecutar

MAXDUR = 59          # segundos maximos de cada short
DURDEF = 40          # duracion si no se indica
POR_STREAMER = int(os.environ.get("POR_STREAMER", "3") or 3)   # clips de Twitch por streamer y pasada
MIN_VISTAS = int(os.environ.get("MIN_VISTAS", "0") or 0)       # descarta clips con menos visitas
LANZAMIENTO = datetime.date(2026, 11, 19)
# Solo clips de GTA 6 (antes cogia cualquier "GTA", incluido GTA 5 o Minecraft)
CLAVES = re.compile(r"gta ?(6|vi\b)|grand theft auto (6|vi\b)|leonida|vice ?city|lucia|jason duval", re.I)


def segundos(t):
    if not t:
        return None
    t = t.strip()
    if ":" in t:
        s = 0
        for parte in t.split(":"):
            s = s * 60 + float(parte)
        return s
    return float(t)

def leer_lista():
    out = []
    p = pathlib.Path("clips.txt")
    if not p.exists():
        return out
    for linea in p.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#"):
            continue
        c = [x.strip() for x in linea.split("|")] + [""] * 5
        out.append(dict(url=c[0], streamer=c[1], titulo=c[2], inicio=segundos(c[3]), dur=segundos(c[4])))
    return out

def buscar_twitch():
    out = []
    p = pathlib.Path("streamers.txt")
    if not p.exists():
        return out
    rango = os.environ.get("RANGO") or rango_auto()
    print("Buscando clips de Twitch, rango:", rango)
    for login in leer_streamers():
        try:
            js = json.loads(ejecutar(["yt-dlp", "--flat-playlist", "-J", "--playlist-end", "300",
                                      f"https://www.twitch.tv/{login}/clips?filter=clips&range={rango}"]))
        except Exception as e:
            print("No pude buscar en", login, e)
            continue
        buenos = [e for e in js.get("entries", []) if CLAVES.search(e.get("title") or "")]
        buenos.sort(key=lambda e: e.get("view_count") or 0, reverse=True)
        for e in buenos[:POR_STREAMER]:
            url = e.get("url") or e.get("webpage_url")
            if url:
                out.append(dict(url=url, streamer=login, titulo=e.get("title", ""), inicio=None, dur=None,
                                vistas=e.get("view_count") or 0))
    out = [c for c in out if c["vistas"] >= MIN_VISTAS]
    out.sort(key=lambda c: c["vistas"], reverse=True)   # los clips mas vistos primero
    return out

def leer_streamers():
    """Nombres de streamers.txt: una linea por canal; las lineas con # son comentarios."""
    p = pathlib.Path("streamers.txt")
    if not p.exists():
        return []
    out = []
    for l in p.read_text(encoding="utf-8").splitlines():
        l = l.strip()
        if l and not l.startswith("#"):
            out.append(l.split()[0].lower().replace("twitch.tv/", "").strip("/@"))
    return out

def rango_auto():
    # Antes del lanzamiento busca en la ultima semana; desde el 18/11, solo lo del ultimo dia
    hoy = datetime.date.today()
    return "24hr" if hoy >= LANZAMIENTO - datetime.timedelta(days=1) else "7d"

def elegir_tramo(meta, inicio, dur):
    total = meta.get("duration") or 0
    dur = min(dur or DURDEF, MAXDUR)
    if inicio is not None:
        return inicio, dur, "minuto indicado"
    if total and total <= MAXDUR + 2:
        return 0, min(total, MAXDUR), "clip entero"
    picos = [h for h in (meta.get("heatmap") or []) if h.get("start_time", 0) >= 30]
    if picos:
        top = max(picos, key=lambda h: h.get("value", 0))
        ini = max(0, top["start_time"] - 8)
        return ini, min(dur, total - ini) if total else dur, "momento más repetido de YouTube"
    ini = min(90, total / 3) if total > 120 else 0
    return ini, dur, "sin datos: cojo cerca del principio"

def descargar(item, ini, dur, salida):
    cmd = ["yt-dlp", "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4",
           "-o", str(salida), "--no-playlist", "--force-overwrites"]
    if not (ini == 0 and dur <= MAXDUR and "twitch.tv" in item["url"] and "/clip" in item["url"]):
        cmd += ["--download-sections", f"*{ini:.1f}-{ini + dur:.1f}", "--force-keyframes-at-cuts"]
    ejecutar(cmd + [item["url"]])
