from flask import Blueprint, jsonify

buyer_auth_bp = Blueprint("buyer_auth_bp", __name__, url_prefix="/buyer/auth-legacy")

@buyer_auth_bp.route("/notice", methods=["GET"])
def notice():
    return jsonify({"status": "info", "message": "Unified authentication available at /auth/register and /auth/login"}), 200 
