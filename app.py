import os
import requests
import base64
from flask import Flask, redirect, request, jsonify
from urllib.parse import urlencode
from dotenv import load_dotenv

# Cargar variables desde un archivo .env si existe (útil para desarrollo local)
load_dotenv()

app = Flask(__name__)

# --- CONFIGURACIÓN ---
CLIENT_ID = os.environ.get("CANVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CANVA_CLIENT_SECRET")

# En Render, RENDER_EXTERNAL_URL se genera automáticamente. 
# Si estás local, usa http://localhost:5000
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://canvas-api-eqd4.onrender.com")
REDIRECT_URI = f"{BASE_URL}/oauth/callback"

# 1. RUTA HEALTH CHECK (Esencial para que Canva valide tu integración)
@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Canva API Integration</title>
        <style>
            body {
                font-family: 'Inter', system-ui, -apple-system, sans-serif;
                background: #0f172a;
                color: white;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                margin: 0;
                text-align: center;
            }
            .container {
                background: rgba(30, 41, 59, 0.7);
                backdrop-filter: blur(10px);
                padding: 3rem;
                border-radius: 24px;
                box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                max-width: 600px;
                border: 1px solid rgba(255, 255, 255, 0.1);
            }
            img {
                width: 100%;
                max-width: 400px;
                border-radius: 16px;
                margin-bottom: 2rem;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            }
            h1 {
                font-size: 2.5rem;
                margin-bottom: 1rem;
                background: linear-gradient(to right, #818cf8, #c084fc);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
            }
            p {
                color: #94a3b8;
                font-size: 1.1rem;
                margin-bottom: 2rem;
            }
            .btn {
                background: linear-gradient(to right, #6366f1, #a855f7);
                color: white;
                padding: 1rem 2rem;
                border-radius: 12px;
                text-decoration: none;
                font-weight: 600;
                transition: transform 0.2s, box-shadow 0.2s;
                display: inline-block;
            }
            .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 10px 20px rgba(99, 102, 241, 0.4);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <img src="/static/banner.png" alt="Canva Integration Banner">
            <h1>Canva API Active</h1>
            <p>La integración con Python y Canva está funcionando correctamente.</p>
            <a href="/login" class="btn">Conectar con Canva</a>
        </div>
    </body>
    </html>
    """

# 2. RUTA DE LOGIN (Inicia el flujo)
@app.route('/login')
def login():
    # Definimos los permisos que queremos pedir
    scopes = [
        "design:read", 
        "design:content:write", 
        "asset:read", 
        "asset:write", 
        "profile:read"
    ]
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(scopes)
    }
    
    # Redirigimos al usuario a la pantalla de autorización de Canva
    canva_auth_url = f"https://www.canva.com/api/oauth/authorize?{urlencode(params)}"
    return redirect(canva_auth_url)

# 3. RUTA DE CALLBACK (Donde Canva regresa con el código)
@app.route('/oauth/callback')
def callback():
    code = request.args.get('code')
    error = request.args.get('error')

    if error:
        return f"Error devuelto por Canva: {error}", 400
    if not code:
        return "No se recibió código de autorización", 400

    # Intercambio del CODE por el TOKEN
    token_url = "https://api.canva.com/rest/v1/oauth/token"
    
    # Codificar credenciales en Base64 para el header Authorization
    creds = f"{CLIENT_ID}:{CLIENT_SECRET}"
    creds_b64 = base64.b64encode(creds.encode()).decode()

    headers = {
        "Authorization": f"Basic {creds_b64}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    try:
        response = requests.post(token_url, headers=headers, data=data)
        response.raise_for_status() # Lanza error si la petición falla
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        
        # GUARDAMOS EL TOKEN EN UNA VARIABLE GLOBAL PARA SIMPLIFICAR ESTE EJEMPLO
        # (En producción, esto iría a una base de datos)
        global LATEST_TOKEN
        LATEST_TOKEN = access_token
        
        return f"""
        <h1>¡Conexión Exitosa con Canva!</h1>
        <p>Token obtenido correctamente.</p>
        <hr>
        <h3>Subir una imagen a tu cuenta:</h3>
        <form action="/upload" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept="image/*" required>
            <button type="submit">Subir a Canva</button>
        </form>
        <br>
        <a href="/">Volver al inicio</a>
        """
    except requests.exceptions.RequestException as e:
        error_msg = f"Error al conectar con Canva: {str(e)}"
        if 'response' in locals() and response is not None:
            error_msg += f" - {response.text}"
        return error_msg, 500

# --- NUEVA FUNCIONALIDAD: SUBIR IMÁGENES ---

LATEST_TOKEN = None

@app.route('/upload', methods=['POST'])
def upload_image():
    global LATEST_TOKEN
    if not LATEST_TOKEN:
        return "Primero debes <a href='/login'>iniciar sesión</a> para obtener un token.", 401

    if 'file' not in request.files:
        return "No se seleccionó ningún archivo", 400
    
    file = request.files['file']
    if file.filename == '':
        return "Nombre de archivo vacío", 400

    # Metadatos requeridos por la API de Canva
    import json
    # El nombre debe estar en Base64 según la doc de Canva
    name_b64 = base64.b64encode(file.filename.encode()).decode()
    
    metadata = {
        "name_base64": name_b64,
        "mime_type": file.mimetype or "image/jpeg"
    }

    upload_url = "https://api.canva.com/rest/v1/asset-uploads"
    
    headers = {
        "Authorization": f"Bearer {LATEST_TOKEN}",
        "Asset-Upload-Metadata": json.dumps(metadata),
        "Content-Type": "application/octet-stream"
    }

    try:
        # Leemos el contenido del archivo subido
        file_content = file.read()
        
        response = requests.post(upload_url, headers=headers, data=file_content)
        response.raise_for_status()
        
        res_data = response.json()
        return f"""
        <h2>¡Imagen subida con éxito!</h2>
        <p>ID del Asset: {res_data.get('job', {}).get('id') or res_data.get('id')}</p>
        <pre>{json.dumps(res_data, indent=4)}</pre>
        <br>
        <a href="/oauth/callback">Subir otra</a>
        """

    except Exception as e:
        error_info = ""
        if 'response' in locals():
            error_info = response.text
        return f"Error al subir: {str(e)} <br> Detalle: {error_info}", 500

if __name__ == '__main__':
    # Esto es para correrlo localmente
    app.run(host='0.0.0.0', port=5000, debug=True)