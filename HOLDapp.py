# app.py

from flask import Flask, render_template, request, Response, stream_with_context
from rukbot import stream_response
import os

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("chat.html")  # Ensure this file exists!

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

# ✅ Add this just BEFORE the __main__ block
@app.route("/widget")
def rukbot_widget():
    return render_template("rukbot-widget.html")

# ✅ Main server launcher
if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    app.run(debug=True, host="0.0.0.0", port=port)