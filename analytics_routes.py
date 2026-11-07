from flask import Blueprint, jsonify
from database import query_db
from auth_helper import login_required

analytics_bp = Blueprint("analytics_bp", __name__, url_prefix="/analytics")

@analytics_bp.route("/farmer-summary", methods=["GET"])
@login_required
def farmer_summary(user):
    user_id = user['id']
    stats = query_db("""
        SELECT 
            COUNT(id) as total_orders,
            COALESCE(SUM(crop_total_price), 0.0) as total_earnings
        FROM orders WHERE farmer_id = ? AND status = 'delivered'
    """, (user_id,), one=True)

    return jsonify({"status": "success", "data": stats or {"total_orders": 0, "total_earnings": 0.0}})
