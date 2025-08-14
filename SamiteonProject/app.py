from flask import Flask, request, jsonify, render_template
import os, re, json, math
from dotenv import load_dotenv
import requests
from rapidfuzz import process, fuzz

# ------------------- Setup -------------------
load_dotenv()
app = Flask(__name__)

CMS_API_KEY = os.getenv("CMS_API_KEY")  # optional
CMS_DATASET_ID = "mj5m-pzi6"
CMS_DATASTORE_POST = f"https://data.cms.gov/provider-data/api/1/datastore/query/{CMS_DATASET_ID}/0"

# ------------------- Memory (very simple, per-process) -------------------
user_context = {
    "city": None,          # e.g., "Boston"
    "state": None,         # e.g., "MA"
    "zip": None,           # optional
    "specialty": None,     # e.g., "CARDIOLOGY"
    "last_results": [],    # cached strings for “more”
    "last_shown": 0        # how many we’ve shown already
}

# ------------------- US States -------------------
US_STATES = {
    "AL","AK","AZ","AR","CA","CO","CT","DE","DC","FL","GA","HI","ID","IL","IN","IA",
    "KS","KY","LA","ME","MD","MA","MI","MN","MS","MO","MT","NE","NV","NH","NJ","NM",
    "NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA","WA",
    "WV","WI","WY"
}
STATE_NAME_TO_CODE = {
    "alabama":"AL","alaska":"AK","arizona":"AZ","arkansas":"AR","california":"CA",
    "colorado":"CO","connecticut":"CT","delaware":"DE","district of columbia":"DC",
    "florida":"FL","georgia":"GA","hawaii":"HI","idaho":"ID","illinois":"IL",
    "indiana":"IN","iowa":"IA","kansas":"KS","kentucky":"KY","louisiana":"LA",
    "maine":"ME","maryland":"MD","massachusetts":"MA","michigan":"MI","minnesota":"MN",
    "mississippi":"MS","missouri":"MO","montana":"MT","nebraska":"NE","nevada":"NV",
    "new hampshire":"NH","new jersey":"NJ","new mexico":"NM","new york":"NY",
    "north carolina":"NC","north dakota":"ND","ohio":"OH","oklahoma":"OK","oregon":"OR",
    "pennsylvania":"PA","rhode island":"RI","south carolina":"SC","south dakota":"SD",
    "tennessee":"TN","texas":"TX","utah":"UT","vermont":"VT","virginia":"VA",
    "washington":"WA","west virginia":"WV","wisconsin":"WI","wyoming":"WY"
}

# ------------------- Specialties & synonyms -------------------
# Keys: phrases users type; Values: canonical labels to display to user.
SYNONYM_MAP = {
    # Cardio
    "heart": "Cardiology", "cardio": "Cardiology", "cardiology": "Cardiology",
    "cardiologist": "Cardiology",
    # Neuro
    "neuro": "Neurology", "neurology": "Neurology", "brain": "Neurology",
    # Eyes
    "eye": "Ophthalmology", "eyes": "Ophthalmology", "vision": "Ophthalmology",
    # ENT
    "ent": "Otolaryngology", "ear": "Otolaryngology", "throat": "Otolaryngology",
    # Ortho
    "ortho": "Orthopedic Surgery", "orthopedics": "Orthopedic Surgery",
    "orthopedic": "Orthopedic Surgery", "bone": "Orthopedic Surgery",
    "knee": "Orthopedic Surgery", "hip": "Orthopedic Surgery",
    # Peds
    "peds": "Pediatrics", "pediatric": "Pediatrics", "pediatrics": "Pediatrics",
    "kids": "Pediatrics", "children": "Pediatrics", "child": "Pediatrics",
    # Psych(ology/iatry)
    "psych": "Psychiatry",
    "psychiatry": "Psychiatry", "psychiatrist": "Psychiatry",
    "psychology": "Clinical Psychologist", "psychologist": "Clinical Psychologist",
    # Common misspellings -> Psychology
    "pscychologist": "Clinical Psychologist", "phsycologist": "Clinical Psychologist",
    "psycologist": "Clinical Psychologist",
    # Therapy (Physical Therapy)
    "therapy": "Physical Therapy", "therapist": "Physical Therapy", "pt": "Physical Therapy",
    "physical therapy": "Physical Therapy", "physiotherapy": "Physical Therapy",
}

