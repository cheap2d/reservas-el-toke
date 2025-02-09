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
    Consulta el endpoint de operatingHours y busca los horarios de apertura y cierre
    correspondientes al día de la semana de la fecha indicada.
    
    Se asume que el endpoint devuelve una lista de objetos con al menos:
      - "dayOfWeek": (0 para lunes, 6 para domingo)
      - "startTime": formato "HH:MM:SS"
      - "endTime": formato "HH:MM:SS"
    
    Si no se encuentra la información, se retornan valores por defecto (por ejemplo, 16 a 20).
    """
    url = f"{BOOKEO_BASE_URL}/business/operatingHours?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    try:
        response = requests.get(url)
        if response.status_code in (200, 201):
            data = response.json()
            # Suponemos que la respuesta tiene una clave "data" con una lista de horarios
            if "data" in data and len(data["data"]) > 0:
                # Convertir la fecha de consulta en un objeto datetime
                dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
                weekday = dt.weekday()  # lunes=0, domingo=6
                for item in data["data"]:
                    # Se asume que cada item tiene un campo "dayOfWeek" (numérico o en forma de string convertible a int)
                    if "dayOfWeek" in item and int(item["dayOfWeek"]) == weekday:
                        apertura_str = item.get("startTime", "16:00:00")
                        cierre_str = item.get("endTime", "20:00:00")
                        horario_apertura = int(apertura_str.split(":")[0])
                        horario_cierre = int(cierre_str.split(":")[0])
                        return horario_apertura, horario_cierre
    except Exception as e:
        print(f"Error obteniendo horarios operativos: {e}")
    # Valores por defecto en caso de error
    return 16, 20

def obtener_horarios_disponibles(fecha):
    """
    Consulta los horarios disponibles en Bookeo para todas las salas para la fecha indicada,
    y calcula los bloques de 1 hora libres según los horarios de apertura y cierre de ese día.
    Se consideran las horas reservadas devueltas por la API.
    """
    # Se obtienen los horarios operativos para la fecha consultada
    horario_apertura, horario_cierre = obtener_horarios_apertura_cierre(fecha)
    # Se consulta el día completo (de 00:00 a 23:59:59)
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
                # Se crea un conjunto de horas ocupadas en base a los slots devueltos
                horarios_reservados = set()
                for slot in slots:
                    st = slot.get("startTime", "")
                    et = slot.get("endTime", "")
                    if st and et:
                        # Se extrae la hora de inicio y fin (asumiendo formato ISO 8601)
                        start_hour = int(st.split("T")[1].split(":")[0])
                        end_hour = int(et.split("T")[1].split(":")[0])
                        # Se marca cada hora entre start_hour y end_hour como reservada
                        for hour in range(start_hour, end_hour):
                            horarios_reservados.add(hour)
                
                # Ahora, generamos los bloques de 1 hora libres entre el horario de apertura y cierre
                bloques_disponibles = []
                for hour in range(horario_apertura, horario_cierre):
                    if hour not in horarios_reservados:
                        bloques_disponibles.append(f"🕒 {hour:02d}:00 - {hour+1:02d}:00")
                
                if bloques_disponibles:
                    disponibilidad.append(f"*{sala}:*\n" + "\n".join(bloques_disponibles))
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
    Recibe mensajes de WhatsApp (vía Twilio) y responde con la disponibilidad de salas
    y los bloques de 1 hora disponibles para la fecha consultada.
    El mensaje puede incluir el día (por ejemplo, "disponibilidad 09") para consultar una fecha específica;
    de lo contrario se utiliza la fecha actual.
    """
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()
    
    if "disponibilidad" in incoming_msg:
        partes = incoming_msg.split()
        if len(partes) > 1 and partes[1].isdigit():
            # Se asume que se consulta para el mes actual (por ejemplo, 2025-02-XX)
            fecha_consulta = f"2025-02-{partes[1].zfill(2)}"
        else:
            fecha_consulta = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        bloques = obtener_horarios_disponibles(fecha_consulta)
        respuesta = (
            f"📅 *Disponibilidad de salas para el {fecha_consulta}:*\n"
            "✔ Sala A\n"
            "✔ Sala B\n"
            "✔ Sala C\n"
            "✔ Sala D\n\n"
            "📆 *Horarios disponibles (bloques de 1 hora):*\n"
            f"{bloques}"
        )
    else:
        respuesta = "No entendí tu mensaje. Escribe 'Disponibilidad' (opcionalmente seguido del día, ej. 'disponibilidad 09') para ver las salas y horarios."
    
    msg.body(respuesta)
    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
