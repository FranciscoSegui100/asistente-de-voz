"""
Asistente virtual de Marketing Digital y Redes Sociales
Ingeniería del Conocimiento - TP N° 2 - Universidad del Aconcagua

Uso:
    python main.py            -> modo voz (micrófono)
    python main.py --texto    -> modo texto (escribir los comandos)
"""
import sys

import config

if "--texto" in sys.argv:
    config.MODO_TEXTO = True

import calendario
import comunidad
import diseno
import funciones_base as base
from voz import hablar, normalizar, preguntar, transformar_audio_texto

AYUDA = """Puedo ayudarte con:
Calendario: agendá un post en Instagram para el jueves a las 18 sobre la promo. Qué tengo para publicar hoy, mañana o esta semana. Marcá como publicada la 3. Borrá la publicación 2.
Diseño: creá una placa que diga 20 por ciento off. Armá un carrusel de 3 slides. Podés pedir paleta clara, oscura o vibrante, y formato historia o cuadrado.
Comunidad: leé los comentarios. Resumen de comentarios. Respondé los comentarios. Publicá la última pieza.
Además: qué hora es, qué día es, buscá en Wikipedia, buscá en internet, reproducir una canción, contame un chiste, dame una excusa para no trabajar, precio de la acción de Apple, abrir Instagram. Para terminar, decí adiós."""

SITIOS = {
    "instagram": "https://www.instagram.com",
    "facebook": "https://www.facebook.com",
    "tiktok": "https://www.tiktok.com",
    "canva": "https://www.canva.com",
    "meta business": "https://business.facebook.com",
    "youtube": "https://www.youtube.com",
    "navegador": "https://www.google.com.ar",
}


def contiene(texto, *frases):
    return any(f in texto for f in frases)


def procesar_pedido(pedido_original):
    """Interpreta un pedido y ejecuta la acción. Devuelve False si hay que terminar."""
    pedido = normalizar(pedido_original)
    if not pedido or pedido == "sigo esperando":
        return True

    # ---- Salida y ayuda ----
    if contiene(pedido, "adios", "chau", "salir del asistente", "apagate"):
        hablar(f"Nos vemos {config.NOMBRE_USUARIO}, ¡éxitos con el contenido!")
        return False
    if contiene(pedido, "ayuda", "que podes hacer", "que sabes hacer", "comandos"):
        hablar(AYUDA)

    # ---- Comunidad ----
    elif "comentario" in pedido:
        if contiene(pedido, "respond", "contesta"):
            comunidad.comando_responder_comentarios(preguntar)
        elif contiene(pedido, "resumen", "resumi", "analiza"):
            comunidad.comando_resumen_comentarios()
        else:
            comunidad.comando_leer_comentarios()
    elif contiene(pedido, "publica la ultima", "publicar la ultima", "subi la ultima", "publica la pieza"):
        comunidad.comando_publicar(preguntar, diseno.ultima_pieza())

    # ---- Diseño ----
    elif "carrusel" in pedido and contiene(pedido, "crea", "arma", "hace", "genera", "diseña", "disena"):
        diseno.comando_carrusel(pedido_original, preguntar)
    elif contiene(pedido, "placa", "flyer", "pieza grafica", "imagen para") and \
            contiene(pedido, "crea", "arma", "hace", "genera", "disena", "diseña"):
        diseno.comando_placa(pedido_original, preguntar)
    elif contiene(pedido, "abri la ultima pieza", "mostrame la ultima pieza"):
        ruta = diseno.ultima_pieza()
        diseno.abrir_imagen(ruta) if ruta else hablar("Todavía no creaste ninguna pieza")

    # ---- Calendario ----
    elif contiene(pedido, "agenda", "programa", "planifica") and \
            contiene(pedido, "post", "publicacion", "historia", "reel", "carrusel", "video"):
        calendario.comando_agendar(pedido_original, preguntar)
    elif contiene(pedido, "que tengo para publicar", "que hay para publicar", "calendario",
                  "publicaciones de", "publicaciones para", "que publico"):
        calendario.comando_listar(pedido)
    elif contiene(pedido, "marca como publicad", "marcar como publicad", "ya publique"):
        calendario.comando_marcar_publicada(pedido)
    elif contiene(pedido, "borra la publicacion", "elimina la publicacion", "borrar la publicacion"):
        calendario.comando_eliminar(pedido, preguntar)

    # ---- Funciones del código base ----
    elif contiene(pedido, "que dia es", "que fecha es"):
        base.pedir_dia()
    elif contiene(pedido, "que hora es", "que hora"):
        base.pedir_hora()
    elif contiene(pedido, "busca en wikipedia", "buscar en wikipedia"):
        base.buscar_wikipedia(pedido.split("wikipedia", 1)[1])
    elif contiene(pedido, "busca en internet", "buscar en internet", "busca en google"):
        base.buscar_internet(pedido.split("internet" if "internet" in pedido else "google", 1)[1])
    elif pedido.startswith("reproduci") or "reproducir" in pedido:
        base.reproducir_youtube(pedido.split(" ", 1)[1] if " " in pedido else "")
    elif "chiste" in pedido:
        base.contar_chiste()
    elif contiene(pedido, "excusa", "no trabajar", "zafar"):
        base.dar_excusa()
    elif contiene(pedido, "precio de la accion"):
        base.precio_accion(pedido.split("accion", 1)[1].replace("de ", "", 1))
    elif pedido.startswith("abri") or pedido.startswith("abrir"):
        sitio = next((s for s in SITIOS if s in pedido), None)
        base.abrir_sitio(sitio, SITIOS[sitio]) if sitio else hablar("No conozco ese sitio")

    else:
        hablar("No entendí el pedido. Decí ayuda para escuchar lo que puedo hacer")
    return True


def centro_pedido():
    base.saludo_inicial()
    calendario.iniciar_recordatorios()
    continuar = True
    while continuar:
        pedido = transformar_audio_texto()
        try:
            continuar = procesar_pedido(pedido)
        except Exception as e:
            # Un error en una función no debe cerrar el asistente
            print(f"Error: {e}")
            hablar("Ups, algo salió mal con ese pedido. Probemos de nuevo")


if __name__ == "__main__":
    centro_pedido()
