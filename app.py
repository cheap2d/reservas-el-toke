import requests
from flask import Flask, request

app = Flask(__name__)

# Credenciales de Bookeo
BOOKEO_API_URL = "https://api.bookeo.com/v2/availability"
BOOKEO_APP_ID = "K7YT7NXCTENX"  # Application ID
BOOKEO_SECRET_KEY = "TU_SECRET_KEY"  # Asegúrate de agregar el Secret Key correcto
BOOKEO_API_KEY = "AJ9CL4R7WK7YT7NXCTENX415663YHCYT17E53FE901F"  # API Key real

@app.route("/", methods=["GET"])
def home():
    return "Flask app is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_message = request.form.get("Body")  # Mensaje recibido

    if "disponibilidad" in incoming_message.lower():
        availability = consultar_disponibilidad()
        return f"""
        <Response>
            <Message>
                {availability}
            </Message>
        </Response>
        """

    response_message = f"Hola, recibimos tu mensaje: {incoming_message}"
    return f"""
    <Response>
        <Message>
            {response_message}
        </Message>
    </Response>
    """

def consultar_disponibilidad():
    headers = {
        "Authorization": f"Basic {BOOKEO_APP_ID}:{BOOKEO_SECRET_KEY}"
    }
    params = {
        "apiKey": BOOKEO_API_KEY,  # API Key real
        "startTime": "2025-02-09T09:00:00",  # Cambia la fecha si es necesario
        "endTime": "2025-02-09T18:00:00",
        "productId": "ID_DE_LA_SALA"  # Debes reemplazarlo con un ID válido
    }
    try:
        response = requests.get(BOOKEO_API_URL, headers=headers, params=params)
        print(f"Respuesta de Bookeo: {response.text}")  # Log para depuración
        if response.status_code == 200:
            data = response.json()
            return f"Salas disponibles: {data}" if data else "No hay salas disponibles."
        else:
            return f"Error en Bookeo: {response.status_code} - {response.text}"
    except Exception as e:
        return f"Hubo un error al conectar con Bookeo: {str(e)}"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

