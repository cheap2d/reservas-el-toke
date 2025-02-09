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
    para el día correspondiente a la fecha indicada.
    
    Se asume que:
      - La respuesta contiene una clave "data" con una lista de objetos.
      - Cada objeto tiene "dayOfWeek", "startTime" y "endTime".
      - Bookeo utiliza la convención: domingo=0, lunes=1, …, sábado=6.
    
    Como Python devuelve weekday() con lunes=0 … domingo=6, convertimos:
        bookeo_day = (python_weekday + 1) % 7
    Si no se encuentra información, se retornan valores por defecto.
    """
    url = f"{BOOKEO_BASE_URL}/business/operatingHours?apiKey={BOOKEO_API_KEY}&secretKey={BOOKEO_SECRET_KEY}"
    try:
        response = requests.get(url)
        if response.status_code in (200, 201):
            data = response.json()
            dt = datetime.datetime.strptime(fecha, "%Y-%m-%d")
            python_weekday = dt.weekday()  # lunes=0, domingo=6
            bookeo_day = (python_weekday + 1) % 7  # Convertir: domingo=0, lunes=1, etc.
            print(f"[DEBUG] Fecha: {fecha} | Python weekday: {python_weekday} | Bookeo_day: {bookeo_day}")
            if "data" in data and data["data"]:
                for item in data["data"]:
                    print(f"[DEBUG] operatingHours item: {item}")
                    # Se asume que item["dayOfWeek"] es numérico y sigue la convención Bookeo.
                    if "dayOfWeek" in item and int(item["dayOfWeek"]) == bookeo_day:
                        apertura_str = item.get("startTime", "16:00:00")
                        cierre_str = item.get("endTime", "20:00:00")
                        print(f"[DEBUG] Horario para {fecha}: Apertura: {apertura_str} - Cierre: {cierre_str}")
                        return int(apertura_str.split(":")[0]), int(cierre_str.split(":")[0])
    except Exception as e:
        print(f"[DEBUG] Error obteniendo horarios operativos: {e}")
    # Valores por defecto en caso de error o si no hay datos:
    # Puedes ajustar estos valores según la configuración de tu negocio.
    return 16, 20

def obtener_horarios_disponibles(fecha):
    """
    Consulta los slots disponibles en Bookeo para todas las salas para la fecha indicada
    (desde las 00:00 hasta las 23:59:59Z) y filtra los slots para que se muestren solo aquellos
    que caigan dentro del horario operativo obtenido (por ejemplo, apertura 16:00 y cierre 20:00).
    """
    inicio_dia = f"{fecha}T00:00:00Z"
    fin_dia = f"{fecha}T23:59:59Z"
    headers = {"Content-Type": "application/json"}
    disponibilidad = []

    # Obtener los horarios operativos para la fecha
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
                # Filtrar slots para incluir solo aquellos dentro del horario operativo
                slots_filtrados = []
                for slot in slots:
                    st = slot.get("startTime", "")
                    et = slot.get("endTime", "")
                    if st and et:
                        try:
                            start_hour = int(st.split("T")[1].split(":")[0])
                            end_hour = int(et.split("T")[1].split(":")[0])
                        except Exception as ex:
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
    
    - Si el mensaje es "disponibilidad" se usa la fecha actual.
    - Si es "disponibilidad 9", se consulta para el 2025-02-09 (en este ejemplo se fija el mes y el año a 2025-02).
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
        # También obtenemos la información operativa para mostrarla (por depuración)
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
