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

def obtener_horarios_apertura_cierre():
    """
    Consulta los horarios de apertura y cierre desde Bookeo.
    Se intenta obtener el primer bloque de horario disponible.
    Si ocurre algún error, se retornan valores por defecto.
    """
    url = f"{BOOKEO_BASE_URL}/business/operatingHours?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    try:
        response = requests.get(url)
        if response.status_code in (200, 201):
            data = response.json()
            if "data" in data and len(data["data"]) > 0:
                apertura_str = data["data"][0].get("startTime", "16:00:00")
                cierre_str = data["data"][0].get("endTime", "20:00:00")
                # Se extrae la hora usando split; se asume formato "HH:MM:SS" (o similar)
                horario_apertura = int(apertura_str.split(":")[0])
                horario_cierre = int(cierre_str.split(":")[0])
                return horario_apertura, horario_cierre
    except Exception as e:
        print(f"Error procesando los horarios de apertura y cierre: {e}")
    # Valores por defecto (por ejemplo, de 16 a 20)
    return 16, 20

def obtener_horarios_disponibles(fecha):
    """
    Consulta los horarios disponibles en Bookeo para todas las salas,
    y calcula los bloques de 1 hora que NO están ocupados, basado en
    los horarios de apertura y cierre.
    
    Se considera que un slot reserva la(s) hora(s) en que se inicia el bloque.
    """
    # Se obtienen las horas de apertura y cierre de la empresa
    horario_apertura, horario_cierre = obtener_horarios_apertura_cierre()
    inicio_dia = f"{fecha}T00:00:00Z"
    fin_dia = f"{fecha}T23:59:59Z"
    headers = {"Content-Type": "application/json"}
    disponibilidad = []

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
                horarios_reservados = set()
                # Se recorren los slots y se extrae la hora de inicio y fin usando split
                for slot in slots:
                    st = slot.get("startTime", "")
                    et = slot.get("endTime", "")
                    if st and et:
                        # Se asume que el formato es "YYYY-MM-DDTHH:MM:SS±HH:MM"
                        start_hour = int(st.split("T")[1].split(":")[0])
                        end_hour = int(et.split("T")[1].split(":")[0])
                        # Se marca cada hora del rango como reservada
                        for hour in range(start_hour, end_hour):
                            horarios_reservados.add(hour)
                
                # Se genera la lista de bloques disponibles de 1 hora
                bloques = []
                # Usamos el rango [horario_apertura, horario_cierre)
                for hour in range(horario_apertura, horario_cierre):
                    if hour not in horarios_reservados:
                        bloques.append(f"🕒 {hour:02d}:00 - {hour+1:02d}:00")
                
                if bloques:
                    disponibilidad.append(f"*{sala}:*\n" + "\n".join(bloques))
                else:
                    disponibilidad.append(f"*{sala}:* No hay horarios disponibles.")
            except Exception as e:
                disponibilidad.append(f"*{sala}:* Error al procesar la respuesta: {e}")
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get("message", "Sin mensaje")
            except Exception:
                error_msg = response.text
            disponibilidad.append(f"*{sala}:* Error {response.status_code} - {error_msg}")

    return "\n\n".join(disponibilidad)

@app.route("/webhook", methods=["POST"])
def webhook():
    """
    Recibe mensajes de WhatsApp (vía Twilio) y responde con la disponibilidad
    de salas y bloques de 1 hora disponibles.
    
    Si el mensaje contiene "disponibilidad" se consulta Bookeo; se permite
    especificar el día (por ejemplo, "disponibilidad 08") y, de lo contrario,
    se utiliza la fecha actual.
    """
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()
    
    if "disponibilidad" in incoming_msg:
        partes = incoming_msg.split()
        # Si se especifica un día numérico (por ejemplo, "disponibilidad 08")
        if len(partes) > 1 and partes[1].isdigit():
            fecha_consulta = f"2025-02-{partes[1].zfill(2)}"
        else:
            fecha_consulta = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        horarios = obtener_horarios_disponibles(fecha_consulta)
        respuesta = (
            f"📅 *Disponibilidad de salas para el {fecha_consulta}:*\n"
            "✔ Sala A\n"
            "✔ Sala B\n"
            "✔ Sala C\n"
            "✔ Sala D\n\n"
            "📆 *Horarios disponibles:*\n"
            f"{horarios}"
        )
    else:
        respuesta = "No entendí tu mensaje. Escribe 'Disponibilidad' (opcionalmente seguido del día, ej. 'Disponibilidad 08') para ver las salas y horarios."
    
    msg.body(respuesta)
    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
