# GTA VICE CLIPS 6 - vigilante de directos
# Mira (con la API de Twitch) que streamers de la lista estan EN DIRECTO jugando a GTA VI,
# graba su directo durante un rato, escucha su chat y, cuando el chat explota (risas, "WTF", "KEKW"...),
# corta ese momento y te lo manda a Telegram ya montado. Asi tenemos el clip minutos despues de que pase.
import os, re, time, json, socket, pathlib, subprocess, datetime, collections
import requests
import tg, pipeline
from video import ejecutar

CID = os.environ.get("TWITCH_CLIENT_ID", "")
SECRET = os.environ.get("TWITCH_CLIENT_SECRET", "")
JUEGO = os.environ.get("JUEGO") or "Grand Theft Auto VI"
MINUTOS = float(os.environ.get("MINUTOS_DIRECTO", "20") or 20)     # cuanto rato escucha cada pasada
MAX_DIRECTOS = int(os.environ.get("MAX_DIRECTOS", "3") or 3)       # cuantos directos a la vez
MAX_MOMENTOS = int(os.environ.get("MAX_MOMENTOS", "2") or 2)       # momentos por directo y pasada
ANTES, DESPUES = 30, 10                                              # segundos antes/despues del pico
CLAVES = re.compile(r"ja(ja)+|jsj|xd+|kekw|lul|omegalul|lmao|wtf|que (co[nñ]o|cojones)|💀|😂|🤣|clip", re.I)
TMP = pathlib.Path("tmp_directo"); TMP.mkdir(exist_ok=True)


def twitch(ruta, token, **params):
    r = requests.get(f"https://api.twitch.tv/helix/{ruta}", params=params, timeout=30,
                     headers={"Client-Id": CID, "Authorization": f"Bearer {token}"})
    r.raise_for_status()
    return r.json().get("data", [])


def directos_de_gta():
    r = requests.post("https://id.twitch.tv/oauth2/token", timeout=30, data={
        "client_id": CID, "client_secret": SECRET, "grant_type": "client_credentials"})
    if "access_token" not in r.json():
        raise SystemExit(f"Twitch no acepta las claves (revisa TWITCH_CLIENT_ID y TWITCH_CLIENT_SECRET): {r.text[:150]}")
    token = r.json()["access_token"]
    juego = twitch("games", token, name=JUEGO)
    if not juego:
        print("Twitch no conoce todavía el juego:", JUEGO)
        return []
    logins = [l for l in pathlib.Path("streamers.txt").read_text(encoding="utf-8").split() if not l.startswith("#")]
    vivos = []
    for i in range(0, len(logins), 100):
        vivos += twitch("streams", token, game_id=juego[0]["id"], user_login=logins[i:i + 100], first=100)
    vivos.sort(key=lambda s: s.get("viewer_count", 0), reverse=True)
    return vivos[:MAX_DIRECTOS]


def grabar(login):
    url = ejecutar(["yt-dlp", "-g", "-f", "best[height<=720]/best", f"https://www.twitch.tv/{login}"]).strip().splitlines()[0]
    ruta = TMP / f"rec_{login}.ts"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-i", url, "-t", str(int(MINUTOS * 60) + 15),
                          "-c", "copy", str(ruta)], stdin=subprocess.DEVNULL)
    return p, ruta, time.time()


