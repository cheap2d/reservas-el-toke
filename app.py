import requests
from flask import Flask, request

app = Flask(__name__)

BOOKEO_API_URL = "https://signin.bookeo.com/?authappid=K7YT7NXCTENX&permissions=..."
BOOKEO_APP_ID = "K7YT7NXCTENX"  # Reemplaza con tu Application ID
BOOKEO_SECRET_KEY = "Hv8pW1kCjHmi3dhQe2jl1RTYL1TMsebb"  # Reemplaza con tu Secret Key

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
        "startTime": "2025-02-09T09:00:00",  # Cambia por la fecha y hora deseadas
        "endTime": "2025-02-09T18:00:00",    # Cambia por la fecha y hora deseadas
        "productId": "ID_DE_LA_SALA"         # Reemplaza con el ID del recurso
    }
    try:
        response = requests.get(BOOKEO_API_URL, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            return f"Salas disponibles: {data}"  # Ajusta según los datos devueltos
        else:
            return "Error al consultar disponibilidad en Bookeo."
    except Exception as e:
        return f"Hubo un error: {str(e)}"

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
