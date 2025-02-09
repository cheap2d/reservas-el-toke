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

def parse_iso_hour(iso_str):
    try:
        dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.hour
    except Exception as e:
        print(f"[DEBUG] Error parseando '{iso_str}': {e}")
        return None

def detectar_horarios_operativos_por_slots(fecha):
    sala_id = next(iter(SALAS.values()))
    inicio_dia = f"{fecha}T00:00:00Z"
    fin_dia = f"{fecha}T23:59:59Z"
    headers = {"Content-Type": "application/json"}
    url = f"{BOOKEO_BASE_URL}/availability/matchingslots?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    payload = {
        "productId": sala_id,
        "startTime": inicio_dia,
        "endTime": fin_dia,
        "peopleNumbers": [{"peopleCategoryId": "Cadults", "number": 1}]
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code in (200, 201):
            data = response.json()
            slots = data.get("data", [])
            if slots:
                horas_inicio = [parse_iso_hour(slot.get("startTime")) for slot in slots if slot.get("startTime")]
                horas_fin = [parse_iso_hour(slot.get("endTime")) for slot in slots if slot.get("endTime")]
                if horas_inicio and horas_fin:
                    return min(horas_inicio), max(horas_fin)
    except Exception as e:
        print(f"[DEBUG] Error detectando horarios por slots: {e}")
    return 16, 20

def obtener_horarios_apertura_cierre(fecha):
    url = f"{BOOKEO_BASE_URL}/business/operatingHours?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    try:
        response = requests.get(url)
        if response.status_code in (200, 201):
            data = response.json()
            dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
            bookeo_day = (dt.weekday() + 1) % 7
            for item in data.get("data", []):
                if int(item.get("dayOfWeek", -1)) == bookeo_day:
                    apertura_ep = int(item.get("startTime", "16:00").split(":")[0])
                    cierre_ep = int(item.get("endTime", "20:00").split(":")[0])
                    return apertura_ep, cierre_ep
    except Exception as e:
        print(f"[DEBUG] Error obteniendo horarios operativos del endpoint: {e}")
    return detectar_horarios_operativos_por_slots(fecha)

def obtener_horarios_disponibles(fecha):
    inicio_dia = f"{fecha}T00:00:00Z"
    fin_dia = f"{fecha}T23:59:59Z"
    headers = {"Content-Type": "application/json"}
    disponibilidad = []
    apertura, cierre = obtener_horarios_apertura_cierre(fecha)
    print(f"[DEBUG] Horarios operativos para {fecha}: {apertura}:00 - {cierre}:00")

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
                slots_filtrados = [slot for slot in slots if apertura <= parse_iso_hour(slot.get("startTime")) < cierre]
                if slots_filtrados:
                    horarios = [f"🕒 {slot['startTime'][11:16]} - {slot['endTime'][11:16]}" for slot in slots_filtrados]
                    disponibilidad.append(f"*{sala}:*\n" + "\n".join(horarios))
                else:
                    disponibilidad.append(f"*{sala}:* No hay horarios disponibles.")
            except Exception as e:
                disponibilidad.append(f"*{sala}:* Error al procesar la respuesta: {e}")
    return "\n\n".join(disponibilidad)

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_msg = request.values.get("Body", "").strip().lower()
    print(f"[DEBUG] Mensaje recibido: {incoming_msg}")  # Verificar qué mensaje llega

    resp = MessagingResponse()
    msg = resp.message()

    if "disponibilidad" in incoming_msg:
        fecha_consulta = datetime.datetime.utcnow().strftime("%Y-%m-%d")
        print(f"[DEBUG] Consultando disponibilidad para {fecha_consulta}")  # Log de la fecha

        slots = obtener_horarios_disponibles(fecha_consulta)
        print(f"[DEBUG] Resultado de disponibilidad:\n{slots}")  # Log de lo que devuelve la función

        respuesta = (
            f"📅 *Disponibilidad de salas para el {fecha_consulta}:*\n"
            "✔ Sala A\n✔ Sala B\n✔ Sala C\n✔ Sala D\n\n"
            "📆 *Horarios disponibles:*\n"
            f"{slots}"
        )
    else:
        respuesta = "No entendí tu mensaje. Escribe 'disponibilidad' para ver las salas y horarios."

    print(f"[DEBUG] Respuesta enviada:\n{respuesta}")  # Log de la respuesta final
    msg.body(respuesta)
    return str(resp), 200, {'Content-Type': 'text/xml'}



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
