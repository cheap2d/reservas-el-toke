from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import datetime

app = Flask(__name__)

# Credenciales de Bookeo
BOOKEO_API_KEY = "AJ9CL4R7WK7YT7NXCTENX415663YHCYT17E53FE901F"
BOOKEO_SECRET_KEY = "Hv8pW1kCjHmi3dhQe2jl1RTYL1TMsebb"
BOOKEO_BASE_URL = "https://api.bookeo.com/v2"

# IDs de las salas (productos)
SALAS = {
    "Sala A": "41566UKFAJM17E54036652_JXTLMHYU",
    "Sala B": "41566UKFAJM17E54036652_NFNHNNJE",
    "Sala C": "41566UKFAJM17E54036652_FKPWTENX",
    "Sala D": "41566UKFAJM17E54036652_TAHYRHYL",
}

def obtener_horarios_disponibles():
    """
    Consulta los horarios disponibles en Bookeo para todas las salas.
    En caso de error, se incluye el código y el contenido de la respuesta para depuración.
    """
    # Usamos la fecha UTC para el día actual
    hoy = datetime.datetime.utcnow().strftime("%Y-%m-%dT00:00:00Z")
    fin_dia = datetime.datetime.utcnow().strftime("%Y-%m-%dT23:59:59Z")
    headers = {"Content-Type": "application/json"}
    disponibilidad = []

    for sala, sala_id in SALAS.items():
        url = f"{BOOKEO_BASE_URL}/availability/matchingslots?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
        payload = {
            "productId": sala_id,
            "startTime": hoy,
            "endTime": fin_dia,
            "peopleNumbers": [
                {"peopleCategoryId": "Cadults", "number": 1}
            ]
        }

        try:
            response = requests.post(url, headers=headers, json=payload)
            # Para depuración: imprime la URL, el payload y la respuesta en la consola
            print(f"Consulta para {sala}:\n  URL: {url}\n  Payload: {payload}\n  Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                slots = data.get("data", [])
                if slots:
                    horarios = [f"🕒 {slot['startTime'][11:16]} - {slot['endTime'][11:16]}" for slot in slots]
                    disponibilidad.append(f"*{sala}:*\n" + "\n".join(horarios))
                else:
                    disponibilidad.append(f"*{sala}:* No hay horarios disponibles.")
            else:
                disponibilidad.append(f"*{sala}:* Error {response.status_code} - {response.text}")
        except Exception as e:
            disponibilidad.append(f"*{sala}:* Exception: {str(e)}")

    return "\n\n".join(disponibilidad)

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Recibe mensajes de WhatsApp (vía Twilio) y responde con la disponibilidad de salas y horarios.
    Si el mensaje recibido contiene la palabra "disponibilidad" (en cualquier combinación de mayúsculas/minúsculas),
    se consulta Bookeo y se responde con los horarios disponibles; en otro caso se muestra un mensaje de ayuda.
    """
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()
    
    if "disponibilidad" in incoming_msg:
        horarios = obtener_horarios_disponibles()
        respuesta = (
            "📅 *Disponibilidad de salas:*\n"
            "✔ Sala A\n"
            "✔ Sala B\n"
            "✔ Sala C\n"
            "✔ Sala D\n\n"
            "📆 *Horarios disponibles para hoy:*\n"
            f"{horarios}"
        )
    else:
        respuesta = "No entendí tu mensaje. Escribe 'Disponibilidad' para ver las salas y horarios."
    
    msg.body(respuesta)
    # Devolvemos el TwiML con Content-Type 'text/xml'
    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
