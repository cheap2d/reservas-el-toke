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

def detectar_horarios_operativos_por_slots(fecha):
    """
    Detecta los horarios operativos a partir de los slots devueltos por Bookeo para
    una sala (se toma la primera de SALAS). Se retorna (min_start, max_end) según los
    slots encontrados; en caso de error, se retornan valores por defecto.
    """
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
                # Extraemos la hora de inicio y fin de cada slot
                horas_inicio = [int(slot['startTime'].split("T")[1].split(":")[0]) for slot in slots]
                horas_fin = [int(slot['endTime'].split("T")[1].split(":")[0]) for slot in slots]
                if horas_inicio and horas_fin:
                    apertura_detectada = min(horas_inicio)
                    cierre_detectado = max(horas_fin)
                    print(f"[DEBUG] Detectado por slots para {fecha}: Apertura {apertura_detectada}:00, Cierre {cierre_detectado}:00")
                    return apertura_detectada, cierre_detectada
    except Exception as e:
        print(f"[DEBUG] Error detectando horarios por slots: {e}")
    # Valor por defecto
    return 16, 20

def obtener_horarios_apertura_cierre(fecha):
    """
    Intenta obtener los horarios operativos usando el endpoint /business/operatingHours.
    Se compara con la detección por slots y, si los valores del endpoint parecen inconsistentes
    (por ejemplo, apertura mayor que la detectada por slots o cierre menor), se usa la detección por slots.
    """
    url = f"{BOOKEO_BASE_URL}/business/operatingHours?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    try:
        response = requests.get(url)
        if response.status_code in (200, 201):
            data = response.json()
            dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
            python_weekday = dt.weekday()  # lunes=0 ... domingo=6
            # Suponiendo que Bookeo usa domingo=0, lunes=1, etc.
            bookeo_day = (python_weekday + 1) % 7
            print(f"[DEBUG] Fecha: {fecha} | Python weekday: {python_weekday} | Bookeo_day: {bookeo_day}")
            if "data" in data and data["data"]:
                for item in data["data"]:
                    print(f"[DEBUG] operatingHours item: {item}")
                    if "dayOfWeek" in item and int(item["dayOfWeek"]) == bookeo_day:
                        apertura_str = item.get("startTime")
                        cierre_str = item.get("endTime")
                        if apertura_str and cierre_str:
                            apertura_ep = int(apertura_str.split(":")[0])
                            cierre_ep = int(cierre_str.split(":")[0])
                            # Detectar también por slots
                            apertura_slots, cierre_slots = detectar_horarios_operativos_por_slots(fecha)
                            print(f"[DEBUG] Horario por endpoint: {apertura_ep}:00 - {cierre_ep}:00")
                            # Si los valores del endpoint son "más restrictivos" que los detectados por slots, usaremos los de slots
                            if apertura_ep > apertura_slots or cierre_ep < cierre_slots:
                                print(f"[DEBUG] Usando valores detectados por slots: {apertura_slots}:00 - {cierre_slots}:00")
                                return apertura_slots, cierre_slots
                            else:
                                return apertura_ep, cierre_ep
    except Exception as e:
        print(f"[DEBUG] Error obteniendo horarios operativos del endpoint: {e}")
    # Si no se pudo obtener o no hay datos, usar la detección por slots
    return detectar_horarios_operativos_por_slots(fecha)

def obtener_horarios_disponibles(fecha):
    """
    Consulta los slots disponibles en Bookeo para todas las salas para la fecha indicada
    (rango de 00:00 a 23:59:59Z) y filtra los slots para incluir sólo aquellos que caigan
    dentro de los horarios operativos detectados.
    """
    inicio_dia = f"{fecha}T00:00:00Z"
    fin_dia = f"{fecha}T23:59:59Z"
    headers = {"Content-Type": "application/json"}
    disponibilidad = []

    # Obtener horarios operativos detectados para la fecha
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
                # Filtrar para que solo se incluyan slots dentro de [apertura, cierre]
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
    
    - Si el mensaje es "disponibilidad" sin número se usa la fecha actual.
    - Si es "disponibilidad 9" se consulta para 2025-02-09, "disponibilidad 10" para 2025-02-10, etc.
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
