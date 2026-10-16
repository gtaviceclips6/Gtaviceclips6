# GTA VICE CLIPS 6 - lee config.json (marca, juego, hashtags, filtro). Si falta algo, usa estos valores.
import json, pathlib

_DEF = {
    "marca": {"nombre": "GTA VICE CLIPS 6", "handle": "@gtaviceclips6",
              "descripcion_ia": "una cuenta de fans (no oficial) de GTA 6 para España",
              "color_principal": [255, 46, 136], "color_secundario": [0, 229, 255], "color_resaltado": [255, 230, 0]},
    "juego": {"nombre_twitch": "Grand Theft Auto VI", "nombre_corto": "GTA 6", "lanzamiento": "2026-11-19",
              "palabras_clave": r"gta ?(6|vi\b)|grand theft auto (6|vi\b)|leonida|vice ?city|lucia|jason duval",
              "vocabulario": "GTA 6, Vice City, Leonida, Lucia, Jason, Rockstar, chat, stream, directo, Twitch",
              "busqueda_noticias": '"GTA 6" OR "GTA VI"'},
    "idioma": {"codigo": "es", "pais": "ES"},
    "hashtags": {"base": "#gta6 #gtavi #gta6españa #humor #clipsgraciosos #viral #parati #fyp #twitch #streamer #vicecity",
                 "escenas": "#gta6 #gtavi #gta6españa #vicecity #leonida #graficos #gaming #viral #parati #fyp",
                 "noticias": "#gta6 #gtavi #gta6españa #noticiasgta6 #rockstargames #vicecity #ultimahora"},
    "filtro": {"nota_minima": 7, "min_vistas_sin_ia": 50, "min_segundos": 8, "max_segundos": 45},
    "horarios": {"zona": "Europe/Madrid", "clips": ["12:00", "18:00"]},
}


def _mezclar(a, b):
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _mezclar(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


def cargar():
    p = pathlib.Path("config.json")
    datos = {}
    if p.exists():
        try:
            datos = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print("config.json con errores, uso valores por defecto:", e)
    return _mezclar(_DEF, datos)


CFG = cargar()
MARCA, JUEGO, HASHTAGS, FILTRO, HORARIOS = CFG["marca"], CFG["juego"], CFG["hashtags"], CFG["filtro"], CFG["horarios"]
