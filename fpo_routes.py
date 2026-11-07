from flask import Blueprint, request, jsonify
from database import query_db, execute_db
from auth_helper import login_required

fpo_profile_bp = Blueprint("fpo_profile_bp", __name__, url_prefix="/fpo/profile-legacy")

def api_response(status, data=None, message="", http_status=200):
    return jsonify({"status": status, "data": data, "message": message}), http_status

@fpo_profile_bp.route("", methods=["GET", "POST"])
@login_required
def manage_fpo(user):
    user_id = user['id']

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        execute_db("""
            UPDATE fpo_profiles
            SET fpo_name = ?, registration_number = ?, district = ?, state = ?, pincode = ?,
                contact_person_name = ?, bank_account_no = ?, ifsc_code = ?
            WHERE user_id = ?
        """, (
            payload.get("fpo_name"), payload.get("registration_number"),
            payload.get("district"), payload.get("state"), payload.get("pincode"),
            payload.get("contact_person"), payload.get("bank_account_no"), payload.get("ifsc_code"),
            user_id
        ))
        return api_response("success", message="FPO profile saved.")

    fpo = query_db("SELECT * FROM fpo_profiles WHERE user_id = ?", (user_id,), one=True)
    return api_response("success", data=dict(fpo) if fpo else {})
