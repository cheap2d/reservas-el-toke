import requests
from flask import Flask, request

app = Flask(__name__)

# Credenciales de Bookeo
BOOKEO_API_URL = "https://api.bookeo.com/v2/availability"
BOOKEO_APP_ID = "K7YT7NXCTENX"  # Application ID
BOOKEO_SECRET_KEY = "Hv8pW1kCjHmi3dhQe2jl1RTYL1TMsebb"  # Asegúrate de agregar el Secret Key correcto
BOOKEO_API_KEY = "AJ9CL4R7WK7YT7NXCTENX415663YHCYT17E53FE901F"  # API Key real

@app.route("/", methods=["GET"])
def home():
    return "Flask app is running!"

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_message = request.form.get("Body")  # Mensaje recibido

    if "disponibilidad" in incoming_message.lower():
        availability = consultar_disponibilidad()
        return f"""
        <Response>
            <Message>
                {availability}
            </Message>
        </Response>
        """

    response_message = f"Hola, recibimos tu mensaje: {incoming_message}"
    return f"""
    <Response>
        <Message>
            {response_message}
        </Message>
    </Response>
    """

def consultar_disponibilidad():
    salas = {
        "Sala A": "JXTLMHYU",
        "Sala B": "NFNHNNJE",
        "Sala C": "FKPWTENX",
        "Sala D": "TAHYRHYL"
    }

    disponibilidad = []

    for nombre_sala, product_id in salas.items():
        params = {
            "apiKey": BOOKEO_API_KEY,  # API Key real
            "secretKey": BOOKEO_SECRET_KEY,  # Secret Key real
            "startTime": "2025-02-09T09:00:00Z",  # Asegura que tenga la "Z" (UTC)
            "endTime": "2025-02-09T18:00:00Z",
            "productId": product_id
        }
        try:
            response = requests.get(BOOKEO_API_URL, params=params)
            print(f"Respuesta de Bookeo para {nombre_sala}: {response.text}")  # Log para depuración

            if response.status_code == 200:
                data = response.json()
                if data:
                    disponibilidad.append(f"{nombre_sala}: Disponible")
                else:
                    disponibilidad.append(f"{nombre_sala}: No disponible")
            else:
                disponibilidad.append(f"{nombre_sala}: Error {response.status_code}")

        except Exception as e:
            disponibilidad.append(f"{nombre_sala}: Error {str(e)}")

    return "\n".join(disponibilidad)




if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)

