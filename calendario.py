"""
Planificación de contenido: calendario de publicaciones (sqlite3)
y recordatorios hablados en segundo plano (schedule + threading).
"""
import contextlib
import datetime
import os
import re
import sqlite3
import threading
import time

import schedule

import config
from voz import es_afirmativo, hablar, normalizar

DIAS = {"lunes": 0, "martes": 1, "miercoles": 2, "jueves": 3,
        "viernes": 4, "sabado": 5, "domingo": 6}
MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7,
         "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
REDES = ["instagram", "facebook", "tiktok", "linkedin", "youtube", "twitter"]
TIPOS = ["historia", "reel", "carrusel", "video", "post"]
NOMBRES_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


# ---------------- Base de datos ----------------
@contextlib.contextmanager
def _conectar():
    """Abre la base, confirma los cambios al salir y siempre cierra la conexión."""
    os.makedirs(os.path.dirname(config.RUTA_DB), exist_ok=True)
    con = sqlite3.connect(config.RUTA_DB)
    con.row_factory = sqlite3.Row
    con.execute("""
        CREATE TABLE IF NOT EXISTS publicaciones (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            red       TEXT NOT NULL,
            tipo      TEXT NOT NULL,
            fecha     TEXT NOT NULL,          -- 'YYYY-MM-DD HH:MM'
            tema      TEXT NOT NULL,
            estado    TEXT DEFAULT 'pendiente',
            avisado   INTEGER DEFAULT 0
        )""")
    try:
        with con:
            yield con
    finally:
        con.close()


# ---------------- Interpretación del lenguaje natural ----------------
def _fecha_proxima(dia, mes, hoy):
    """Próxima vez que ocurre ese día/mes (este año o el siguiente). None si la fecha no existe (31/02)."""
    for anio in (hoy.year, hoy.year + 1, hoy.year + 2):
        try:
            fecha = datetime.date(anio, mes, dia)
        except ValueError:
            continue
        if fecha >= hoy:
            return fecha
    return None


def interpretar_fecha(texto, hoy=None):
    """Convierte 'mañana', 'el jueves', '25 de septiembre' o '25/9' en una fecha."""
    t = normalizar(texto)
    hoy = hoy or datetime.date.today()

    if "pasado manana" in t:
        return hoy + datetime.timedelta(days=2)
    if re.search(r"\bmanana\b", re.sub(r"\b(?:de|por|a) la manana\b", "", t)):   # "9 de la mañana" no es "mañana"
        return hoy + datetime.timedelta(days=1)
    if re.search(r"\bhoy\b", t):
        return hoy

    m = re.search(r"\b(\d{1,2}) de (" + "|".join(MESES) + r")\b", t)
    if m:
        return _fecha_proxima(int(m.group(1)), MESES[m.group(2)], hoy)

    m = re.search(r"\b(\d{1,2})/(\d{1,2})\b", t)
    if m:
        return _fecha_proxima(int(m.group(1)), int(m.group(2)), hoy)

    for nombre, num in DIAS.items():
        if re.search(rf"\b{nombre}\b", t):
            dias_hasta = (num - hoy.weekday()) % 7 or 7   # si es hoy, la semana que viene
            return hoy + datetime.timedelta(days=dias_hasta)
    return None


def interpretar_hora(texto):
    """Convierte 'a las 18', 'a las 9 y media de la noche' o '18:30' en (hora, minuto)."""
    t = normalizar(texto)
    m = re.search(r"\b(\d{1,2}):(\d{2})\b", t)
    if m:
        hora, minuto = int(m.group(1)), int(m.group(2))
    else:
        m = re.search(r"\ba la(?:s)? (\d{1,2})(?:\s*y\s*(media|cuarto|\d{1,2}))?", t)
        if not m:
            return None
        hora = int(m.group(1))
        extra = m.group(2)
        minuto = {"media": 30, "cuarto": 15, None: 0}.get(extra, None)
        if minuto is None:
            minuto = int(extra)
    if hora < 12 and ("de la tarde" in t or "de la noche" in t):
        hora += 12
    elif hora == 12 and "de la noche" in t:
        hora = 0
    if hora > 23 or minuto > 59:
        return None
    return hora, minuto


