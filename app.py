from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import base64
import google.generativeai as genai
import os
import hashlib

app = Flask(__name__)
CORS(app)

# Image response cache
cache = {}

# Question cache
question_cache = {}

# Configure Gemini API
genai.configure(api_key="AIzaSyBckWBfyGBrD-j_ulaWUvm0mKl8e0HKC0Y")

@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        image_data = data.get("image")

        if not image_data:
            return jsonify({"reply": "No image received"}), 400

        # Strip base64 prefix
        image_data = image_data.split(",")[1]
        image_hash = hashlib.md5(image_data.encode('utf-8')).hexdigest()

        if image_hash in cache:
            reply = f"Using cached response: {cache[image_hash]}"
            return jsonify({"reply": reply})

        image_bytes = base64.b64decode(image_data)

        # Create Gemini model
        model = genai.GenerativeModel("gemini-2.0-flash")

        # First, extract questions from the image
        extract_response = model.generate_content([
            {"mime_type": "image/jpeg", "data": image_bytes},
            "Extract all questions from this image. List them as Q1: question text\nQ2: question text\n etc. If no questions, say 'No questions found'."
        ])

        questions_text = extract_response.text if extract_response.text else "No questions found"

        if 'No questions found' in questions_text:
            # Describe the image
            response = model.generate_content([
                {"mime_type": "image/jpeg", "data": image_bytes},
                "Describe this image in detail, interpreting any graphs, charts, or visual data present."
            ])
            reply = response.text if response.text else "No response from Gemini"
        else:
            # Parse questions
            questions = [line.strip() for line in questions_text.split('\n') if line.strip().startswith('Q')]
            response_parts = []
            for q in questions:
                q_hash = hashlib.md5(q.encode('utf-8')).hexdigest()
                if q_hash in question_cache:
                    a = question_cache[q_hash]
                    response_parts.append(f"{q}\nCached Answer: {a}")
                else:
                    # Generate answer
                    ans_response = model.generate_content([
                        {"mime_type": "image/jpeg", "data": image_bytes},
                        f"Answer this question accurately based on the image, interpreting any graphs or charts if present, and standard knowledge: {q}"
                    ])
                    a = ans_response.text if ans_response.text else "No answer"
                    question_cache[q_hash] = a
                    response_parts.append(f"{q}\n{a}")
            reply = '\n\n'.join(response_parts)

        # Cache the full response
        cache[image_hash] = reply
        return jsonify({"reply": reply})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)