def escuchar_chat(logins, segundos):
    """Cuenta mensajes del chat cada 5 s. Devuelve {login: Counter(bloque -> puntos)}."""
    puntos = {l: collections.Counter() for l in logins}
    s = socket.socket(); s.settimeout(5)
    s.connect(("irc.chat.twitch.tv", 6667))
    s.send(b"PASS SCHMOOPIIE\r\nNICK justinfan" + str(int(time.time()) % 99999).encode() + b"\r\n")
    for l in logins:
        s.send(f"JOIN #{l}\r\n".encode())
    t0, buf = time.time(), ""
    while time.time() - t0 < segundos:
        try:
            buf += s.recv(65536).decode("utf-8", "ignore")
        except socket.timeout:
            continue
        *lineas, buf = buf.split("\r\n")
        for li in lineas:
            if li.startswith("PING"):
                s.send(b"PONG :tmi.twitch.tv\r\n"); continue
            m = re.search(r"PRIVMSG #(\w+) :(.*)", li)
            if m and m.group(1) in puntos:
                bloque = int((time.time() - t0) // 5)
                puntos[m.group(1)][bloque] += 1 + (2 if CLAVES.search(m.group(2)) else 0)
    s.close()
    return puntos, t0


def picos(cont, maximo):
    """Bloques donde el chat se dispara (3 veces por encima de lo normal)."""
    if not cont:
        return []
    serie = [cont.get(i, 0) for i in range(max(cont) + 1)]
    out = []
    for i, v in sorted(enumerate(serie), key=lambda x: -x[1]):
        base = sorted(serie[max(0, i - 24):i] or [0])[len(serie[max(0, i - 24):i] or [0]) // 2]
        if v >= max(15, 3 * (base + 1)) and all(abs(i - j) > 12 for j in out):
            out.append(i)
        if len(out) >= maximo:
            break
    return sorted(out)


def main():
    if not (CID and SECRET):
        raise SystemExit("Faltan los secretos TWITCH_CLIENT_ID y TWITCH_CLIENT_SECRET")
    if not tg.chat_id():
        raise SystemExit("Falta el chat de Telegram")
    vivos = directos_de_gta()
    if not vivos:
        print("Nadie de la lista está en directo con", JUEGO); return
    logins = [v["user_login"] for v in vivos]
    nombres = {v["user_login"]: v["user_name"] for v in vivos}
    print("En directo:", logins)
    grab = {}
    for l in logins:
        try:
            grab[l] = grabar(l)
        except Exception as e:
            print("No pude grabar", l, e)
    if not grab:
        return
    puntos, t_chat = escuchar_chat(list(grab), MINUTOS * 60)
    hechos = 0
    for l, (proc, ruta, t_rec) in grab.items():
        try:
            proc.wait(timeout=60)
        except subprocess.TimeoutExpired:
            proc.terminate(); proc.wait()
        for k, b in enumerate(picos(puntos[l], MAX_MOMENTOS), 1):
            momento = (t_chat + b * 5) - t_rec            # segundo dentro de la grabacion
            ini = max(0, momento - ANTES)
            trozo = TMP / f"{l}_{k}.mp4"
            try:
                ejecutar(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{ini:.1f}", "-i", str(ruta), "-t", str(ANTES + DESPUES),
                          "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", str(trozo)])
                ahora = datetime.datetime.utcnow().strftime("%Y%m%d%H%M")
                item = dict(url=f"https://www.twitch.tv/{l}#{ahora}-{k}", streamer=nombres[l],
                            titulo=f"{nombres[l]} en directo" + (" jugando a GTA 6" if "VI" in JUEGO else ""), vistas=0)
                pipeline.procesar(item, trozo, f"d{l}{k}", info_extra=" · 🔴 cortado del directo", tmp=TMP)
                hechos += 1
            except Exception as e:
                print("Momento descartado:", l, k, e)
        ruta.unlink(missing_ok=True)
    if hechos:
        tg.mensaje(f"🔴 Vigilante de directos: {hechos} momento(s) nuevo(s) cortado(s) en directo.")


if __name__ == "__main__":
    try:
        main()
    except BaseException as e:   # deja constancia del fallo (en Telegram y en el repo) para poder arreglarlo
        import traceback
        err = traceback.format_exc()
        print(err)
        pathlib.Path("errores_directo.txt").write_text(err, encoding="utf-8")
        try:
            tg.mensaje(f"⚠️ Vigilante de directos: {e}")
        except Exception:
            pass
        raise
