import requests
import json
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Credenciales de Bookeo
API_KEY = "AJ9CL4R7WK7YT7NXCTENX415663YHCYT17E53FE901F"
SECRET_KEY = "Hv8pW1kCjHmi3dhQe2jl1RTYL1TMsebb"

# Identificadores de salas en Bookeo
PRODUCT_IDS = {
    "Sala A": "41566UKFAJM17E54036652_JXTLMHYU",
    "Sala B": "41566UKFAJM17E54036652_NFNHNNJE",
    "Sala C": "41566UKFAJM17E54036652_FKPWTENX",
    "Sala D": "41566UKFAJM17E54036652_TAHYRHYL"
}

BASE_URL = "https://api.bookeo.com/v2"

def get_availability(product_id):
    """Consulta la disponibilidad de una sala en Bookeo."""
    url = f"{BASE_URL}/availability/slots"
    params = {
        "apiKey": API_KEY,
        "secretKey": SECRET_KEY,
        "startTime": "2025-02-09T00:00:00Z",
        "endTime": "2025-02-09T23:59:59Z",
        "productId": product_id
    }
    
    response = requests.get(url, params=params)

    if response.status_code == 200:
        data = response.json()
        slots = data.get("data", [])
        if slots:
            return "\n".join([f"- {slot['startTime']} hasta {slot['endTime']}" for slot in slots])
        else:
            return "No hay disponibilidad en este momento."
    else:
        return f"Error en Bookeo {response.status_code}: {response.text}"


@app.route('/whatsapp', methods=['POST'])
def whatsapp_reply():
    """Responde mensajes en WhatsApp con la disponibilidad de las salas."""
    incoming_msg = request.values.get('Body', '').strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    if incoming_msg == "disponibilidad":
        disponibilidad_texto = "📅 *Disponibilidad de salas:*\n\n"
        for sala, product_id in PRODUCT_IDS.items():
            disponibilidad_texto += f"*{sala}:*\n{get_availability(product_id)}\n\n"
        
        msg.body(disponibilidad_texto)
    else:
        msg.body("Envíame *Disponibilidad* para ver los horarios disponibles.")

    return str(resp)


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)
