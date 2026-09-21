"""
Configuración central del asistente de marketing digital.
Modificar acá los datos del usuario, la marca y las credenciales.
"""
import os

# ---------------- Usuario / asistente ----------------
NOMBRE_USUARIO = "GRANCEL"
NOMBRE_ASISTENTE = "Nova"

# Modo texto: escribir comandos por teclado en vez de hablar
# (útil para probar sin micrófono). Se activa con:  python main.py --texto
MODO_TEXTO = os.getenv("MODO_TEXTO", "0") == "1"

# ---------------- Voz ----------------
VOZ_ACTIVA = True            # False: el asistente solo escribe, sin hablar (la interfaz lo cambia con un botón)
IDIOMA_RECONOCIMIENTO = "es-AR"
VELOCIDAD_VOZ = 350          # palabras por minuto aprox.
VOLUMEN_VOZ = 1.0            # 0.0 a 1.0
# Voz del código base (Windows). Si no existe, se busca automáticamente una voz en español.
ID_VOZ_ESPANOL = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech\Voices\Tokens\TTS_MS_ES-ES_HELENA_11.0"

# ---------------- Rutas ----------------
CARPETA_BASE = os.path.dirname(os.path.abspath(__file__))
RUTA_DB = os.path.join(CARPETA_BASE, "datos", "calendario.db")
CARPETA_PIEZAS = os.path.join(CARPETA_BASE, "piezas")

# ---------------- Identidad de marca (diseño) ----------------
NOMBRE_MARCA = "@mimarca"
PALETAS = {
    "oscuro":   {"fondo": (18, 18, 18),    "texto": (255, 255, 255), "acento": (255, 107, 53)},
    "claro":    {"fondo": (245, 241, 234), "texto": (25, 25, 25),    "acento": (214, 64, 69)},
    "vibrante": {"fondo": (76, 44, 214),   "texto": (255, 255, 255), "acento": (255, 214, 10)},
}
PALETA_POR_DEFECTO = "oscuro"

# ---------------- Meta Graph API (Instagram / Facebook) ----------------
# Si no hay token, el módulo de comunidad funciona en MODO DEMO con datos simulados.
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN", "")
IG_USER_ID = os.getenv("IG_USER_ID", "")
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v21.0")
# Instagram solo publica imágenes desde una URL pública: carpeta donde se suben las piezas
URL_PUBLICA_PIEZAS = os.getenv("URL_PUBLICA_PIEZAS", "")

MODO_DEMO_REDES = not (META_ACCESS_TOKEN and IG_USER_ID)

# ---------------- Excusas para no trabajar ("dame una excusa") ----------------
# Agregá, cambiá o borrá las que quieras: Nova elige una al azar sin repetir la anterior.
EXCUSAS = [
    "Decí que el algoritmo de Instagram cambió otra vez y estás esperando a ver cómo se acomoda antes de publicar nada.",
    "Decí que estás haciendo investigación de mercado profunda. Es decir, mirando reels con mucha atención.",
    "Decí que se te cayó el wifi, y que casualmente se fue justo cuando ibas a empezar.",
    "Decí que tu creatividad está en modo de carga y que apurarla arruina el contenido.",
    "Decí que la paleta de colores no te terminó de convencer y que no querés lanzar nada a medias.",
    "Decí que estás en una reunión estratégica con vos mismo, y que va para largo.",
    "Decí que el calendario de contenidos está tan perfecto que tocarlo hoy sería un error.",
    "Decí que estás analizando métricas. Nadie te va a pedir ver la planilla.",
    "Decí que tu compu se puso a instalar actualizaciones y que Windows dijo que no la apagues.",
    "Decí que estás haciendo un descanso de pantalla para cuidar la vista, es salud ocupacional.",
    "Decí que estás esperando la aprobación del cliente. Técnicamente es cierto: esperás la tuya.",
    "Decí que hoy se te dio por pensar en grande y que las ideas grandes no se rinden un lunes.",
]

# ---------------- Recordatorios ----------------
MINUTOS_AVISO_PREVIO = 15    # avisar X minutos antes de cada publicación
