# Vice GTA6 Clips - de donde salen los clips (clips.txt y Twitch) y que tramo cortar
import os, re, json, pathlib, datetime
from video import ejecutar

MAXDUR = 59          # segundos maximos de cada short
DURDEF = 40          # duracion si no se indica
POR_STREAMER = int(os.environ.get("POR_STREAMER", "3") or 3)   # clips de Twitch por streamer y pasada
MIN_VISTAS = int(os.environ.get("MIN_VISTAS", "0") or 0)       # descarta clips con menos visitas
LANZAMIENTO = datetime.date(2026, 11, 19)
# Solo clips de GTA 6 (antes cogia cualquier "GTA", incluido GTA 5 o Minecraft)
CLAVES = re.compile(os.environ.get("FILTRO") or r"gta ?(6|vi\b)|grand theft auto (6|vi\b)|leonida|vice ?city|lucia|jason duval", re.I)


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
    if os.environ.get("TOP_ESPANOL", "true") == "true":
        try:
            vistos = {c["url"] for c in out}
            top = clips_top_espanol(os.environ.get("JUEGO_TOP") or "Grand Theft Auto VI")
            out += [c for c in top if c["url"] not in vistos]
            print("Top en español de todo Twitch:", len(top))
        except Exception as e:
            print("Top en español:", e)
    out = [c for c in out if c["vistas"] >= MIN_VISTAS]
    out.sort(key=lambda c: c["vistas"], reverse=True)   # los clips mas vistos primero
    return out

def twitch_token():
    cid, sec = os.environ.get("TWITCH_CLIENT_ID"), os.environ.get("TWITCH_CLIENT_SECRET")
    if not (cid and sec):
        return None, None
    import requests
    r = requests.post("https://id.twitch.tv/oauth2/token", timeout=30, data={
        "client_id": cid, "client_secret": sec, "grant_type": "client_credentials"}).json()
    return cid, r.get("access_token")


def clips_top_espanol(juego="Grand Theft Auto VI", maximo=10):
    """Los clips en español mas vistos del juego en TODO Twitch (no solo nuestra lista)."""
    import requests
    cid, tok = twitch_token()
    if not tok:
        return []
    h = {"Client-Id": cid, "Authorization": f"Bearer {tok}"}
    g = requests.get("https://api.twitch.tv/helix/games", params={"name": juego}, headers=h, timeout=30).json().get("data", [])
    if not g:
        print("Twitch no conoce todavía el juego", juego); return []
    horas = 24 if rango_auto() == "24hr" else 24 * 7
    desde = (datetime.datetime.utcnow() - datetime.timedelta(hours=horas)).strftime("%Y-%m-%dT%H:%M:%SZ")
    datos, cursor = [], None
    for _ in range(5):                      # hasta 500 clips (los mas vistos primero), y nos quedamos con los de España/español
        params = {"game_id": g[0]["id"], "started_at": desde, "first": 100}
        if cursor:
            params["after"] = cursor
        r = requests.get("https://api.twitch.tv/helix/clips", headers=h, timeout=30, params=params).json()
        datos += r.get("data", [])
        cursor = (r.get("pagination") or {}).get("cursor")
        if not cursor:
            break
    es = [c for c in datos if (c.get("language") or "").startswith("es")]
    # ademas: los canales en español que estan ahora en directo con el juego -> sus clips de las ultimas horas
    vivos = requests.get("https://api.twitch.tv/helix/streams", headers=h, timeout=30,
                         params={"game_id": g[0]["id"], "language": "es", "first": 100}).json().get("data", [])
    vivos.sort(key=lambda v: v.get("viewer_count", 0), reverse=True)
    ya = {c["id"] for c in es}
    for v in vivos[:15]:
        for c in requests.get("https://api.twitch.tv/helix/clips", headers=h, timeout=30, params={
                "broadcaster_id": v["user_id"], "started_at": desde, "first": 5}).json().get("data", []):
            if c.get("game_id") == g[0]["id"] and c["id"] not in ya:
                es.append(c); ya.add(c["id"])
    pathlib.Path("estado_busqueda.txt").write_text(
        f"{datetime.datetime.utcnow():%Y-%m-%d %H:%M} {juego}: {len(datos)} clips mirados, {len(vivos)} directos en español, {len(es)} clips en español\n", encoding="utf-8")
    es.sort(key=lambda c: c.get("view_count", 0), reverse=True)
    return [dict(url=c["url"], streamer=c["broadcaster_name"], titulo=c.get("title", ""), inicio=None, dur=None,
                 vistas=c.get("view_count", 0)) for c in es[:maximo]]


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
