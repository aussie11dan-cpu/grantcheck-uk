import csv
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder=".")
CORS(app)

CSV_FILE = "leads.csv"
CSV_HEADERS = [
    "submitted_at", "name", "email", "phone", "postcode",
    "property_type", "ownership", "benefits", "heating_type",
    "score",
]


def score_lead(data):
    """Score a lead as HOT, WARM, or COLD.

    HOT  = owner + receives benefits (proxy for income under 31k)
           OR owner + heating is electric/storage/none (heat-pump candidate)
    WARM = owner + no benefits (proxy for 31k-50k)
    COLD = everything else (tenants, landlords, etc.)
    """
    ownership = data.get("ownership", "")
    benefits = data.get("benefits", "")
    heating = data.get("heating_type", "")

    is_owner = ownership == "owner"
    on_benefits = benefits not in ("none", "")
    heat_pump_candidate = heating in ("electric", "storage", "none")

    if is_owner and (on_benefits or heat_pump_candidate):
        return "HOT"
    if is_owner:
        return "WARM"
    return "COLD"


def ensure_csv():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/submit", methods=["POST"])
def submit():
    body = request.get_json(silent=True)
    if not body:
        return jsonify(success=False, message="Invalid JSON body."), 400

    # Map frontend field names to internal names
    data = {
        "name": (body.get("fullName") or "").strip(),
        "email": (body.get("email") or "").strip(),
        "phone": (body.get("phone") or "").strip(),
        "postcode": (body.get("postcode") or "").strip().upper(),
        "property_type": body.get("propertyType", ""),
        "ownership": body.get("ownership", ""),
        "benefits": body.get("benefits", ""),
        "heating_type": body.get("heating", ""),
    }

    # Validate required fields
    required = ["name", "phone", "postcode"]
    missing = [f for f in required if not data[f]]
    if missing:
        return jsonify(
            success=False,
            message=f"Missing required fields: {', '.join(missing)}",
        ), 400

    data["score"] = score_lead(data)

    # Append to CSV
    ensure_csv()
    with open(CSV_FILE, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.utcnow().isoformat(),
            data["name"],
            data["email"],
            data["phone"],
            data["postcode"],
            data["property_type"],
            data["ownership"],
            data["benefits"],
            data["heating_type"],
            data["score"],
        ])

    return jsonify(
        success=True,
        message="Thank you! We'll be in touch shortly with your eligibility results.",
        score=data["score"],
    )


if __name__ == "__main__":
    ensure_csv()
    app.run(debug=True, port=5000)
