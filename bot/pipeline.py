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
NEUTROS = ["{s} no tiene filtro y por eso lo queremos 😂", "Lo que acaba de pasar en el directo de {s} 💀",
           "{s} en su máximo esplendor 🔥", "El chat de {s} no se lo podía creer 😭",
           "Momento de {s} que tenía que estar en todos lados 😂"]
NEUTROS_GANCHO = ["NO PUEDE SER", "MIRA SU CARA", "ESPERA AL FINAL", "QUÉ ACABA DE PASAR"]
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
    """Una frase real del streamer para citarla (siempre que haya voz)."""
    trozos = [t.strip(" ,") for t in re.split(r"[.!?¿¡]", txt) if 4 <= len(t.split()) <= 12]
    if trozos:
        return max(trozos, key=len)[:90]
    pal = txt.split()
    if len(pal) >= 4:                      # sin puntuacion: 8 palabras del centro del clip
        m = len(pal) // 2
        return " ".join(pal[max(0, m - 4):m + 4]).strip(" ,")[:90]
    return ""


def es_de_gta(item, transcripcion):
    return bool(re.search(r"gta|vice ?city|leonida|lucia|jason|rockstar|grand theft", f"{item['titulo']} {transcripcion}", re.I))


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
    gta = es_de_gta(item, transcripcion)
    titulo = item["titulo"] or "Reacción a GTA 6"
    if item.get("directo") and frase:      # en directo no hay titulo: usamos lo que dice
        titulo = f'{s}: "{" ".join(frase.split()[:6])}…"'
    cita = f'\n\n"{frase}" 💀' if frase and not item.get("directo") else ""
    comentario = (COMENTARIOS[h % len(COMENTARIOS)] if gta else NEUTROS[h % len(NEUTROS)]).format(s=s)
    pregunta = "¿Y tú cómo vas a reaccionar el 19/11? 👇" if gta else "¿Qué habrías hecho tú? 👇"
    etiquetas = HASHTAGS if gta else "#humor #clipsgraciosos #viral #parati #fyp #twitch #streamer #momentosepicos"
    texto = (f"{RISAS[h % len(RISAS)]}\n\n{titulo} 🔥{cita}\n\n{comentario}\n\n"
             f"{pregunta}\nSíguenos para más 👉 {HANDLE}\n\n{etiquetas}" + (f" #{tag}" if tag else ""))
    return titulo, GANCHOS[h % len(GANCHOS)] if gta else NEUTROS_GANCHO[h % len(NEUTROS_GANCHO)], texto, "plantilla"


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
    guardar(item, final, cid, titulo, texto, quien)
    return cid


def guardar(item, final, cid, titulo, texto, quien=""):
    SHORTS.mkdir(exist_ok=True)
    nombre = re.sub(r"[^a-z0-9]+", "-", f"{item['streamer']}-{cid}".lower())
    (SHORTS / f"{nombre}.mp4").write_bytes(pathlib.Path(final).read_bytes())
    with open(LISTA, "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(id=cid, archivo=f"{nombre}.mp4", url=item["url"], streamer=item["streamer"],
                                titulo=titulo, texto=texto, textos=quien, vistas=item.get("vistas") or 0,
                                fecha=datetime.datetime.utcnow().isoformat(timespec="minutes")),
                           ensure_ascii=False) + "\n")