def interpretar_publicacion(texto):
    """Extrae red, tipo, fecha, hora y tema de un pedido hablado."""
    t = normalizar(texto)
    m = re.search(r"\b(?:sobre|de tema|acerca de)\s+(.+)$", texto, re.IGNORECASE)
    tema = m.group(1).strip() if m else None
    # Red, tipo, fecha y hora se buscan antes del tema: una palabra del tema ("promo de lunes") no las confunde
    cabecera = normalizar(texto[:m.start()]) if m else t
    red = next((r for r in REDES if r in cabecera), None) or next((r for r in REDES if r in t), None)
    tipo = next((tp for tp in TIPOS if tp in cabecera), None) or next((tp for tp in TIPOS if tp in t), "post")
    fecha, hora = interpretar_fecha(cabecera), interpretar_hora(cabecera)
    if tema:
        # fecha/hora dichas después del tema ("... sobre la promo para el jueves a las 18")
        for corte in re.finditer(r"\s+(?:para el|para|el d[ií]a|a las?)\s+", tema, re.IGNORECASE):
            cola = tema[corte.start():]
            f, h = interpretar_fecha(cola), interpretar_hora(cola)
            if f or h:
                fecha, hora, tema = fecha or f, hora or h, tema[:corte.start()].strip()
                break
    return {"red": red, "tipo": tipo, "fecha": fecha, "hora": hora, "tema": tema or None}


# ---------------- Operaciones del calendario ----------------
def agregar_publicacion(red, tipo, fecha, hora, tema):
    momento = datetime.datetime.combine(fecha, datetime.time(*hora))
    with _conectar() as con:
        cur = con.execute(
            "INSERT INTO publicaciones (red, tipo, fecha, tema) VALUES (?, ?, ?, ?)",
            (red, tipo, momento.strftime("%Y-%m-%d %H:%M"), tema))
        return cur.lastrowid


def listar_publicaciones(desde, hasta, solo_pendientes=True):
    consulta = "SELECT * FROM publicaciones WHERE fecha >= ? AND fecha < ?"
    if solo_pendientes:
        consulta += " AND estado = 'pendiente'"
    with _conectar() as con:
        return con.execute(consulta + " ORDER BY fecha",
                           (desde.strftime("%Y-%m-%d %H:%M"), hasta.strftime("%Y-%m-%d %H:%M"))).fetchall()


def proxima_pendiente():
    ahora = datetime.datetime.now() - datetime.timedelta(hours=12)
    with _conectar() as con:
        return con.execute("SELECT * FROM publicaciones WHERE estado='pendiente' AND fecha >= ? "
                           "ORDER BY fecha LIMIT 1", (ahora.strftime("%Y-%m-%d %H:%M"),)).fetchone()


def cambiar_estado(id_pub, estado):
    with _conectar() as con:
        return con.execute("UPDATE publicaciones SET estado=? WHERE id=?", (estado, id_pub)).rowcount


def eliminar_publicacion(id_pub):
    with _conectar() as con:
        return con.execute("DELETE FROM publicaciones WHERE id=?", (id_pub,)).rowcount


def _describir(pub, con_dia=True):
    f = datetime.datetime.strptime(pub["fecha"], "%Y-%m-%d %H:%M")
    dia = f"el {NOMBRES_DIAS[f.weekday()]} {f.day} " if con_dia else ""
    return f"número {pub['id']}: {pub['tipo']} de {pub['red']} {dia}a las {f.strftime('%H:%M')} sobre {pub['tema']}"


