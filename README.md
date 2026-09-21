# Nova: asistente virtual de Marketing Digital y Redes Sociales

**Ingeniería del Conocimiento, TP N° 2 (1° Proyecto: Asistente Virtual)**
Universidad del Aconcagua, Licenciatura en Informática y Desarrollo de Software

Asistente por voz para community managers y emprendedores. Amplía el código base de la cátedra con tres áreas: **planificación de contenido**, **diseño gráfico básico** y **gestión de comunidades**.

## Instalación

```bash
pip install -r requirements.txt
python main.py            # modo voz (micrófono)
python main.py --texto    # modo texto, para probar sin micrófono
python interfaz.py        # interfaz gráfica (o doble clic en iniciar_interfaz.bat)
```

## Interfaz gráfica

`interfaz.py` (tkinter, viene con Python: no necesita librerías extra) reúne todo en una ventana con cuatro secciones:

| Sección | Qué hace |
|---|---|
| **Asistente** | Chat con Nova: se le escribe o se le habla con el botón *Hablar*. Usa el mismo motor de pedidos que `main.py`, así que entiende los mismos comandos. Incluye atajos y el botón *Voz activada/silenciada* para que solo escriba. |
| **Calendario** | Formulario para agendar (acepta `25/09/2026`, `mañana`, `18:30`), tabla de publicaciones, marcar como publicada y eliminar. |
| **Diseño** | Placas y carruseles con selector de formato y paleta, vista previa, botón para abrir la carpeta `piezas/` y publicar en Instagram. |
| **Comunidad** | Lista de comentarios clasificados (quejas primero), respuesta sugerida editable y envío con un clic. |

Las piezas creadas desde el chat también aparecen en la vista previa de *Diseño*. Los módulos originales siguen funcionando por consola.

> En Windows, si falla `PyAudio`, instalar con `pip install pipwin && pipwin install pyaudio`.
> Para que la voz sea en español hay que tener instalada una voz en español
> (Configuración → Hora e idioma → Voz). El asistente la detecta sola.

## Estructura (modular)

| Archivo | Responsabilidad | Librerías |
|---|---|---|
| `main.py` | Centro de pedidos: interpreta el comando y deriva al módulo | — |
| `voz.py` | Texto a voz y voz a texto (`hablar`, `transformar_audio_texto`) | pyttsx3, speech_recognition |
| `funciones_base.py` | Funciones originales: hora, fecha, Wikipedia, YouTube, chistes, acciones | pywhatkit, yfinance, pyjokes, wikipedia, webbrowser, datetime |
| `calendario.py` | Calendario de publicaciones y recordatorios hablados | sqlite3, schedule, threading |
| `diseno.py` | Generación de placas y carruseles | Pillow |
| `comunidad.py` | Base de conocimiento para comentarios + Meta Graph API | requests |
| `config.py` | Datos del usuario, paleta de marca y credenciales | os |

## Comandos de ejemplo

**Planificación de contenido**
- "Agendá un post en Instagram para el jueves a las 18 sobre la promo de invierno"
- "Programá una historia para mañana" (el asistente pregunta los datos que faltan)
- "¿Qué tengo para publicar hoy / mañana / esta semana?"
- "Marcá como publicada la 3" · "Borrá la publicación 2"
- El asistente avisa por voz 15 minutos antes de cada publicación.

**Diseño gráfico**
- "Creá una placa que diga Liquidación de invierno 30% OFF"
- "Creá una placa vibrante para historia que diga Nuevo drop"
- "Armá un carrusel de 5 slides claro" (te pide el texto de cada slide)
- Paletas: `oscuro`, `claro`, `vibrante` · Formatos: post 4:5, `cuadrado`, `historia` 9:16
- Las piezas se guardan en la carpeta `piezas/`.

**Gestión de comunidad**
- "Leé los comentarios": los lee y clasifica (queja, precio, envíos, pagos, stock, elogio)
- "Resumen de comentarios": cantidad por tipo y alerta de quejas
- "Respondé los comentarios": prioriza las quejas y sugiere una respuesta; se confirma con *sí*, *no* u *otra* (para dictarla)
- "Publicá la última pieza"

**Del código base:** "¿Qué hora es?", "¿Qué día es?", "Buscá en Wikipedia marketing digital", "Buscá en internet tendencias de Instagram", "Reproducir lo-fi", "Contame un chiste", "Precio de la acción de Meta", "Abrí Canva", "Ayuda", "Adiós".

## Base de conocimiento (comunidad)

Los comentarios se clasifican con un sistema basado en reglas (`BASE_CONOCIMIENTO` en `comunidad.py`):
cada regla tiene palabras clave, una **intención**, una **prioridad** y una **respuesta sugerida**.
El motor de inferencia evalúa las reglas en orden (las quejas primero) y aplica la primera que coincide.
Si ninguna coincide, se usa una regla general. Para ampliar el conocimiento solo hay que agregar reglas.

## Conexión real con Instagram (opcional)

Sin credenciales, el módulo de comunidad funciona en **modo demo** con comentarios simulados.
Para usar una cuenta real:

1. La cuenta de Instagram debe ser **profesional** y estar vinculada a una página de Facebook.
2. Crear una app en [Meta for Developers](https://developers.facebook.com) y generar un token con los permisos
   `instagram_basic`, `instagram_manage_comments` e `instagram_content_publish`.
3. Definir las variables de entorno:
   ```bash
   set META_ACCESS_TOKEN=...      # (Linux/Mac: export)
   set IG_USER_ID=...
   set URL_PUBLICA_PIEZAS=https://...   # solo para publicar: Instagram exige imágenes en una URL pública
   ```
