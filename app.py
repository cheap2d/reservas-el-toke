from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import requests
import os
from datetime import datetime, timedelta

app = Flask(__name__)

# Credenciales API de Bookeo
BOOKEO_API_KEY = "AJ9CL4R7WK7YT7NXCTENX415663YHCYT17E53FE901F"
BOOKEO_SECRET_KEY = "Hv8pW1kCjHmi3dhQe2jl1RTYL1TMsebb"
BOOKEO_API_URL = "https://api.bookeo.com/v2/availability"  # Endpoint de disponibilidad

# Diccionario de salas con sus IDs en Bookeo
SALAS = {
    "Sala A": "41566UKFAJM17E54036652_JXTLMHYU",
    "Sala B": "41566UKFAJM17E54036652_NFNHNNJE",
    "Sala C": "41566UKFAJM17E54036652_FKPWTENX",
    "Sala D": "41566UKFAJM17E54036652_TAHYRHYL"
}


def obtener_disponibilidad(sala_id, fecha):
    """Consulta la API de Bookeo para obtener la disponibilidad de una sala en una fecha específica."""
    params = {
        "apiKey": BOOKEO_API_KEY,
        "secretKey": BOOKEO_SECRET_KEY,
        "productId": sala_id,
        "startTime": fecha.isoformat(),  # Formato de fecha ISO 8601
        "endTime": (fecha + timedelta(days=1)).isoformat(),
    }
    response = requests.get(BOOKEO_API_URL, params=params)
    
    if response.status_code == 200:
        data = response.json()
        horarios = [slot["startTime"] for slot in data.get("availability", [])]
        return horarios
    else:
        return []  # Si hay error, devolver lista vacía


@app.route("/webhook", methods=["POST"])
def whatsapp_webhook():
    """Maneja los mensajes entrantes de WhatsApp y responde con disponibilidad de salas."""
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()
    
    if "disponibilidad" in incoming_msg:
        fecha_consulta = datetime.now()  # Obtener la fecha actual
        mensaje_respuesta = "📅 *Disponibilidad de salas para hoy:*\n"
        
        for nombre_sala, sala_id in SALAS.items():
            horarios = obtener_disponibilidad(sala_id, fecha_consulta)
            if horarios:
                horarios_format = "\n".join([datetime.fromisoformat(h).strftime('%H:%M') for h in horarios])
                mensaje_respuesta += f"✔ {nombre_sala}:\n{horarios_format}\n\n"
            else:
                mensaje_respuesta += f"❌ {nombre_sala}: No disponible\n\n"
        
        msg.body(mensaje_respuesta)
    else:
        msg.body("No entendí tu mensaje. Escribe 'Disponibilidad' para ver los horarios.")
    
    return str(resp)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
