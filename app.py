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

# Definir manualmente los horarios operativos para fechas específicas.
# Ajusta estos valores según la configuración real de tu negocio en Bookeo.
OPERATING_HOURS = {
    "2025-02-09": (12, 16),  # Apertura a las 12:00 y cierre a las 16:00 para el 9 de febrero
    "2025-02-10": (8, 20),   # Apertura a las 08:00 y cierre a las 20:00 para el 10 de febrero
}

def obtener_horarios_apertura_cierre(fecha):
    """
    Retorna los horarios operativos (apertura, cierre) para la fecha dada,
    usando la información del diccionario OPERATING_HOURS.
    Si la fecha no está configurada, retorna valores por defecto (16:00-20:00).
    """
    return OPERATING_HOURS.get(fecha, (16, 20))

def obtener_horarios_disponibles(fecha):
    """
    Consulta los slots disponibles en Bookeo para todas las salas para la fecha indicada
    (rango 00:00 a 23:59:59Z) y filtra los slots para incluir solo aquellos que
    caigan dentro de los horarios operativos definidos.
    """
    inicio_dia = f"{fecha}T00:00:00Z"
    fin_dia = f"{fecha}T23:59:59Z"
    headers = {"Content-Type": "application/json"}
    disponibilidad = []
    
    # Obtener los horarios operativos manualmente
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
                # Filtrar los slots para incluir únicamente los que caigan dentro de [apertura, cierre]
                slots_filtrados = []
                for slot in slots:
                    st = slot.get("startTime", "")
                    et = slot.get("endTime", "")
                    if st and et:
                        try:
                            start_hour = int(st.split("T")[1].split(":")[0])
                            end_hour = int(et.split("T")[1].split(":")[0])
                        except Exception:
                            continue
                        if start_hour >= apertura and end_hour <= cierre:
                            slots_filtrados.append(slot)
                if slots_filtrados:
                    horarios = [f"🕒 {slot['startTime'][11:16]} - {slot['endTime'][11:16]}" for slot in slots_filtrados]
                    disponibilidad.append(f"*{sala}:*\n" + "\n".join(horarios))
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
    para la fecha solicitada.
    
    - Si se envía "disponibilidad" sin número, se usa la fecha actual.
    - Si se envía "disponibilidad 9" se consulta para 2025-02-09,
      "disponibilidad 10" para 2025-02-10, etc.
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
        
        slots = obtener_horarios_disponibles(fecha_consulta)
        apertura, cierre = obtener_horarios_apertura_cierre(fecha_consulta)
        info_operativa = f"(Horarios operativos: {apertura:02d}:00 - {cierre:02d}:00)"
        respuesta = (
            f"📅 *Disponibilidad de salas para el {fecha_consulta}:* {info_operativa}\n"
            "✔ Sala A\n"
            "✔ Sala B\n"
            "✔ Sala C\n"
            "✔ Sala D\n\n"
            "📆 *Horarios disponibles (dentro del horario operativo):*\n"
            f"{slots}"
        )
    else:
        respuesta = "No entendí tu mensaje. Escribe 'disponibilidad' (opcionalmente seguido del día, ej. 'disponibilidad 10') para ver las salas y horarios."
    
    msg.body(respuesta)
    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
