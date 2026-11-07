from flask import Blueprint, jsonify

driver_auth_bp = Blueprint("driver_auth_bp", __name__, url_prefix="/driver/auth-legacy")

@driver_auth_bp.route("/notice", methods=["GET"])
def notice():
    return jsonify({"status": "info", "message": "Unified authentication available at /auth/register and /auth/login"}), 200
