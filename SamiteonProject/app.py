"""
Healthcare Chatbot API - Flask
"""

from flask import Flask, request, jsonify
import os

app = Flask(__name__)

# Root endpoint
@app.route('/')
def hello():
    return "Healthcare Chatbot API is running 🚑"

# Chatbot endpoint
@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()

    if not data or 'question' not in data:
        return jsonify({"error": "Please send a JSON with a 'question' field"}), 400

    user_question = data['question']

    # TODO: Replace this placeholder with AI/GPT logic
    answer = f"You asked: {user_question}. I will connect to the AI model soon!"

    return jsonify({"answer": answer})

if __name__ == '__main__':
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)
