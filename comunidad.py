"""
Gestión de comunidad: lectura, clasificación y respuesta de comentarios en Instagram
mediante la Meta Graph API, y publicación de piezas.

Incluye una BASE DE CONOCIMIENTO de reglas (palabras clave -> intención -> respuesta)
que clasifica cada comentario y sugiere una respuesta.
Sin credenciales configuradas, funciona en MODO DEMO con comentarios simulados.
"""
import os

import requests

import config
from voz import es_afirmativo, hablar, normalizar

URL_GRAPH = f"https://graph.facebook.com/{config.GRAPH_API_VERSION}"

# ---------------- Base de conocimiento ----------------
# Cada regla: intención, palabras clave que la disparan, prioridad y respuesta sugerida.
# Se evalúan en orden: las quejas van primero para que no se confundan con otras.
BASE_CONOCIMIENTO = [
    {"intencion": "queja", "prioridad": "alta",
     "palabras": ["no llego", "nunca llego", "roto", "rota", "no funciona", "estafa", "reclamo",
                  "devolucion", "mala calidad", "no me respond", "trucho", "decepcion"],
     "respuesta": "Hola, lamentamos mucho lo que pasó. Escribinos por mensaje directo con tu número de pedido y lo resolvemos hoy mismo."},
    {"intencion": "precio", "prioridad": "media",
     "palabras": ["precio", "cuanto sale", "cuanto esta", "cuanto cuesta", "valor", "costo", "$"],
     "respuesta": "¡Hola! Te enviamos el precio y las promos vigentes por mensaje directo 📩"},
    {"intencion": "envios", "prioridad": "media",
     "palabras": ["envio", "envian", "mandan", "llega a", "hacen envios", "demora", "correo", "retiro"],
     "respuesta": "¡Sí! Hacemos envíos a todo el país 🚚 Te pasamos los costos y tiempos por mensaje directo."},
    {"intencion": "medios_de_pago", "prioridad": "media",
     "palabras": ["cuotas", "tarjeta", "transferencia", "mercado pago", "efectivo", "medios de pago"],
     "respuesta": "Aceptamos tarjetas, transferencia y Mercado Pago 💳 ¡Consultanos por las cuotas sin interés!"},
    {"intencion": "stock", "prioridad": "media",
     "palabras": ["stock", "hay en", "tienen en", "disponible", "talle", "quedan"],
     "respuesta": "¡Hola! Escribinos por mensaje directo y te confirmamos la disponibilidad al instante 🙌"},
    {"intencion": "elogio", "prioridad": "baja",
     "palabras": ["hermoso", "hermosa", "me encanta", "genial", "excelente", "lindo", "linda",
                  "increible", "buenisimo", "divino", "recomiendo", "gracias", "❤", "😍", "🔥"],
     "respuesta": "¡Muchas gracias por el amor! 🧡 Nos alegra un montón que te guste."},
]
REGLA_GENERAL = {"intencion": "consulta_general", "prioridad": "media",
                 "respuesta": "¡Hola! Gracias por escribirnos, te respondemos por mensaje directo 😊"}

NOMBRES_INTENCION = {"queja": "queja", "precio": "consulta de precio", "envios": "consulta de envíos",
                     "medios_de_pago": "consulta de medios de pago", "stock": "consulta de stock",
                     "elogio": "elogio", "consulta_general": "consulta general"}


def clasificar_comentario(texto):
    """Motor de inferencia simple: devuelve la primera regla cuya palabra clave aparece."""
    t = normalizar(texto)
    for regla in BASE_CONOCIMIENTO:
        if any(normalizar(p) in t for p in regla["palabras"]):
            return regla
    return REGLA_GENERAL


# ---------------- Modo demo ----------------
_COMENTARIOS_DEMO = [
    {"id": "d1", "usuario": "sofi.mza", "texto": "Hola! cuánto sale el modelo negro?", "respondido": False},
    {"id": "d2", "usuario": "juanpe_92", "texto": "Hice un pedido hace 10 días y nunca llegó", "respondido": False},
    {"id": "d3", "usuario": "cami.ruiz", "texto": "Me encantan!! 😍", "respondido": False},
    {"id": "d4", "usuario": "martin.gz", "texto": "Hacen envíos a San Rafael?", "respondido": False},
    {"id": "d5", "usuario": "lu.fernandez", "texto": "Se puede pagar en cuotas con tarjeta?", "respondido": False},
    {"id": "d6", "usuario": "nico_ok", "texto": "Tienen stock en color blanco?", "respondido": False},
]


