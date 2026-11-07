from flask import Blueprint, jsonify
from database import query_db
from auth_helper import login_required

orders_bp = Blueprint("orders_bp", __name__, url_prefix="/orders-legacy")

def api_response(status, data=None, message="", http_status=200):
    return jsonify({"status": status, "data": data, "message": message}), http_status

@orders_bp.route("", methods=["GET"])
@login_required
def get_orders(user):
    user_id = user['id']
    orders = query_db(
        "SELECT * FROM orders WHERE farmer_id = ? OR buyer_id = ? ORDER BY created_at DESC",
        (user_id, user_id)
    )
    return api_response("success", data=orders)
