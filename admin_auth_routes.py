from flask import Blueprint, jsonify

admin_auth_bp = Blueprint("admin_auth_bp", __name__, url_prefix="/admin/auth-legacy")

@admin_auth_bp.route("/notice", methods=["GET"])
def notice():
    return jsonify({"status": "info", "message": "Admin authentication available at /admin/auth/login"}), 200
