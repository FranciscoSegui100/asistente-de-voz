"""
Diseño gráfico básico: genera placas y carruseles listos para redes con Pillow.
"""
import datetime
import os
import re
import webbrowser

from PIL import Image, ImageDraw, ImageFont

import config
from voz import hablar, normalizar

FORMATOS = {
    "post": (1080, 1350),       # 4:5, formato recomendado para feed
    "cuadrado": (1080, 1080),
    "historia": (1080, 1920),   # 9:16, historias y portadas de reels
}
MARGEN = 110

_FUENTES_NEGRITA = ["arialbd.ttf", "C:/Windows/Fonts/arialbd.ttf", "Arial Bold.ttf",
                    "/Library/Fonts/Arial Bold.ttf", "DejaVuSans-Bold.ttf",
                    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
_FUENTES_NORMAL = ["arial.ttf", "C:/Windows/Fonts/arial.ttf", "Arial.ttf",
                   "/Library/Fonts/Arial.ttf", "DejaVuSans.ttf",
                   "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def _fuente(tamanio, negrita=True):
    for ruta in (_FUENTES_NEGRITA if negrita else _FUENTES_NORMAL):
        try:
            return ImageFont.truetype(ruta, tamanio)
        except OSError:
            continue
    return ImageFont.load_default(size=tamanio)


def _partir_lineas(draw, texto, fuente, ancho_max):
    """Divide el texto en líneas que entren en el ancho disponible."""
    lineas, actual = [], ""
    for palabra in texto.split():
        prueba = f"{actual} {palabra}".strip()
        if draw.textlength(prueba, font=fuente) <= ancho_max:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def _texto_centrado(draw, texto, caja, color, tamanio_max=130, tamanio_min=40):
    """Escribe el texto centrado en la caja (x0, y0, x1, y1), achicando la letra si no entra."""
    x0, y0, x1, y1 = caja
    tamanio = tamanio_max
    while True:
        fuente = _fuente(tamanio)
        lineas = _partir_lineas(draw, texto, fuente, x1 - x0)
        alto_linea = int(tamanio * 1.2)
        alto_total = alto_linea * len(lineas)
        entra_ancho = all(draw.textlength(l, font=fuente) <= (x1 - x0) for l in lineas)
        if (alto_total <= (y1 - y0) and entra_ancho) or tamanio <= tamanio_min:
            break
        tamanio -= 6
    y = y0 + ((y1 - y0) - alto_total) // 2
    for linea in lineas:
        ancho = draw.textlength(linea, font=fuente)
        draw.text((x0 + ((x1 - x0) - ancho) // 2, y), linea, font=fuente, fill=color)
        y += alto_linea


def _lienzo(formato, paleta):
    ancho, alto = FORMATOS.get(formato, FORMATOS["post"])
    colores = config.PALETAS.get(paleta, config.PALETAS[config.PALETA_POR_DEFECTO])
    img = Image.new("RGB", (ancho, alto), colores["fondo"])
    draw = ImageDraw.Draw(img)
    # Detalles de marca: barra de acento y firma
    draw.rectangle([MARGEN, MARGEN, MARGEN + 120, MARGEN + 14], fill=colores["acento"])
    draw.text((MARGEN, alto - MARGEN - 20), config.NOMBRE_MARCA, font=_fuente(34, False), fill=colores["texto"])
    return img, draw, colores


def _guardar(img, prefijo):
    os.makedirs(config.CARPETA_PIEZAS, exist_ok=True)
    marca_tiempo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    ruta = os.path.join(config.CARPETA_PIEZAS, f"{prefijo}_{marca_tiempo}.png")
    img.save(ruta)
    return ruta


def crear_placa(texto, formato="post", paleta=None, subtitulo=None):
    """Genera una placa con un mensaje principal (y subtítulo opcional). Devuelve la ruta."""
    img, draw, colores = _lienzo(formato, paleta or config.PALETA_POR_DEFECTO)
    ancho, alto = img.size
    fondo_texto = alto - MARGEN * 2 - (200 if subtitulo else 80)
    _texto_centrado(draw, texto.upper(), (MARGEN, MARGEN + 80, ancho - MARGEN, fondo_texto), colores["texto"])
    if subtitulo:
        _texto_centrado(draw, subtitulo, (MARGEN, fondo_texto + 10, ancho - MARGEN, fondo_texto + 130),
                        colores["acento"], tamanio_max=52, tamanio_min=30)
    return _guardar(img, "placa")


def crear_carrusel(textos, paleta=None, formato="post"):
    """Genera una slide por texto, con numeración e indicador para deslizar. Devuelve las rutas."""
    rutas, total = [], len(textos)
    marca_tiempo = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, texto in enumerate(textos, start=1):
        img, draw, colores = _lienzo(formato, paleta or config.PALETA_POR_DEFECTO)
        ancho, alto = img.size
        tamanio = 130 if i == 1 else 90          # la portada lleva letra más grande
        _texto_centrado(draw, texto.upper() if i == 1 else texto,
                        (MARGEN, MARGEN + 80, ancho - MARGEN, alto - MARGEN - 120),
                        colores["texto"], tamanio_max=tamanio)
        fuente_chica = _fuente(34)
        num = f"{i}/{total}"
        draw.text((ancho - MARGEN - draw.textlength(num, font=fuente_chica), MARGEN - 10),
                  num, font=fuente_chica, fill=colores["acento"])
        if i < total:
            indicacion = "Deslizá →"
            draw.text((ancho - MARGEN - draw.textlength(indicacion, font=fuente_chica), alto - MARGEN - 20),
                      indicacion, font=fuente_chica, fill=colores["acento"])
        os.makedirs(config.CARPETA_PIEZAS, exist_ok=True)
        ruta = os.path.join(config.CARPETA_PIEZAS, f"carrusel_{marca_tiempo}_{i}.png")
        img.save(ruta)
        rutas.append(ruta)
    return rutas


mostrar_pieza = None   # la interfaz gráfica lo define para mostrar la pieza en su vista previa


def abrir_imagen(ruta):
    if mostrar_pieza:
        return mostrar_pieza(ruta)
    webbrowser.open("file://" + os.path.abspath(ruta).replace("\\", "/"))


def ultima_pieza():
    if not os.path.isdir(config.CARPETA_PIEZAS):
        return None
    archivos = [os.path.join(config.CARPETA_PIEZAS, f) for f in os.listdir(config.CARPETA_PIEZAS)
                if f.endswith(".png")]
    return max(archivos, key=os.path.getmtime) if archivos else None


# ---------------- Comandos de voz ----------------
def _detectar_opciones(t):
    paleta = next((p for p in config.PALETAS if p in t), None)
    formato = "historia" if "historia" in t else "cuadrado" if "cuadrad" in t else "post"
    return paleta, formato


def comando_placa(pedido, preguntar):
    t = normalizar(pedido)
    paleta, formato = _detectar_opciones(t)
    m = re.search(r"\b(?:que diga|con el texto|que dice)\s+(.+)$", pedido, re.IGNORECASE)
    texto = m.group(1).strip() if m else preguntar("¿Qué texto querés que lleve la placa?", crudo=True)
    if not texto:
        return hablar("No recibí el texto, probemos de nuevo")
    subtitulo = None
    resp = preguntar("¿Le agrego un subtítulo? Decime el texto o no", crudo=True)
    if resp and normalizar(resp) not in ("no", "no gracias", "sin subtitulo"):
        subtitulo = resp
    ruta = crear_placa(texto, formato, paleta, subtitulo)
    hablar(f"Listo, creé la placa y la guardé en la carpeta piezas")
    abrir_imagen(ruta)


def comando_carrusel(pedido, preguntar):
    t = normalizar(pedido)
    paleta, formato = _detectar_opciones(t)
    m = re.search(r"\b(\d{1,2})\s*(?:slides|diapositivas|placas|imagenes|laminas)", t)
    cantidad = int(m.group(1)) if m else None
    while not cantidad:
        resp = preguntar("¿Cuántas slides querés? Entre 2 y 10")
        m = re.search(r"\b(\d{1,2})\b", resp)
        cantidad = int(m.group(1)) if m else {"dos": 2, "tres": 3, "cuatro": 4, "cinco": 5}.get(resp)
    cantidad = max(2, min(cantidad, 10))

    textos = []
    for i in range(1, cantidad + 1):
        etiqueta = "la portada" if i == 1 else f"la slide {i}"
        texto = preguntar(f"Decime el texto de {etiqueta}", crudo=True)
        while not texto:
            texto = preguntar(f"No te escuché. Repetime el texto de {etiqueta}", crudo=True)
        textos.append(texto)

    rutas = crear_carrusel(textos, paleta, formato)
    hablar(f"Listo, armé el carrusel de {cantidad} slides en la carpeta piezas")
    abrir_imagen(rutas[0])
