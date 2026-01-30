import os
import requests
import base64
import json
import time
import io
from flask import Flask, redirect, request, jsonify, render_template
from urllib.parse import urlencode
from dotenv import load_dotenv
from rembg import remove
from PIL import Image

# Cargar variables desde un archivo .env si existe
load_dotenv()

app = Flask(__name__)

# --- CONFIGURACIÓN ---
CLIENT_ID = os.environ.get("CANVA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("CANVA_CLIENT_SECRET")
CANVA_TEMPLATE_ID = "DAG_56I6Cnk"
SHOPIFY_FOLDER_NAME = "Shopify Raw Photos"

# En Render, RENDER_EXTERNAL_URL se genera automáticamente. 
BASE_URL = os.environ.get("RENDER_EXTERNAL_URL", "https://canvas-api-eqd4.onrender.com")
REDIRECT_URI = f"{BASE_URL}/oauth/callback"

LATEST_TOKEN = None

# --- RUTAS DE AUTENTICACIÓN ---

@app.route('/')
def home():
    return render_template('index.html', token_ready=(LATEST_TOKEN is not None))

@app.route('/login')
def login():
    scopes = [
        "design:read", 
        "design:content:write", 
        "asset:read", 
        "asset:write", 
        "profile:read",
        "folder:read",
        "folder:write"
    ]
    
    params = {
        "response_type": "code",
        "client_id": CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": " ".join(scopes)
    }
    
    canva_auth_url = f"https://www.canva.com/api/oauth/authorize?{urlencode(params)}"
    return redirect(canva_auth_url)

@app.route('/oauth/callback')
def callback():
    global LATEST_TOKEN
    code = request.args.get('code')
    if not code:
        return "No se recibió código de autorización", 400

    token_url = "https://api.canva.com/rest/v1/oauth/token"
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
        response.raise_for_status()
        token_data = response.json()
        LATEST_TOKEN = token_data.get("access_token")
        
        return f"""
        <h1>¡Conexión Exitosa con Canva!</h1>
        <p>Token obtenido correctamente.</p>
        <hr>
        <h3>Procesar Imagen de Shopify:</h3>
        <form action="/process-product" method="post">
            <input type="text" name="url" placeholder="URL de imagen de Shopify" required style="width: 400px;">
            <button type="submit">Procesar y Crear Burbuja</button>
        </form>
        <br>
        <a href="/">Volver al inicio</a>
        """
    except Exception as e:
        return f"Error al conectar con Canva: {str(e)}", 500

# --- LÓGICA DE PROCESAMIENTO ---

def poll_job(url, token, timeout=60, interval=2):
    """Realiza polling a un job de Canva hasta que termine o falle."""
    headers = {"Authorization": f"Bearer {token}"}
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        
        # El estado puede estar en 'job.status' o 'status' directamente
        job_info = data.get("job", {})
        status = job_info.get("status") or data.get("status")
        
        if status == "success":
            return data
        elif status == "failed":
            error_detail = job_info.get("error") or data.get("error")
            raise Exception(f"El trabajo en Canva falló: {error_detail}")
        
        time.sleep(interval)
    
    raise Exception(f"Tiempo de espera agotado (timeout) en: {url}")

def get_or_create_folder(name, token):
    """Busca o crea una carpeta en Canva con el nombre dado."""
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Buscar carpeta existente
    list_url = "https://api.canva.com/rest/v1/folders"
    # Nota: Canva API v1 puede requerir paginación o filtros. 
    # Aquí buscamos en los resultados iniciales por simplicidad.
    try:
        res = requests.get(list_url, headers=headers)
        if res.status_code == 200:
            folders = res.json().get("items", [])
            for f in folders:
                if f.get("name") == name:
                    return f.get("id")
    except:
        pass

    # 2. Si no existe, crearla
    create_url = "https://api.canva.com/rest/v1/folders"
    try:
        res = requests.post(create_url, headers=headers, json={"name": name})
        if res.status_code == 201 or res.status_code == 200:
            return res.json().get("id")
    except:
        pass
    
    return None

@app.route('/process-product', methods=['POST'])
def process_product():
    global LATEST_TOKEN
    
    # Soporta tanto form-data (del HTML) como JSON (API)
    shopify_url = request.form.get('url') or request.json.get('url') if request.is_json else None
    token = request.headers.get('Authorization', '').replace('Bearer ', '') or LATEST_TOKEN

    if not shopify_url:
        return jsonify({"error": "Falta el parámetro 'url'"}), 400
    if not token:
        return jsonify({"error": "No hay token de acceso. Inicie sesión primero."}), 401

    try:
        # --- PASO 1: Descarga y Limpieza (rembg) ---
        print(f"Descargando imagen: {shopify_url}")
        img_res = requests.get(shopify_url)
        img_res.raise_for_status()
        
        input_bytes = img_res.content
        print("Eliminando fondo con rembg...")
        output_bytes = remove(input_bytes)
        
        # --- PASO 2: Subida a Canva (Asset API) ---
        print("Subiendo asset a Canva...")
        filename = f"product_{int(time.time())}.png"
        name_b64 = base64.b64encode(filename.encode()).decode()
        
        metadata = {
            "name_base64": name_b64,
            "mime_type": "image/png"
        }
        
        # Obtener folder_id para guardar la imagen en la carpeta correcta
        folder_id = get_or_create_folder(SHOPIFY_FOLDER_NAME, token)
        if folder_id:
            metadata["parent_id"] = folder_id
            print(f"Subiendo a la carpeta: {SHOPIFY_FOLDER_NAME} (ID: {folder_id})")
        
        upload_url = "https://api.canva.com/rest/v1/asset-uploads"
        headers = {
            "Authorization": f"Bearer {token}",
            "Asset-Upload-Metadata": json.dumps(metadata),
            "Content-Type": "application/octet-stream"
        }
        
        up_res = requests.post(upload_url, headers=headers, data=output_bytes)
        up_res.raise_for_status()
        up_data = up_res.json()
        
        job_id = up_data.get("job", {}).get("id")
        if job_id:
            # Polling para asegurar que el asset esté listo
            poll_res = poll_job(f"https://api.canva.com/rest/v1/asset-uploads/{job_id}", token)
            asset_id = poll_res.get("item", {}).get("id") or poll_res.get("asset", {}).get("id")
        else:
            asset_id = up_data.get("id")

        if not asset_id:
            raise Exception("No se pudo obtener el ID del asset subido.")

        # --- PASO 3: Inyección en Plantilla (Autofill API) ---
        print(f"Ejecutando Autofill con plantilla {CANVA_TEMPLATE_ID}...")
        autofill_url = "https://api.canva.com/rest/v1/autofills"
        autofill_body = {
            "brand_template_id": CANVA_TEMPLATE_ID,
            "title": f"Burbuja {filename}",
            "data": {
                "ProductImage": { # Label del campo en la plantilla
                    "type": "image",
                    "asset_id": asset_id
                }
            }
        }
        
        af_res = requests.post(autofill_url, headers={"Authorization": f"Bearer {token}"}, json=autofill_body)
        af_res.raise_for_status()
        af_job_id = af_res.json().get("job", {}).get("id")
        
        # Polling Autofill
        af_result = poll_job(f"https://api.canva.com/rest/v1/autofills/{af_job_id}", token)
        design_id = af_result.get("design", {}).get("id")
        print(f"Diseño creado: {design_id}")

        # --- PASO 4: Exportación (Export API) ---
        print("Iniciando exportación a PNG...")
        export_url = "https://api.canva.com/rest/v1/exports"
        export_body = {
            "design_id": design_id,
            "format": {
                "type": "png",
                "lossless": True
            }
        }
        
        ex_res = requests.post(export_url, headers={"Authorization": f"Bearer {token}"}, json=export_body)
        ex_res.raise_for_status()
        ex_job_id = ex_res.json().get("job", {}).get("id")
        
        # Polling Export
        ex_result = poll_job(f"https://api.canva.com/rest/v1/exports/{ex_job_id}", token)
        urls = ex_result.get("export", {}).get("urls", [])
        
        final_download_url = urls[0] if urls else None
        print(f"Exportación completa: {final_download_url}")

        if request.is_json:
            return jsonify({
                "status": "success",
                "download_url": final_download_url,
                "design_id": design_id,
                "asset_id": asset_id
            })
        else:
            return f"""
            <h2>¡Proceso Completado!</h2>
            <p>Imagen procesada con éxito.</p>
            <p><b>ID del Diseño:</b> {design_id}</p>
            <a href="{final_download_url}" target="_blank" style="padding: 10px; background: #00c4cc; color: white; text-decoration: none; border-radius: 5px;">Descargar PNG Final</a>
            <br><br>
            <a href="/oauth/callback">Procesar otra</a>
            """

    except Exception as e:
        error_msg = f"Error en la cadena de procesamiento: {str(e)}"
        print(error_msg)
        return jsonify({"status": "error", "message": error_msg}), 500

@app.route('/test-719244')
def test_local_image():
    global LATEST_TOKEN
    token = LATEST_TOKEN
    if not token:
        return "Primero debes <a href='/login'>iniciar sesión</a>.", 401

    try:
        # --- PASO 1: Carga Local y Limpieza ---
        file_path = os.path.join(os.getcwd(), '719244.jpg')
        if not os.path.exists(file_path):
            return "No se encontró el archivo 719244.jpg en el servidor.", 404
            
        with open(file_path, 'rb') as f:
            input_bytes = f.read()
            
        print("Eliminando fondo con rembg (Prueba Local)...")
        output_bytes = remove(input_bytes)
        
        # --- PASO 2: Subida a Canva ---
        filename = "test_719244.png"
        name_b64 = base64.b64encode(filename.encode()).decode()
        
        metadata = {
            "name_base64": name_b64,
            "mime_type": "image/png"
        }
        
        folder_id = get_or_create_folder(SHOPIFY_FOLDER_NAME, token)
        if folder_id:
            metadata["parent_id"] = folder_id
        
        headers = {
            "Authorization": f"Bearer {token}",
            "Asset-Upload-Metadata": json.dumps(metadata),
            "Content-Type": "application/octet-stream"
        }
        
        print("Subiendo asset de prueba a Canva...")
        up_res = requests.post("https://api.canva.com/rest/v1/asset-uploads", headers=headers, data=output_bytes)
        up_res.raise_for_status()
        
        up_data = up_res.json()
        job_id = up_data.get("job", {}).get("id")
        if job_id:
            poll_res = poll_job(f"https://api.canva.com/rest/v1/asset-uploads/{job_id}", token)
            asset_id = poll_res.get("item", {}).get("id") or poll_res.get("asset", {}).get("id")
        else:
            asset_id = up_data.get("id")

        # --- PASO 3: Autofill ---
        print(f"Autofill con plantilla {CANVA_TEMPLATE_ID}...")
        autofill_body = {
            "brand_template_id": CANVA_TEMPLATE_ID,
            "title": "Test Burbuja 719244",
            "data": {
                "ProductImage": {"type": "image", "asset_id": asset_id}
            }
        }
        af_res = requests.post("https://api.canva.com/rest/v1/autofills", 
                               headers={"Authorization": f"Bearer {token}"}, json=autofill_body)
        af_res.raise_for_status()
        af_job_id = af_res.json().get("job", {}).get("id")
        
        af_result = poll_job(f"https://api.canva.com/rest/v1/autofills/{af_job_id}", token)
        design_id = af_result.get("design", {}).get("id")

        # --- PASO 4: Exportación ---
        print("Exportando...")
        export_body = {
            "design_id": design_id,
            "format": {"type": "png", "lossless": True}
        }
        ex_res = requests.post("https://api.canva.com/rest/v1/exports", 
                               headers={"Authorization": f"Bearer {token}"}, json=export_body)
        ex_res.raise_for_status()
        ex_job_id = ex_res.json().get("job", {}).get("id")
        
        ex_result = poll_job(f"https://api.canva.com/rest/v1/exports/{ex_job_id}", token)
        final_url = ex_result.get("export", {}).get("urls", [])[0]

        return f"""
        <h2>¡Prueba 719244 Exitosa!</h2>
        <p>Imagen local procesada y guardada en {SHOPIFY_FOLDER_NAME}</p>
        <a href="{final_url}" target="_blank" style="padding: 10px; background: #7D2AE8; color: white; text-decoration: none; border-radius: 5px;">Ver Resultado Final</a>
        <br><br>
        <a href="/">Volver</a>
        """

    except Exception as e:
        return f"Error en la prueba: {str(e)}", 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
