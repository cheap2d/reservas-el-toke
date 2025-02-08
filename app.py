from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests

app = Flask(__name__)

# Reemplaza con tus claves reales de Bookeo
BOOKEO_API_KEY = "AJ9CL4R7WK7YT7NXCTENX415663YHCYT17E53FE901F"
BOOKEO_SECRET_KEY = "Hv8pW1kCjHmi3dhQe2jl1RTYL1TMsebb"

def get_bookeo_availability():
    """Obtiene la disponibilidad de salas desde la API de Bookeo."""
    url = f"https://api.bookeo.com/v2/settings/products?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    
    try:
        response = requests.get(url)
        data = response.json()

        if "data" in data:
            salas = data["data"]
            disponibilidad = "📅 Disponibilidad de salas:\n"

            for sala in salas:
                nombre = sala["name"]
                disponibilidad += f"✔ {nombre}\n"

            return disponibilidad
        else:
            return "❌ No se pudo obtener la disponibilidad."

    except Exception as e:
        return f"⚠ Error al consultar Bookeo: {str(e)}"

@app.route("/webhook", methods=["POST"])
def webhook():
    """Responde a mensajes de WhatsApp usando Twilio."""
    incoming_msg = request.values.get("Body", "").lower()
    resp = MessagingResponse()
    msg = resp.message()

    if "disponibilidad" in incoming_msg:
        disponibilidad = get_bookeo_availability()
        msg.body(disponibilidad)
    else:
        msg.body("No entendí tu mensaje. Escribe 'disponibilidad' para ver las salas.")

    return str(resp)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
