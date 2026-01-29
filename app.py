import os
import requests
import base64
from flask import Flask, redirect, request, jsonify
from urllib.parse import urlencode

app = Flask(__name__)

# --- CONFIGURACIÓN ---
# En Render, estas variables las pondrás en la sección "Environment"
CLIENT_ID = os.environ.get("CANVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CANVA_CLIENT_SECRET")

# IMPORTANTE: En Render, tu URL será algo como https://mi-app.onrender.com
# Asegúrate de que esta URL coincida con la que pusiste en el Developer Portal de Canva
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "http://localhost:5000")
REDIRECT_URI = f"{BASE_URL}/oauth/callback"

# 1. RUTA HEALTH CHECK (Esencial para que Canva valide tu integración)
@app.route('/')
def home():
    return "Status: OK. La integración con Canva está activa."

# 2. RUTA DE LOGIN (Inicia el flujo)
@app.route('/login')
def login():
    # Definimos los permisos que queremos pedir
    scopes = ["design:read", "design:meta:read", "profile:read"]
    
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
        
        # AQUÍ ES DONDE GUARDARÍAS EL TOKEN EN TU BASE DE DATOS
        
        return jsonify({
            "mensaje": "¡Conexión Exitosa con Python!",
            "access_token_preview": access_token[:10] + "...", # Solo mostramos un pedazo por seguridad
            "data_completa": token_data
        })

    except requests.exceptions.RequestException as e:
        return f"Error al conectar con Canva: {str(e)} - {response.text}", 500

if __name__ == '__main__':
    # Esto es para correrlo localmente
    app.run(host='0.0.0.0', port=5000, debug=True)