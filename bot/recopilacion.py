# GTA VICE CLIPS 6 - recopilacion semanal "TOP 5 MOMENTOS DE GTA 6 DE LA SEMANA"
# Coge los shorts de los ultimos 7 dias (primero los que aprobaste con ✅, luego los mas vistos),
# les pone una portada y carteles #5...#1 y lo manda a Telegram (cabe en el limite de 50 MB).
import json, pathlib, datetime, subprocess
from PIL import Image, ImageDraw, ImageFont
import tg, pipeline
from video import ejecutar, FUENTE, W, H, ROSA, CIAN, AMARILLO, BLANCO

TMP = pathlib.Path("tmp_top"); TMP.mkdir(exist_ok=True)


def cartel(lineas, ruta):
    im = Image.new("RGB", (W, H), (12, 0, 30))
    d = ImageDraw.Draw(im)
    y = H // 2 - sum(t for _, t, _ in lineas) // 2 - 40
    for txt, tam, color in lineas:
        f = ImageFont.truetype(FUENTE, tam)
        w = d.textlength(txt, font=f)
        d.text(((W - w) / 2, y), txt, font=f, fill=color, stroke_width=8, stroke_fill=ROSA)
        y += int(tam * 1.15)
    im.save(ruta)


def a_video(png, seg, salida):
    ejecutar(["ffmpeg", "-y", "-loglevel", "error", "-loop", "1", "-t", str(seg), "-i", str(png),
              "-f", "lavfi", "-t", str(seg), "-i", "anullsrc=r=44100:cl=stereo",
              "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast", "-c:a", "aac", "-shortest", str(salida)])


def main():
    if not pipeline.LISTA.exists():
        print("No hay shorts todavía"); return
    hace7 = (datetime.datetime.utcnow() - datetime.timedelta(days=7)).isoformat()
    lista = [json.loads(l) for l in pipeline.LISTA.read_text(encoding="utf-8").splitlines()]
    semana = [d for d in lista if (d.get("fecha") or "") >= hace7 and (pipeline.SHORTS / d["archivo"]).exists()]
    ok = {a["id"] for a in tg.aprobados()}
    fuera = set(tg.DESCARTADOS.read_text().split()) if tg.DESCARTADOS.exists() else set()
    semana = [d for d in semana if d.get("id") not in fuera]
    semana.sort(key=lambda d: (d.get("id") in ok, d.get("vistas", 0)), reverse=True)
    top = semana[:5]
    if len(top) < 3:
        print("Pocos clips esta semana para una recopilación:", len(top)); return
    partes = []
    cartel([("TOP " + str(len(top)), 220, AMARILLO), ("MOMENTOS", 150, BLANCO), ("DE GTA 6", 150, BLANCO),
            ("DE LA SEMANA", 110, CIAN), ("@gtaviceclips6", 60, BLANCO)], TMP / "portada.png")
    a_video(TMP / "portada.png", 2.5, TMP / "p0.mp4"); partes.append(TMP / "p0.mp4")
    for k, d in enumerate(reversed(top)):
        num = len(top) - k
        cartel([(f"#{num}", 380, AMARILLO), (d["streamer"].upper(), 110, BLANCO)], TMP / f"n{num}.png")
        a_video(TMP / f"n{num}.png", 1.2, TMP / f"n{num}.mp4")
        partes += [TMP / f"n{num}.mp4", pipeline.SHORTS / d["archivo"]]
    entradas = sum((["-i", str(p)] for p in partes), [])
    norm = "".join(f"[{i}:v]scale={W}:{H},fps=30,format=yuv420p,setsar=1[v{i}];[{i}:a]aresample=44100,"
                   f"aformat=channel_layouts=stereo[a{i}];" for i in range(len(partes)))
    cadena = "".join(f"[v{i}][a{i}]" for i in range(len(partes)))
    fecha = datetime.date.today().isoformat()
    salida = pipeline.SHORTS / f"top-semana-{fecha}.mp4"
    ejecutar(["ffmpeg", "-y", "-loglevel", "error", *entradas, "-filter_complex",
              norm + f"{cadena}concat=n={len(partes)}:v=1:a=1[v][a]", "-map", "[v]", "-map", "[a]",
              "-c:v", "libx264", "-preset", "medium", "-b:v", "1200k", "-maxrate", "1500k", "-bufsize", "3000k",
              "-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", str(salida)])
    nombres = ", ".join(d["streamer"] for d in top)
    texto = (f"🔥 TOP {len(top)} MOMENTOS DE GTA 6 DE LA SEMANA 🔥\n\n¿Cuál es tu favorito? 👇 Te leemos\n"
             f"Síguenos para más 👉 @gtaviceclips6\n\n{pipeline.HASHTAGS} #top5 #recopilacion")
    tg.enviar_video(salida, texto + f"\n\n— Recopilación semanal · {nombres}", f"top{fecha.replace('-', '')}")
    with open(pipeline.LISTA, "a", encoding="utf-8") as f:
        f.write(json.dumps(dict(id=f"top{fecha.replace('-', '')}", archivo=salida.name, url=f"top:{fecha}",
                                streamer="Varios", titulo=f"TOP {len(top)} momentos de GTA 6 de la semana",
                                texto=texto, vistas=0, fecha=datetime.datetime.utcnow().isoformat(timespec="minutes")),
                           ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
