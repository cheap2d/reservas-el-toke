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
    Consulta el endpoint /business/operatingHours y busca los horarios de apertura y cierre
    para el día de la semana correspondiente a la fecha indicada.

    Se asume que la respuesta contiene una clave "data" con una lista de objetos, donde cada
    objeto tiene:
      - "dayOfWeek": un número (suponemos lunes=0 ... domingo=6)
      - "startTime": en formato "HH:MM:SS"
      - "endTime": en formato "HH:MM:SS"

    Si no se encuentra la información para ese día, se retornan valores por defecto.
    """
    url = f"{BOOKEO_BASE_URL}/business/operatingHours?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    try:
        response = requests.get(url)
        if response.status_code in (200, 201):
            data = response.json()
            # Convertir la fecha consultada en un objeto datetime
            dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
            weekday = dt.weekday()  # lunes=0, domingo=6
            print(f"[DEBUG] Fecha consultada: {fecha} - weekday: {weekday}")
            if "data" in data and data["data"]:
                for item in data["data"]:
                    # Imprime el item para ver la convención del día
                    print(f"[DEBUG] operatingHours item: {item}")
                    # Si la API usa la misma convención (lunes=0) que Python:
                    if "dayOfWeek" in item and int(item["dayOfWeek"]) == weekday:
                        apertura_str = item.get("startTime", "16:00:00")
                        cierre_str = item.get("endTime", "20:00:00")
                        print(f"[DEBUG] Horario para {fecha}: Apertura: {apertura_str} - Cierre: {cierre_str}")
                        # Extraemos la hora (solo la parte "HH")
                        return int(apertura_str.split(":")[0]), int(cierre_str.split(":")[0])
    except Exception as e:
        print(f"[DEBUG] Error obteniendo horarios operativos: {e}")
    # Valores por defecto en caso de error o si no se encuentra información para ese día
    return 16, 20

def obtener_horarios_disponibles(fecha):
    """
    Consulta los horarios disponibles en Bookeo para todas las salas para la fecha indicada,
    y muestra los slots tal como los devuelve la API.
    """
    # Rango completo del día
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
                if slots:
                    # Se muestran los slots tal como los devuelve la API
                    horarios = [f"🕒 {slot['startTime'][11:16]} - {slot['endTime'][11:16]}" for slot in slots]
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
    y los slots disponibles para la fecha consultada.
    
    Se puede especificar el día en el mensaje (por ejemplo, "disponibilidad 10" para el 10 del mes)
    y se usará ese día para construir la fecha. Si no se especifica, se usa la fecha actual.
    """
    incoming_msg = request.values.get("Body", "").strip().lower()
    resp = MessagingResponse()
    msg = resp.message()
    
    if "disponibilidad" in incoming_msg:
        partes = incoming_msg.split()
        if len(partes) > 1 and partes[1].isdigit():
            # Aquí se fija el mes y el año (en este ejemplo, "2025-02-")
            fecha_consulta = f"2025-02-{partes[1].zfill(2)}"
        else:
            fecha_consulta = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        slots = obtener_horarios_disponibles(fecha_consulta)
        # Para depuración, mostramos también el horario operativo obtenido:
        apertura, cierre = obtener_horarios_apertura_cierre(fecha_consulta)
        info_operativa = f"(Horarios operativos: {apertura:02d}:00 - {cierre:02d}:00)"
        respuesta = (
            f"📅 *Disponibilidad de salas para el {fecha_consulta}:* {info_operativa}\n"
            "✔ Sala A\n"
            "✔ Sala B\n"
            "✔ Sala C\n"
            "✔ Sala D\n\n"
            "📆 *Horarios disponibles:*\n"
            f"{slots}"
        )
    else:
        respuesta = "No entendí tu mensaje. Escribe 'Disponibilidad' (opcionalmente seguido del día, ej. 'disponibilidad 10') para ver las salas y horarios."
    
    msg.body(respuesta)
    return str(resp), 200, {'Content-Type': 'text/xml'}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
