# GTA VICE CLIPS 6 - de un trozo de video a un short listo en Telegram
# (lo usan cortar.py para clips de Twitch y directo.py para momentos cortados en directo)
import os, re, json, hashlib, pathlib, datetime
import video, ia, tg

HANDLE = video.HANDLE
SHORTS = pathlib.Path("shorts")
LISTA = SHORTS / "lista.jsonl"
MIN_PALABRAS = int(os.environ.get("MIN_PALABRAS", "3") or 3)   # filtro: clips donde casi no se habla, fuera
MIN_SEG = 8
NOTA_MINIMA = float(os.environ.get("NOTA_MINIMA", "7") or 7)          # la IA puntua de 1 a 10; por debajo, fuera
MIN_VISTAS_SIN_IA = int(os.environ.get("MIN_VISTAS_SIN_IA", "50") or 50)  # si la IA no responde, solo clips muy vistos
SIMULACRO = os.environ.get("SIMULACRO") == "true"

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


def escribir_textos(item, transcripcion, t=None):
    s = item["streamer"] or "este hombre"
    tag = re.sub(r"\W", "", (item["streamer"] or "").lower())
    h = int(hashlib.md5(item["url"].encode()).hexdigest(), 16)
    if t and t.get("titulo") and t.get("comentario"):
        base = HASHTAGS if es_de_gta(item, transcripcion) else "#humor #clipsgraciosos #viral #parati #fyp #twitch #streamer"
        if t.get("tipo") == "escena_guapa":
            base = "#gta6 #gtavi #gta6españa #vicecity #leonida #graficos #gaming #viral #parati #fyp"
        tags = []
        for x in base.split() + [f"#{tag}"] + ["#" + re.sub(r"\W", "", str(x).lstrip("#")) for x in (t.get("hashtags") or [])]:
            if len(x) > 1 and x.lower() not in [y.lower() for y in tags]:
                tags.append(x)
        texto = (f"{t.get('risa') or RISAS[h % len(RISAS)]}\n\n{t['comentario']}\n\n"
                 f"{t.get('pregunta') or '¿Tú qué harías? 👇'}\nSíguenos para más 👉 {HANDLE}\n\n"
                 + " ".join(tags[:16]))
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
    transcripcion = " ".join(w for w, _, _ in palabras)
    # la IA mira 4 fotogramas + lo que se dice y decide si es gracioso / escena guapa / nada
    juicio = ia.textos(item["streamer"] or "", item["titulo"], transcripcion, video.fotogramas(src))
    forzar = item.get("forzar")          # clips que has puesto tu a mano en clips.txt: no se filtran
    if juicio:
        if not forzar and (juicio.get("tipo") not in ("gracioso", "escena_guapa") or juicio["nota"] < NOTA_MINIMA):
            raise RuntimeError(f"descartado: no es bueno ({juicio.get('tipo')}, nota {juicio['nota']:g}: {juicio.get('motivo')})")
    elif not forzar:
        if len(palabras) < MIN_PALABRAS:
            raise RuntimeError("descartado: casi no habla nadie")
        if (item.get("vistas") or 0) < MIN_VISTAS_SIN_IA:
            raise RuntimeError("descartado: sin IA no puedo juzgarlo y tiene pocas visitas")
    titulo, gancho, texto, quien = escribir_textos(item, transcripcion, juicio)
    if juicio:
        quien = f"IA · {'😂 gracioso' if juicio.get('tipo') == 'gracioso' else '😍 escena guapa'} · nota {juicio['nota']:g}/10"
    # recorte inteligente: fuera silencios y, si es largo, los mejores 40 s
    if not (juicio and juicio.get("tipo") == "escena_guapa"):
        ini, fin = video.mejor_tramo(palabras, video.picos_volumen(src), dur)
        if ini > 0.2 or fin < dur - 0.2:
            src = video.recortar(src, ini, fin, pathlib.Path(tmp) / f"rec{n}.mp4")
            palabras = [(w, a - ini, b - ini) for w, a, b in palabras if a >= ini and b <= fin]
            dur = fin - ini
    final = pathlib.Path(tmp) / f"short{n}.mp4"
    modo = video.montar(src, final, dur, titulo, gancho, palabras, tmp=tmp)
    cid = hashlib.md5(item["url"].encode()).hexdigest()[:10]
    vistas = f" · 👀 {item['vistas']:,} visitas".replace(",", ".") if item.get("vistas") else ""
    info = f"\n\n— {item['streamer']} · {int(dur)} s · {modo} · textos: {quien}{vistas}{info_extra}"
    if SIMULACRO:
        info = "\n\n🧪 SIMULACRO (prueba, no publicar)" + info
    tg.enviar_video(final, texto + info, cid)
    guardar(item, final, cid, titulo, texto, quien)
    if SIMULACRO:   # los clips de prueba se descartan solos
        with open(tg.DESCARTADOS, "a") as f:
            f.write(cid + "\n")
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
