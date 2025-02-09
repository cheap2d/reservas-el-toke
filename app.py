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

def obtener_horarios_apertura_cierre(fecha):
    """
    Obtiene los horarios de apertura y cierre del negocio desde Bookeo.
    """
    url = f"{BOOKEO_BASE_URL}/business/operatingHours?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    response = requests.get(url)
    if response.status_code in (200, 201):
        data = response.json()
        dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
        python_weekday = dt.weekday()
        bookeo_day = (python_weekday + 1) % 7
        for item in data.get("data", []):
            if int(item.get("dayOfWeek", -1)) == bookeo_day:
                return int(item["startTime"].split(":")[0]), int(item["endTime"].split(":")[0])
    return 10, 20  # Valores predeterminados si falla la API

def obtener_horarios_disponibles(fecha):
    """
    Obtiene los horarios disponibles filtrados dentro del horario operativo.
    """
    inicio_dia = f"{fecha}T00:00:00Z"
    fin_dia = f"{fecha}T23:59:59Z"
    headers = {"Content-Type": "application/json"}
    disponibilidad = []
    apertura, cierre = obtener_horarios_apertura_cierre(fecha)
    
    for sala, sala_id in SALAS.items():
        url = f"{BOOKEO_BASE_URL}/availability/matchingslots?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
        payload = {
            "productId": sala_id,
            "startTime": inicio_dia,
            "endTime": fin_dia,
            "peopleNumbers": [{"peopleCategoryId": "Cadults", "number": 1}]
        }
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in (200, 201):
            try:
                data = response.json()
                slots = data.get("data", [])
                horarios_disponibles = [
                    f"🕒 {slot['startTime'][11:16]} - {slot['endTime'][11:16]}"
                    for slot in slots
                    if apertura <= int(slot['startTime'][11:13]) < cierre
                ]
                if horarios_disponibles:
                    disponibilidad.append(f"*{sala}:*\n" + "\n".join(horarios_disponibles))
                else:
                    disponibilidad.append(f"*{sala}:* No hay horarios disponibles.")
            except Exception as e:
                disponibilidad.append(f"*{sala}:* Error al procesar la respuesta: {e}")
        else:
            disponibilidad.append(f"*{sala}:* Error {response.status_code} - {response.text}")
    
    return "\n\n".join(disponibilidad)

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Recibe mensajes de WhatsApp y responde con la disponibilidad de salas.
    """
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()

    if "disponibilidad" in incoming_msg:
        partes = incoming_msg.split()
        if len(partes) > 1 and partes[1].isdigit():
            fecha_consulta = f"2025-02-{partes[1].zfill(2)}"
        else:
            fecha_consulta = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        
        horarios = obtener_horarios_disponibles(fecha_consulta)
        apertura, cierre = obtener_horarios_apertura_cierre(fecha_consulta)
        respuesta = (
            f"📅 *Disponibilidad de salas para el {fecha_consulta}:* (Horarios operativos: {apertura:02d}:00 - {cierre:02d}:00)\n"
            "✔ Sala A\n"
            "✔ Sala B\n"
            "✔ Sala C\n"
            "✔ Sala D\n\n"
            "📆 *Horarios disponibles:*\n"
            f"{horarios}"
        )
    else:
        respuesta = "No entendí tu mensaje. Escribe 'Disponibilidad' seguido de un día opcional (ej. 'Disponibilidad 10') para consultar horarios."
    
    msg.body(respuesta)
    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
