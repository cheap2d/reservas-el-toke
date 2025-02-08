from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import datetime
import re

app = Flask(__name__)

# Credenciales de Bookeo
BOOKEO_API_KEY = "AJ9CL4R7WK7YT7NXCTENX415663YHCYT17E53FE901F"
BOOKEO_SECRET_KEY = "Hv8pW1kCjHmi3dhQe2jl1RTYL1TMsebb"
BOOKEO_BASE_URL = "https://api.bookeo.com/v2"

# IDs de las salas
SALAS = {
    "Sala A": "41566UKFAJM17E54036652_JXTLMHYU",
    "Sala B": "41566UKFAJM17E54036652_NFNHNNJE",
    "Sala C": "41566UKFAJM17E54036652_FKPWTENX",
    "Sala D": "41566UKFAJM17E54036652_TAHYRHYL",
}

def obtener_horarios_disponibles(duracion=None):
    """Consulta horarios disponibles en Bookeo con la duración específica."""
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
            "peopleNumbers": [{"peopleCategoryId": "Cadults", "number": 1}]
        }
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code in (200, 201):
            try:
                data = response.json()
                slots = data.get("data", [])
                if slots:
                    horarios = []
                    for slot in slots:
                        start = slot["startTime"][11:16]  # Extrae HH:MM de inicio
                        end = slot["endTime"][11:16]      # Extrae HH:MM de fin
                        duracion_slot = int(end[:2]) - int(start[:2])  # Duración en horas
                        
                        # Si se especificó duración, filtrar solo los que coincidan
                        if duracion is None or duracion_slot == duracion:
                            horarios.append(f"🕒 {start} - {end}")

                    if horarios:
                        disponibilidad.append(f"*{sala}:*\n" + "\n".join(horarios))
                    else:
                        disponibilidad.append(f"*{sala}:* No hay horarios disponibles para {duracion} horas.")
                else:
                    disponibilidad.append(f"*{sala}:* No hay horarios disponibles.")
            except Exception as e:
                disponibilidad.append(f"*{sala}:* Error al procesar la respuesta: {str(e)}")
        else:
            error_msg = response.text
            disponibilidad.append(f"*{sala}:* Error {response.status_code} - {error_msg}")

    return "\n\n".join(disponibilidad)

@app.route("/webhook", methods=["POST"])
def webhook():
    """Maneja mensajes de WhatsApp y responde con disponibilidad y horarios."""
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    # Buscar duración en el mensaje (opcional)
    match = re.search(r'\b(\d+)\s*horas?\b', incoming_msg)
    duracion = int(match.group(1)) if match else None

    if "disponibilidad" in incoming_msg:
        horarios = obtener_horarios_disponibles(duracion)
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
    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