# When talking to CMS data, we search these substrings in pri_spec/sec_spec_all
# so we catch CMS's wording variations.
CMS_SEARCH_TERMS = {
    "Cardiology": "CARDIO",
    "Neurology": "NEURO",
    "Ophthalmology": "OPHTHAL",
    "Otolaryngology": "OTOLARYNG",   # ENT
    "Orthopedic Surgery": "ORTHOPED",
    "Pediatrics": "PEDIATR",         # CMS often has “PEDIATRIC MEDICINE”
    "Psychiatry": "PSYCHIAT",
    "Clinical Psychologist": "PSYCHOLOG",  # “Clinical Psychologist”
    "Physical Therapy": "THERAP",     # catches Therapist/Therapy variants
}

# Optional: seed a set of observed CMS specialties for fuzzy matching (best-effort)
CMS_SPECIALTIES = set()

def load_cms_specialties_sample():
    try:
        headers = {"Accept": "application/json"}
        if CMS_API_KEY:
            headers["X-API-KEY"] = CMS_API_KEY
        r = requests.get(CMS_DATASTORE_POST, params={"size": 300}, headers=headers, timeout=15)
        r.raise_for_status()
        for row in r.json().get("results", []):
            for k in ("pri_spec", "sec_spec_all"):
                if row.get(k):
                    CMS_SPECIALTIES.add(row[k].strip().upper())
    except Exception as e:
        print("Load specialties sample failed:", e)

load_cms_specialties_sample()

# ------------------- Parsing helpers -------------------
CITY_STATE_RE = re.compile(r"^\s*([A-Za-z .'\-]+?)[,\s]+([A-Za-z .'\-]{2,})\s*$")

def normalize_state(token: str):
    if not token:
        return None
    token = token.strip()
    if len(token) == 2 and token.upper() in US_STATES:
        return token.upper()
    return STATE_NAME_TO_CODE.get(token.lower())

def parse_city_state(text: str):
    """
    Accept:
      - "City, ST"
      - "City ST"
      - "City StateName"
      - "ST" (code) or "StateName"
      - "City" (only city)
    Return (city or None, state_code or None)
    """
    t = (text or "").strip()
    if not t:
        return None, None

    m = CITY_STATE_RE.match(t)
    if m:
        city = m.group(1).strip()
        st_code = normalize_state(m.group(2))
        if st_code:
            return city, st_code

    parts = t.rsplit(" ", 1)
    if len(parts) == 2:
        maybe_city, maybe_state = parts[0].strip(), parts[1].strip()
        st_code = normalize_state(maybe_state)
        if st_code:
            return maybe_city, st_code

    st_code = normalize_state(t)
    if st_code:
        return None, st_code

    return t, None  # city-only guess

def fuzzy_specialty(user_text: str):
    """
    Map user text to a canonical specialty (display label), using:
      1) wide synonym table (incl. misspellings),
      2) fuzzy match against synonyms keys,
      3) fuzzy match against observed CMS specialties (fallback),
      4) otherwise None (we'll treat it as location, or ask for clarity).
    """
    if not user_text:
        return None

    raw = user_text.strip().lower()

    # Exact synonym hit
    if raw in SYNONYM_MAP:
        return SYNONYM_MAP[raw]

    # Fuzzy to synonym keys
    s_key, score, _ = process.extractOne(raw, SYNONYM_MAP.keys(), scorer=fuzz.token_sort_ratio)
    if score >= 85:
        return SYNONYM_MAP[s_key]

    # If multi-word contains a synonym key, honor it (e.g., "back orthopedic doctor")
    for key in SYNONYM_MAP:
        if key in raw:
            return SYNONYM_MAP[key]

    # Fuzzy to CMS specialty values (e.g., “PEDIATRIC MEDICINE”, etc.)
    if CMS_SPECIALTIES:
        cand, cscore, _ = process.extractOne(raw.upper(), CMS_SPECIALTIES, scorer=fuzz.token_sort_ratio)
        if cscore >= 80:
            # Convert back to a reasonable display class when possible
            # We'll keep the raw CMS label for display if we don't have a canonical bucket.
            for label, needle in CMS_SEARCH_TERMS.items():
                if needle in cand:
                    return label
            return cand.title()

    return None

