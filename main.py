import os
from canvasapi import Canvas
from dotenv import load_dotenv

# Cargar variables desde el archivo .env
load_dotenv()

# Intentar cargar credenciales de varias posibles variables
# El usuario ha usado diferentes nombres en el pasado, así que probamos todos
CANVAS_API_URL = os.getenv("CANVAS_API_URL") or os.getenv("CANVA_CLIENT_ID") or os.getenv("CANVAS_REDIRECT_URI")
CANVAS_API_TOKEN = os.getenv("CANVAS_API_TOKEN") or os.getenv("CANVA_CLIENT_SECRET") or os.getenv("CANVA_REDIRECT_URI")

# Depuración (quitar en producción)
print(f"DEBUG: URL cargada: {CANVAS_API_URL}")
print(f"DEBUG: Token cargado: {'****' + CANVAS_API_TOKEN[-4:] if CANVAS_API_TOKEN and len(CANVAS_API_TOKEN) > 4 else 'No cargado'}")

if not CANVAS_API_URL or not CANVAS_API_TOKEN or "your_access_token" in CANVAS_API_TOKEN:
    print("\nError: No se han encontrado credenciales válidas.")
    print("Asegúrate de que tu archivo .env tenga lo siguiente:")
    print("CANVAS_API_URL=https://tu-url.instructure.com")
    print("CANVAS_API_TOKEN=tu-token-real")
    exit(1)

try:
    # Inicializar la API de Canvas
    print(f"Conectando a {CANVAS_API_URL}...")
    canvas = Canvas(CANVAS_API_URL, CANVAS_API_TOKEN)

    # Intentar obtener el usuario actual para validar la conexión
    user = canvas.get_user("self")
    print(f"\n¡Conexión exitosa! Bienvenido, {user.name}")

    # Listar cursos del usuario
    print("\nCursos encontrados:")
    courses = canvas.get_courses()
    
    # Intentamos listar los primeros 5 cursos para no saturar si hay muchos
    count = 0
    for course in courses:
        try:
            print(f"- {course.name} (ID: {course.id})")
            count += 1
            if count >= 10: break
        except AttributeError:
            # A veces get_courses() devuelve objetos que no tienen 'name' si no hay acceso
            continue
            
    if count == 0:
        print("No se encontraron cursos activos.")

except Exception as e:
    print(f"\nError al conectar con Canvas: {e}")
    print("Verifica que tu URL sea correcta (debe empezar con https://) y que tu Token sea válido.")