# ---------------- Meta Graph API ----------------
def _get(ruta, **params):
    params["access_token"] = config.META_ACCESS_TOKEN
    r = requests.get(f"{URL_GRAPH}/{ruta}", params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def _post(ruta, **datos):
    datos["access_token"] = config.META_ACCESS_TOKEN
    r = requests.post(f"{URL_GRAPH}/{ruta}", data=datos, timeout=30)
    r.raise_for_status()
    return r.json()


def obtener_comentarios(cantidad_posts=3, limite=10):
    """Devuelve los comentarios recientes sin responder de las últimas publicaciones."""
    if config.MODO_DEMO_REDES:
        return [c for c in _COMENTARIOS_DEMO if not c["respondido"]][:limite]

    comentarios = []
    medios = _get(f"{config.IG_USER_ID}/media", fields="id,caption", limit=cantidad_posts)["data"]
    for medio in medios:
        datos = _get(f"{medio['id']}/comments", fields="id,text,username,replies{id}", limit=limite)
        for c in datos.get("data", []):
            if not c.get("replies"):  # solo los que todavía no tienen respuesta
                comentarios.append({"id": c["id"], "usuario": c.get("username", "alguien"),
                                    "texto": c.get("text", ""), "respondido": False})
    return comentarios[:limite]


def responder_comentario(id_comentario, mensaje):
    if config.MODO_DEMO_REDES:
        for c in _COMENTARIOS_DEMO:
            if c["id"] == id_comentario:
                c["respondido"] = True
        print(f"   [DEMO] Respuesta a {id_comentario}: {mensaje}")
        return True
    _post(f"{id_comentario}/replies", message=mensaje)
    return True


def publicar_en_instagram(ruta_imagen, descripcion):
    """Publica una imagen. Instagram exige que la imagen esté en una URL pública."""
    if config.MODO_DEMO_REDES:
        print(f"   [DEMO] Publicado {os.path.basename(ruta_imagen)} con: {descripcion}")
        return "demo"
    if not config.URL_PUBLICA_PIEZAS:
        raise RuntimeError("Falta configurar URL_PUBLICA_PIEZAS")
    url = f"{config.URL_PUBLICA_PIEZAS.rstrip('/')}/{os.path.basename(ruta_imagen)}"
    contenedor = _post(f"{config.IG_USER_ID}/media", image_url=url, caption=descripcion)
    return _post(f"{config.IG_USER_ID}/media_publish", creation_id=contenedor["id"])["id"]


# ---------------- Comandos de voz ----------------
def _aviso_demo():
    if config.MODO_DEMO_REDES:
        hablar("Estoy en modo demostración, con comentarios de ejemplo")


def _obtener_o_avisar():
    try:
        return obtener_comentarios()
    except Exception as e:
        print(e)
        hablar("No pude conectarme con Instagram. Revisá el token de acceso")
        return None


def comando_leer_comentarios():
    _aviso_demo()
    comentarios = _obtener_o_avisar()
    if comentarios is None:
        return
    if not comentarios:
        return hablar("No tenés comentarios sin responder. ¡Bien ahí!")
    hablar(f"Tenés {len(comentarios)} comentarios sin responder")
    for c in comentarios:
        regla = clasificar_comentario(c["texto"])
        urgente = ". Es urgente" if regla["prioridad"] == "alta" else ""
        hablar(f"{c['usuario']} dice: {c['texto']}. Lo clasifiqué como {NOMBRES_INTENCION[regla['intencion']]}{urgente}")


def comando_resumen_comentarios():
    _aviso_demo()
    comentarios = _obtener_o_avisar()
    if not comentarios:
        return hablar("No hay comentarios pendientes para resumir") if comentarios == [] else None
    conteo = {}
    for c in comentarios:
        intencion = clasificar_comentario(c["texto"])["intencion"]
        conteo[intencion] = conteo.get(intencion, 0) + 1
    detalle = ", ".join(f"{n} de {NOMBRES_INTENCION[i]}" for i, n in conteo.items())
    hablar(f"Resumen de {len(comentarios)} comentarios: {detalle}")
    if conteo.get("queja"):
        n = conteo["queja"]
        hablar(f"Ojo: hay {n} {'queja' if n == 1 else 'quejas'} que conviene atender primero")


def comando_responder_comentarios(preguntar):
    """Recorre los comentarios (quejas primero) y confirma cada respuesta por voz."""
    _aviso_demo()
    comentarios = _obtener_o_avisar()
    if comentarios is None:
        return
    if not comentarios:
        return hablar("No hay comentarios para responder")
    orden = {"alta": 0, "media": 1, "baja": 2}
    comentarios.sort(key=lambda c: orden[clasificar_comentario(c["texto"])["prioridad"]])

    respondidos = 0
    for c in comentarios:
        regla = clasificar_comentario(c["texto"])
        resp = preguntar(f"{c['usuario']} dice: {c['texto']}. Sugiero responder: {regla['respuesta']} "
                         f"¿Lo envío? Decí sí, no, u otra para dictar tu respuesta. O salir para terminar")
        if "salir" in resp or "terminar" in resp:
            break
        mensaje = None
        if "otra" in resp:
            mensaje = preguntar("Dictame la respuesta", crudo=True)
        elif es_afirmativo(resp):
            mensaje = regla["respuesta"]
        if mensaje:
            try:
                responder_comentario(c["id"], mensaje)
                respondidos += 1
            except Exception as e:
                print(e)
                hablar("No pude enviar esa respuesta")
    hablar(f"Listo, respondí {respondidos} comentarios")


def comando_publicar(preguntar, ruta_imagen):
    _aviso_demo()
    if not ruta_imagen:
        return hablar("No encontré ninguna pieza creada. Primero creá una placa")
    descripcion = preguntar("¿Qué descripción le pongo a la publicación?", crudo=True)
    if not es_afirmativo(preguntar(f"Voy a publicar la última pieza con la descripción: {descripcion}. ¿Confirmás?")):
        return hablar("No publiqué nada")
    try:
        publicar_en_instagram(ruta_imagen, descripcion)
        hablar("¡Publicado en Instagram!")
    except Exception as e:
        print(e)
        hablar("No pude publicar. Revisá la configuración de la API")