def extract_from_turn(user_text: str):
    """
    Extract possible city/state and specialty from this single user message,
    making sure a specialty word doesn’t become a city by mistake.
    """
    # Specialty first
    spec = fuzzy_specialty(user_text)

    # City/State
    city, state = parse_city_state(user_text)

    # If the “city” looks like a single-word specialty, drop it as city
    if city and not state:
        if len(city.split()) == 1 and fuzzy_specialty(city):
            city = None

    # ZIP (optional)
    zip_code = None
    m = re.search(r"\b\d{5}\b", user_text)
    if m: zip_code = m.group()

    return city, state, zip_code, spec

# ------------------- CMS Query helpers -------------------
def dkan_query_body(city: str, state: str, specialty_display: str, limit=100, offset=0):
    """
    DKAN POST body: AND all top-level conditions; create an OR group for specialty.
    We search using CMS_SEARCH_TERMS so we match CMS wording (e.g., THERAP).
    """
    # Determine the best search token for CMS
    search_token = CMS_SEARCH_TERMS.get(specialty_display, specialty_display.upper())

    return {
        "limit": limit,
        "offset": offset,
        "keys": True,
        "results": True,
        "count": False,
        "schema": False,
        "conditions": [
            {"property": "citytown", "value": city.upper().strip(), "operator": "="},
            {"property": "state", "value": state.upper().strip(), "operator": "="},
            {
                "groupOperator": "or",
                "conditions": [
                    {"property": "pri_spec", "value": search_token, "operator": "contains"},
                    {"property": "sec_spec_all", "value": search_token, "operator": "contains"},
                ],
            },
        ],
    }

def query_cms(city: str, state: str, specialty_display: str, size=100):
    """
    POST to DKAN (most reliable). If ~1500 rows come back, we re-request a smaller window
    and locally re-check for safety. Returns a list[str] lines to render.
    """
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if CMS_API_KEY:
        headers["X-API-KEY"] = CMS_API_KEY

    body = dkan_query_body(city, state, specialty_display, limit=size, offset=0)

    try:
        r = requests.post(CMS_DATASTORE_POST, json=body, headers=headers, timeout=20)
        r.raise_for_status()
        payload = r.json()
        rows = payload.get("results", payload)

        # Safety: if filters ignored (nationwide ~1500), re-fetch smaller & filter locally
        if isinstance(rows, list) and len(rows) >= 1000:
            body_small = dkan_query_body(city, state, specialty_display, limit=500, offset=0)
            r2 = requests.post(CMS_DATASTORE_POST, json=body_small, headers=headers, timeout=20)
            r2.raise_for_status()
            rows = r2.json().get("results", [])

            # Local sanity check
            needle = CMS_SEARCH_TERMS.get(specialty_display, specialty_display.upper())
            filtered = []
            for p in rows:
                c = (p.get("citytown") or "").strip().upper()
                s = (p.get("state") or "").strip().upper()
                pri = (p.get("pri_spec") or "").upper()
                sec = (p.get("sec_spec_all") or "").upper()
                if c == city.upper().strip() and s == state.upper().strip() and (needle in pri or needle in sec):
                    filtered.append(p)
            rows = filtered[:size]

        # Format lines for UI
        out = []
        for p in rows[:size]:
            name = f"Dr. {(p.get('provider_first_name') or '').strip()} {(p.get('provider_last_name') or '').strip()}".strip()
            spec = (p.get("pri_spec") or p.get("sec_spec_all") or "").strip()
            c = (p.get("citytown") or "").title()
            st = (p.get("state") or "").upper()
            phone = (p.get("telephone_number") or "").strip()
            out.append(f"{name} — {spec} | {c}, {st} | {phone}")
        return out

    except Exception as e:
        print("CMS query error:", e)
        return None

