from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
from openai import OpenAI
import requests
import spacy

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Load spaCy NLP model
nlp = spacy.load("en_core_web_sm")

app = Flask(__name__)

CMS_API_BASE = "https://data.cms.gov/provider-data/api/1/datastore/query"
DOCTOR_DATASET = "npcz-7egr"  # Medicare Physician Compare dataset ID

# Specialty keyword map
SPECIALTY_KEYWORDS = {
    "cardio": "Cardiovascular Disease",
    "heart": "Cardiovascular Disease",
    "derma": "Dermatology",
    "skin": "Dermatology",
    "eye": "Ophthalmology",
    "vision": "Ophthalmology",
    "ortho": "Orthopedic Surgery",
    "bone": "Orthopedic Surgery",
    "neuro": "Neurology",
    "brain": "Neurology"
}

# Expanded healthcare assistant system prompt
system_prompt = """
You are a specialized healthcare assistant for seniors and caregivers.
You answer questions and provide guidance on:

🩺 Medical & Preventive Care:
- Medicare Enrollment (Parts A, B, C, D), Medigap, avoiding penalties
- Preventive screenings: mammograms, colonoscopies, cholesterol, diabetes checks
- Vaccinations: shingles, flu, pneumonia, COVID-19 boosters
- Hearing, vision, dental care access
- Medication management and drug interaction prevention

🧠 Cognitive & Mental Health:
- Alzheimer’s, dementia, cognitive decline
- Depression, anxiety, loneliness
- Social engagement & activity programs

🏠 Safety & Daily Living:
- Aging in place: home safety modifications
- Assisted living & nursing care options
- Transportation alternatives & mobility aids
- Daily living help: cooking, cleaning, bathing

🧘 Wellness & Chronic Disease Management:
- Managing chronic illnesses: diabetes, arthritis, COPD, hypertension
- Nutrition for seniors: low sodium, balanced diets
- Physical activity: walking, swimming, yoga, tai chi
- Sleep quality, weight management, metabolism changes

💡 Health Literacy & Advocacy:
- Understanding medical bills & Medicare coverage
- Patient advocacy, care coordination
- End-of-life planning: advanced directives, living wills, DNRs

📱 Technology for Health:
- Telemedicine access
- Wearables & alert systems
- Online health portals for records & appointments

When unsure or if legal/medical advice is required, clearly state that the user should consult a licensed medical or legal professional.
"""

def extract_city_and_specialty(text):
    """Extract city and specialty from user text using spaCy + keyword map."""
    doc = nlp(text)
    city = None
    specialty = None

    # Detect city
    for ent in doc.ents:
        if ent.label_ == "GPE":
            city = ent.text

    # Detect specialty
    for key, spec in SPECIALTY_KEYWORDS.items():
        if key in text.lower():
            specialty = spec

    return city, specialty

def search_providers(city=None, specialty=None):
    """Search CMS API for providers."""
    url = f"{CMS_API_BASE}/{DOCTOR_DATASET}/0"

    params = {}
    if city:
        params["city"] = city.upper()  # CMS expects uppercase for city names
    if specialty:
        params["specialty"] = specialty  # Must match CMS's dataset values exactly

    print("CMS Search Params:", params)  # Debugging

    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        providers = data.get("records", [])[:5]  # Limit to top 5

        formatted_list = []
        for p in providers:
            name = p.get("provider_name") or p.get("name") or "Unknown Name"
            spec = p.get("specialty") or specialty or "Specialty N/A"
            prov_city = p.get("city") or city or "City N/A"
            state = p.get("state") or "State N/A"
            formatted_list.append(f"{name} — {spec} — {prov_city}, {state}")

        return formatted_list

    except Exception as e:
        return [f"Error: {str(e)}"]

@app.route('/')
def hello():
    return "Healthcare Chatbot API is running 🚑"

@app.route('/ask', methods=['POST'])
def ask_question():
    data = request.get_json()

    if not data or 'question' not in data:
        return jsonify({"error": "Please send a JSON with a 'question' field"}), 400

    user_question = data['question']

    # Provider search mode
    if "find" in user_question.lower() or "search" in user_question.lower():
        city, specialty = extract_city_and_specialty(user_question)
        providers = search_providers(city=city, specialty=specialty)
        return jsonify({
            "city": city,
            "specialty": specialty,
            "providers": providers
        })

    # GPT mode
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_question}
            ],
            max_tokens=500
        )
        answer = response.choices[0].message.content.strip()
    except Exception as e:
        answer = f"Error calling AI model: {str(e)}"

    return jsonify({"answer": answer})

if __name__ == '__main__':
    HOST = os.environ.get('SERVER_HOST', 'localhost')
    try:
        PORT = int(os.environ.get('SERVER_PORT', '5555'))
    except ValueError:
        PORT = 5555
    app.run(HOST, PORT, debug=True)
