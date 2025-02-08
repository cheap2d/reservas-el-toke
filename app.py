from flask import Flask, request

app = Flask(__name__)

@app.route("/webhook", methods=["POST"])
def webhook():
    incoming_message = request.form.get("Body")  # Mensaje recibido
    from_number = request.form.get("From")  # Número del remitente
    response_message = f"Hola, recibimos tu mensaje: {incoming_message}"  # Respuesta
    return f"""
    <Response>
        <Message>
            {response_message}
        </Message>
    </Response>
    """

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))  # Render asigna el puerto automáticamente
    app.run(host="0.0.0.0", port=port, debug=True)  # Cambia host a 0.0.0.0
