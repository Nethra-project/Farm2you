from flask import Blueprint, request, jsonify
from database import query_db, execute_db
from auth_helper import login_required

farmer_profile_bp = Blueprint("farmer_profile_bp", __name__, url_prefix="/farmer/profile-legacy")

def api_response(status, data=None, message="", http_status=200):
    return jsonify({"status": status, "data": data, "message": message}), http_status

@farmer_profile_bp.route("", methods=["GET", "POST"])
@login_required
def manage_profile(user):
    user_id = user['id']

    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        execute_db("""
            UPDATE farmer_profiles
            SET full_name = ?, village = ?, district = ?, state = ?, pincode = ?,
                crops_grown = ?, upi_id = ?, bank_account_no = ?, ifsc_code = ?
            WHERE user_id = ?
        """, (
            payload.get("full_name"), payload.get("village"), payload.get("district"),
            payload.get("state"), payload.get("pincode"), payload.get("crops_grown"),
            payload.get("upi_id"), payload.get("bank_account_no"), payload.get("ifsc_code"),
            user_id
        ))
        return api_response("success", message="Farmer profile updated.")

    profile = query_db("SELECT * FROM farmer_profiles WHERE user_id = ?", (user_id,), one=True)
    return api_response("success", data=dict(profile) if profile else {})
