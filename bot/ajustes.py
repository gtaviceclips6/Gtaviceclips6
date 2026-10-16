# GTA VICE CLIPS 6 - ajustes que cambias desde el menú de Telegram (se guardan en ajustes.json)
import os, json, pathlib

RUTA = pathlib.Path("ajustes.json")
DEF = {"pausa": False, "nota_minima": None, "virales": True, "tendencias": True, "noticias_gta": True}


def leer():
    try:
        return {**DEF, **json.loads(RUTA.read_text(encoding="utf-8"))}
    except Exception:
        return dict(DEF)


def guardar(**cambios):
    a = leer(); a.update(cambios)
    RUTA.write_text(json.dumps(a, ensure_ascii=False, indent=1), encoding="utf-8")
    return a


def en_pausa():
    """Las pasadas automaticas no hacen nada si has pausado el bot (lo que pidas a mano sí se hace)."""
    return leer()["pausa"] and os.environ.get("GITHUB_EVENT_NAME") == "schedule"