# ---------------- Comandos de voz ----------------
def comando_agendar(pedido, preguntar):
    """Agenda una publicación; si falta algún dato, lo pregunta."""
    datos = interpretar_publicacion(pedido)

    while not datos["red"]:
        resp = preguntar("¿En qué red social la publico? Instagram, Facebook, TikTok o LinkedIn")
        if "cancel" in resp:
            return hablar("Listo, cancelé la carga")
        datos["red"] = next((r for r in REDES if r in resp), None)
    while not datos["fecha"]:
        resp = preguntar("¿Qué día? Podés decir mañana, el jueves o 25 de septiembre")
        if "cancel" in resp:
            return hablar("Listo, cancelé la carga")
        datos["fecha"] = interpretar_fecha(resp)
    while not datos["hora"]:
        resp = preguntar("¿A qué hora? Por ejemplo, a las 18")
        if "cancel" in resp:
            return hablar("Listo, cancelé la carga")
        datos["hora"] = interpretar_hora(resp if "las" in resp or ":" in resp else f"a las {resp}")
    if not datos["tema"]:
        datos["tema"] = preguntar("¿De qué trata la publicación?", crudo=True) or "sin tema"

    id_pub = agregar_publicacion(**datos)
    f = datos["fecha"]
    articulo = "una" if datos["tipo"] == "historia" else "un"
    hablar(f"Listo, agendé {articulo} {datos['tipo']} de {datos['red']} para el {NOMBRES_DIAS[f.weekday()]} "
           f"{f.day} a las {datos['hora'][0]}:{datos['hora'][1]:02d} sobre {datos['tema']}. "
           f"Quedó con el número {id_pub}")


def comando_listar(pedido):
    t = normalizar(pedido)
    ahora = datetime.datetime.now()
    inicio_hoy = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    if "manana" in t and "semana" not in t:
        desde, hasta, periodo = inicio_hoy + datetime.timedelta(days=1), inicio_hoy + datetime.timedelta(days=2), "mañana"
    elif "semana" in t:
        desde, hasta, periodo = inicio_hoy, inicio_hoy + datetime.timedelta(days=7), "los próximos 7 días"
    else:
        desde, hasta, periodo = inicio_hoy, inicio_hoy + datetime.timedelta(days=1), "hoy"

    pubs = listar_publicaciones(desde, hasta)
    if not pubs:
        return hablar(f"No tenés publicaciones pendientes para {periodo}")
    hablar(f"Tenés {len(pubs)} publicaciones para {periodo}")
    for p in pubs:
        hablar(_describir(p, con_dia=(periodo != "hoy" and periodo != "mañana")))


def _extraer_numero(texto):
    m = re.search(r"\b(\d+)\b", texto)
    return int(m.group(1)) if m else None


def comando_marcar_publicada(pedido):
    num = _extraer_numero(pedido)
    if num is None:
        pub = proxima_pendiente()
        if not pub:
            return hablar("No hay publicaciones pendientes")
        num = pub["id"]
    if cambiar_estado(num, "publicada"):
        hablar(f"Marqué la publicación número {num} como publicada")
    else:
        hablar(f"No encontré la publicación número {num}")


def comando_eliminar(pedido, preguntar):
    num = _extraer_numero(pedido)
    if num is None:
        return hablar("Decime el número de la publicación que querés borrar")
    if not es_afirmativo(preguntar(f"¿Confirmás que borro la publicación número {num}?")):
        return hablar("No borré nada")
    hablar("Publicación eliminada" if eliminar_publicacion(num) else f"No encontré la número {num}")


# ---------------- Recordatorios en segundo plano ----------------
def _revisar_recordatorios():
    ahora = datetime.datetime.now()
    limite = ahora + datetime.timedelta(minutes=config.MINUTOS_AVISO_PREVIO)
    with _conectar() as con:
        pubs = con.execute("SELECT * FROM publicaciones WHERE estado='pendiente' AND avisado=0 "
                           "AND fecha >= ? AND fecha <= ?",
                           ((ahora - datetime.timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M"),
                            limite.strftime("%Y-%m-%d %H:%M"))).fetchall()
        for p in pubs:
            con.execute("UPDATE publicaciones SET avisado=1 WHERE id=?", (p["id"],))
    for p in pubs:
        hablar(f"Recordatorio: se viene la publicación {_describir(p, con_dia=False)}")


def iniciar_recordatorios():
    """Lanza un hilo que revisa el calendario cada minuto."""
    schedule.every(1).minutes.do(_revisar_recordatorios)

    def bucle():
        _revisar_recordatorios()
        while True:
            schedule.run_pending()
            time.sleep(5)

    threading.Thread(target=bucle, daemon=True).start()
