# GTA VICE CLIPS 6 - de un trozo de video a un short listo en Telegram
# (lo usan cortar.py para clips de Twitch y directo.py para momentos cortados en directo)
import os, re, json, hashlib, pathlib, datetime
import video, ia, tg

HANDLE = video.HANDLE
SHORTS = pathlib.Path("shorts")
LISTA = SHORTS / "lista.jsonl"
MIN_PALABRAS = int(os.environ.get("MIN_PALABRAS", "3") or 3)   # filtro: clips donde casi no se habla, fuera
MIN_SEG = 8

RISAS = ["JAJAJAJAJA 😂😂😂", "JAJSJAJSJ NO PUEDO 💀💀", "😂😂 me estoy meando", "JAJAJA lo he visto 10 veces 😭",
         "NO PUEDO MÁS 😂😂😂", "JAJAJAJ qué crack 💀"]
GANCHOS = ["NO SE LO ESPERABA", "MIRA SU CARA", "ESPERA AL FINAL", "SE HA VUELTO LOCO", "ESTO ES GTA 6",
           "QUÉ ACABA DE PASAR", "NO PUEDE SER"]
COMENTARIOS = [
    "{s} ya está más metido en Vice City que en su propia casa 🌴",
    "{s} el 19/11: 'una partidita rápida'… 14 horas después 💀",
    "Rockstar, contratad a {s} para el próximo tráiler, por favor 🙏",
    "{s} lleva 13 años esperando esto y se le nota en la cara 😭",
    "Que alguien le dé a {s} el GTA 6 ya, que no aguanta más 😂",
    "El 19 de noviembre {s} no duerme, apostamos lo que queráis 👀",
    "{s} reaccionando como todos nosotros a las 3 de la mañana 💀",
    "Nivel de hype de {s}: no apto para cardíacos 🔥",
]
HASHTAGS = "#gta6 #gtavi #gta6españa #humor #clipsgraciosos #viral #parati #fyp #twitch #streamer #vicecity"


def norm(t):
    return re.sub(r"\W+", " ", (t or "").lower()).strip()


def ya_hay_igual(streamer, titulo):
    """Evita subir dos clips con el mismo titulo del mismo streamer."""
    if not LISTA.exists():
        return False
    clave = norm(streamer) + "|" + norm(titulo)
    return any(norm(d.get("streamer")) + "|" + norm(d.get("titulo")) == clave
               for d in map(json.loads, LISTA.read_text(encoding="utf-8").splitlines()))


def frase_corta(txt):
    trozos = [t.strip(" ,") for t in re.split(r"[.!?¿¡]", txt) if 4 <= len(t.split()) <= 12]
    return max(trozos, key=len)[:90] if trozos else ""


def escribir_textos(item, transcripcion):
    s = item["streamer"] or "este hombre"
    tag = re.sub(r"\W", "", (item["streamer"] or "").lower())
    h = int(hashlib.md5(item["url"].encode()).hexdigest(), 16)
    t = ia.textos(s, item["titulo"], transcripcion)
    if t and t.get("titulo") and t.get("comentario"):
        extra = " ".join("#" + re.sub(r"\W", "", x.lstrip("#")) for x in (t.get("hashtags") or []) if x)
        texto = (f"{t.get('risa') or RISAS[h % len(RISAS)]}\n\n{t['comentario']}\n\n"
                 f"{t.get('pregunta') or '¿Tú qué harías? 👇'}\nSíguenos para más 👉 {HANDLE}\n\n"
                 f"{HASHTAGS} #{tag} {extra}".strip())
        return t["titulo"], (t.get("gancho") or GANCHOS[h % len(GANCHOS)]), texto, "IA"
    frase = frase_corta(transcripcion)
    cita = f'\n\n"{frase}" 💀' if frase else ""
    texto = (f"{RISAS[h % len(RISAS)]}\n\n{item['titulo'] or 'Reacción a GTA 6'} 🌴{cita}\n\n"
             f"{COMENTARIOS[h % len(COMENTARIOS)].format(s=s)}\n\n"
             f"¿Y tú cómo vas a reaccionar el 19/11? 👇\nSíguenos para más 👉 {HANDLE}\n\n{HASHTAGS}"
             + (f" #{tag}" if tag else ""))
    return item["titulo"] or "Reacción a GTA 6", GANCHOS[h % len(GANCHOS)], texto, "plantilla"


def procesar(item, src, n, info_extra="", tmp="tmp"):
    """item: url, streamer, titulo, vistas. src: video ya descargado/cortado. Lanza error si se descarta."""
    dur = min(video.duracion(src), 59)
    if dur < MIN_SEG:
        raise RuntimeError(f"descartado: demasiado corto ({dur:.0f} s)")
    palabras = video.transcribir(src)
    if len(palabras) < MIN_PALABRAS:
        raise RuntimeError("descartado: casi no habla nadie (sin gracia para un short)")
    transcripcion = " ".join(w for w, _, _ in palabras)
    titulo, gancho, texto, quien = escribir_textos(item, transcripcion)
    final = pathlib.Path(tmp) / f"short{n}.mp4"
    modo = video.montar(src, final, dur, titulo, gancho, palabras, tmp=tmp)
    cid = hashlib.md5(item["url"].encode()).hexdigest()[:10]
    vistas = f" · 👀 {item['vistas']:,} visitas".replace(",", ".") if item.get("vistas") else ""
    info = f"\n\n— {item['streamer']} · {int(dur)} s · {modo} · textos: {quien}{vistas}{info_extra}"
    tg.enviar_video(final, texto + info, cid)
    guardar(item, final, cid, titulo, texto)
    return cid


def guardar(item, final, cid, titulo, texto):
    SHORTS.mkdir(exist_ok=True)
    nombre = re.sub(r"[^a-z0-9]+", "-", f"{item['streamer']}-{cid}".lower())
    (SHORTS / f"{nombre}.mp4").write_bytes(pathlib.Path(final).read_bytes())
    with open(LISTA, "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(id=cid, archivo=f"{nombre}.mp4", url=item["url"], streamer=item["streamer"],
                                titulo=titulo, texto=texto, vistas=item.get("vistas") or 0,
                                fecha=datetime.datetime.utcnow().isoformat(timespec="minutes")),
                           ensure_ascii=False) + "\n")
