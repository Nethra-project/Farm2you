from flask import Blueprint, request, jsonify
from database import query_db, execute_db
from auth_helper import get_current_user, login_required

utils_bp = Blueprint('utils_bp', __name__, url_prefix='/utils')

@utils_bp.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "success", "message": "Farm2you API Engine Healthy."}), 200

@utils_bp.route('/mandi-prices', methods=['GET'])
def get_mandi_prices():
    crop = request.args.get('crop')
    district = request.args.get('district')

    query = "SELECT * FROM mandi_prices WHERE 1=1"
    params = []
    if crop:
        query += " AND crop_name LIKE ?"
        params.append(f"%{crop}%")
    if district:
        query += " AND district LIKE ?"
        params.append(f"%{district}%")

    query += " ORDER BY date DESC, crop_name ASC"
    prices = query_db(query, params)
    return jsonify({"status": "success", "data": prices}), 200

@utils_bp.route('/notifications', methods=['GET'])
@login_required
def get_user_notifications(user):
    notifications = query_db(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
        (user['id'],)
    )
    return jsonify({"status": "success", "data": notifications}), 200

@utils_bp.route('/notifications/<int:notif_id>/read', methods=['POST'])
@login_required
def mark_notification_read(user, notif_id):
    execute_db("UPDATE notifications SET is_read = 1 WHERE id = ? AND user_id = ?", (notif_id, user['id']))
    return jsonify({"status": "success", "message": "Notification marked read."}), 200

@utils_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    user_id = user['id'] if user else 1  # default or system

    subject = data.get('subject', 'General Feedback')
    category = data.get('category', 'general')
    message = str(data.get('message', '')).strip()
    rating = int(data.get('rating', 5))

    if not message:
        return jsonify({"status": "error", "message": "Feedback message cannot be empty."}), 400

    execute_db("""
        INSERT INTO feedback (user_id, subject, category, message, rating)
        VALUES (?, ?, ?, ?, ?)
    """, (user_id, subject, category, message, rating))

    return jsonify({"status": "success", "message": "Thank you for your feedback! Our support team has received it."}), 201

@utils_bp.route('/languages', methods=['GET'])
def get_supported_languages():
    return jsonify({
        "status": "success",
        "languages": [
            {"code": "en", "name": "English"},
            {"code": "hi", "name": "हिन्दी (Hindi)"},
            {"code": "ta", "name": "தமிழ் (Tamil)"},
            {"code": "te", "name": "తెలుగు (Telugu)"}
        ]
    }), 200
