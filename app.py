import os
import requests
import base64
from flask import Flask, redirect, request, jsonify, render_template
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

# 1. RUTA HOME
@app.route('/')
def home():
    return render_template('index.html')

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