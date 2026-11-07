from flask import Blueprint, request, jsonify
from database import query_db, execute_db
from auth_helper import login_required

listings_bp = Blueprint("listings_bp", __name__, url_prefix="/listings-legacy")

def api_response(status, data=None, message="", http_status=200):
    return jsonify({"status": status, "data": data, "message": message}), http_status

@listings_bp.route("", methods=["GET", "POST"])
def handle_listings():
    if request.method == "POST":
        return api_response("error", message="Please use /farmer/listings endpoint for validated listing publishing.", http_status=400)

    listings = query_db("SELECT * FROM listings WHERE status = 'active' ORDER BY created_at DESC")
    return api_response("success", data=listings)
