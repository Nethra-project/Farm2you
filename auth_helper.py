import functools
from flask import request, jsonify
from flask_jwt_extended import create_access_token, decode_token
from database import query_db

def generate_token(user):
    return create_access_token(
        identity=str(user['id']),
        additional_claims={
            "role": user['role'],
            "subtype": user['subtype'],
            "approval_status": user['approval_status']
        }
    )

def get_current_user():
    auth_header = request.headers.get('Authorization', '')
    token = None
    if auth_header.startswith('Bearer '):
        token = auth_header.split(' ', 1)[1].strip()
    elif 'token' in request.args:
        token = request.args.get('token')

    if not token:
        return None

    try:
        decoded = decode_token(token)
        user_id = decoded['sub']
        user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
        if user and user.get('is_blocked'):
            return None
        return user
    except Exception:
        return None

def login_required(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({"status": "error", "message": "Authentication required. Please log in."}), 401
        if user.get('approval_status') == 'blocked' or user.get('is_blocked'):
            return jsonify({"status": "error", "message": "Your account has been blocked. Contact support."}), 403
        return f(user, *args, **kwargs)
    return decorated_function

def roles_required(allowed_roles=None, allowed_subtypes=None):
    def decorator(f):
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            user = get_current_user()
            if not user:
                return jsonify({"status": "error", "message": "Authentication required. Please log in."}), 401
            if user.get('approval_status') == 'blocked' or user.get('is_blocked'):
                return jsonify({"status": "error", "message": "Your account has been blocked."}), 403

            if allowed_roles and user['role'] not in allowed_roles:
                return jsonify({"status": "error", "message": "Access forbidden: insufficient role permissions."}), 403

            if allowed_subtypes and user['subtype'] not in allowed_subtypes:
                return jsonify({"status": "error", "message": "Access forbidden: role subtype not authorized."}), 403

            return f(user, *args, **kwargs)
        return decorated_function
    return decorator

