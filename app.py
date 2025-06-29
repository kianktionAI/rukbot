from flask import Flask, render_template, request, Response, stream_with_context
from rukbot import stream_response

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/chat", methods=["POST"])
def chat():
    try:
        if request.is_json:
            user_input = request.json.get("message", "")
        else:
            user_input = request.form.get("user_input", "")

        if not user_input:
            return Response("No user input received", status=400)

        def generate():
            for chunk in stream_response(user_input):
                yield chunk

        return Response(stream_with_context(generate()), mimetype='text/plain')

    except Exception as e:
        print("Error in /chat route:", e)
        return Response(f"Error: {str(e)}", status=500)

if __name__ == "__main__":
    app.run(debug=True)