# ------------------- Flask views -------------------
@app.route("/")
def home():
    return render_template("chat.html")

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json() or {}
    user_msg = (data.get("question") or "").strip()
    if not user_msg:
        return jsonify({"answer":
            "Please enter your city and state (e.g., Boston, MA).\n"
            "Then tell me the kind of doctor or health concern (e.g., cardiology, pediatrics)."
        })

    # Handle “more” pagination
    if user_msg.lower() in {"more", "show more", "show all"}:
        if not user_context["last_results"]:
            return jsonify({"answer": "There isn’t anything more to show yet. Try searching first."})
        start = user_context["last_shown"]
        chunk = user_context["last_results"][start:start+25]
        if not chunk:
            return jsonify({"answer": "You’ve reached the end of the list."})

        user_context["last_shown"] += len(chunk)
        listing = "\n".join([f"{i+1+start}. {line}" for i, line in enumerate(chunk)])
        more_left = user_context["last_shown"] < len(user_context["last_results"])
        suffix = "\n\nType “more” to see additional results." if more_left else ""
        place = f"{(user_context['city'] or '').title()}, {user_context['state'] or ''}".strip(", ")
        spec_label = user_context["specialty"] or "your specialty"
        return jsonify({"answer":
            f"Showing {len(chunk)} more in {place} (spec contains “{spec_label}”):\n\n{listing}{suffix}"
        })

    # Extract any new info from this turn
    turn_city, turn_state, turn_zip, turn_spec = extract_from_turn(user_msg)

    # Update specialty if detected
    if turn_spec:
        user_context["specialty"] = turn_spec

    # Update location cautiously
    if turn_state:
        user_context["state"] = turn_state
    if turn_city:
        user_context["city"] = turn_city
    if turn_zip:
        user_context["zip"] = turn_zip

    city = user_context["city"]
    state = user_context["state"]
    spec_display = user_context["specialty"]

    # Conversation flow
    if not city and not state:
        return jsonify({"answer":
            "Please enter your city and state (e.g., Boston, MA).\n"
            "Then tell me the kind of doctor or health concern (e.g., cardiology, pediatrics)."
        })

    if city and not state:
        return jsonify({"answer": f"Great — {city.title()}.\nPlease also share the state (e.g., MA or Massachusetts)."})

    if state and not city:
        return jsonify({"answer": f"Got it — {state}.\nPlease also share your city (e.g., Boston)."})

    # We have both city + state
    place = f"{city.title()}, {state}"

    if not spec_display:
        return jsonify({"answer":
            f"Great — {place}.\nWhat kind of doctor or health concern? (e.g., cardiology, pediatrics, orthopedics)"
        })

    # Run search
    results = query_cms(city, state, spec_display, size=200)  # keep 200 for “more”
    if results is None:
        return jsonify({"answer": "Sorry, something went wrong fetching results. Please try again."})

    if not results:
        return jsonify({"answer":
            f"Sorry, I couldn’t find any matches in {place} for “{spec_display}”.\n"
            "Try a nearby city, a different specialty, or rephrase the specialty."
        })

    # Cache for “more”
    user_context["last_results"] = results[:]  # copy
    user_context["last_shown"] = min(25, len(results))

    shown = results[:25]
    listing = "\n".join([f"{i+1}. {line}" for i, line in enumerate(shown)])
    suffix = "\n\nType “more” to see additional results." if len(results) > 25 else ""
    return jsonify({"answer":
        f"Found {len(results)} providers in {place} (spec contains “{spec_display}”) — showing {len(shown)}:\n\n"
        f"{listing}{suffix}"
    })

# ------------------- Run -------------------
if __name__ == "__main__":
    # Ensure templates folder has chat.html from your earlier setup
    app.run(debug=True)
