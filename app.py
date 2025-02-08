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
    app.run(debug=True)
