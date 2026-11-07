import secrets
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db, execute_db
from auth_helper import roles_required, generate_token

admin_bp = Blueprint('admin_bp', __name__, url_prefix='/admin')

@admin_bp.route('/auth/login', methods=['POST'])
def admin_login():
    data = request.get_json(silent=True) or {}
    email = str(data.get('email', '')).strip()
    password = str(data.get('password', '')).strip()

    admin = query_db("SELECT * FROM users WHERE email = ? AND role = 'admin'", (email,), one=True)
    if not admin or not check_password_hash(admin['password_hash'], password):
        return jsonify({"status": "error", "message": "Invalid administrator email or password."}), 401

    if admin['approval_status'] == 'blocked' or admin['is_blocked']:
        return jsonify({"status": "error", "message": "Admin account is blocked."}), 403

    token = generate_token(admin)

    return jsonify({
        "status": "success",
        "message": "Admin authenticated.",
        "token": token,
        "admin": {
            "id": admin['id'],
            "email": admin['email'],
            "role": admin['role'],
            "subtype": admin['subtype'],  # super_admin or moderator
            "approval_status": admin['approval_status']
        }
    }), 200

@admin_bp.route('/dashboard', methods=['GET'])
@roles_required(allowed_roles=['admin'])
def admin_dashboard(admin):
    # Total users by type
    farmers_cnt = query_db("SELECT COUNT(*) as c FROM users WHERE subtype = 'farmer'", one=True)['c']
    fpos_cnt = query_db("SELECT COUNT(*) as c FROM users WHERE subtype = 'fpo'", one=True)['c']
    retail_cnt = query_db("SELECT COUNT(*) as c FROM users WHERE subtype = 'retail_buyer'", one=True)['c']
    bulk_cnt = query_db("SELECT COUNT(*) as c FROM users WHERE subtype = 'bulk_buyer'", one=True)['c']
    drivers_cnt = query_db("SELECT COUNT(*) as c FROM users WHERE subtype = 'driver'", one=True)['c']

    # Other cards
    active_listings_cnt = query_db("SELECT COUNT(*) as c FROM listings WHERE status = 'active'", one=True)['c']

    today_str = datetime.now().strftime('%Y-%m-%d')
    orders_today_cnt = query_db("SELECT COUNT(*) as c FROM orders WHERE DATE(created_at) = ?", (today_str,), one=True)['c']
    orders_delivered_cnt = query_db("SELECT COUNT(*) as c FROM orders WHERE status = 'delivered'", one=True)['c']

    pending_verifications_cnt = query_db("SELECT COUNT(*) as c FROM users WHERE approval_status = 'pending'", one=True)['c']
    open_issues_cnt = query_db("SELECT COUNT(*) as c FROM issues WHERE status = 'open'", one=True)['c']

    # Chart 1: Orders per day (last 7 days)
    orders_per_day = query_db("""
        SELECT DATE(created_at) as order_date, COUNT(*) as order_count, COALESCE(SUM(total_amount), 0.0) as revenue
        FROM orders
        GROUP BY DATE(created_at)
        ORDER BY order_date DESC LIMIT 7
    """)

    # Chart 2: Farmer earnings vs mandi price
    mandi_comp = query_db("""
        SELECT l.crop_name, AVG(o.unit_price) as avg_farmer_price, AVG(l.mandi_price_hint) as avg_mandi_price
        FROM orders o
        JOIN listings l ON o.listing_id = l.id
        GROUP BY l.crop_name
        LIMIT 6
    """)

    # Total buyer savings vs market price
    total_savings = 0.0
    for m in mandi_comp:
        diff = float(m['avg_mandi_price'] or 0) - float(m['avg_farmer_price'] or 0)
        if diff > 0:
            total_savings += diff * 100

    # Orders stuck for too long (in 'new' or 'accepted' state created > 1 day ago)
    stuck_threshold = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    stuck_orders = query_db("""
        SELECT o.id, o.quantity, o.unit, o.status, o.created_at, l.crop_name,
               fu.phone as farmer_phone, bu.phone as buyer_phone
        FROM orders o
        JOIN listings l ON o.listing_id = l.id
        JOIN users fu ON o.farmer_id = fu.id
        JOIN users bu ON o.buyer_id = bu.id
        WHERE o.status IN ('new', 'accepted') AND o.created_at < ?
        ORDER BY o.created_at ASC
    """, (stuck_threshold,))

    return jsonify({
        "status": "success",
        "data": {
            "admin_level": admin['subtype'],
            "metrics": {
                "users_by_type": {
                    "farmers": farmers_cnt,
                    "fpos": fpos_cnt,
                    "retail_buyers": retail_cnt,
                    "bulk_buyers": bulk_cnt,
                    "drivers": drivers_cnt,
                    "total": farmers_cnt + fpos_cnt + retail_cnt + bulk_cnt + drivers_cnt
                },
                "active_listings": active_listings_cnt,
                "orders_today": orders_today_cnt,
                "orders_delivered": orders_delivered_cnt,
                "pending_verifications": pending_verifications_cnt,
                "open_issues": open_issues_cnt,
                "total_buyer_savings": round(total_savings, 2)
            },
            "charts": {
                "orders_per_day": orders_per_day,
                "farmer_vs_mandi": mandi_comp
            },
            "stuck_orders": stuck_orders
        }
    }), 200

# ----------------- Verification Queue -----------------

@admin_bp.route('/verifications', methods=['GET'])
@roles_required(allowed_roles=['admin'])
def get_verification_queue(admin):
    target_type = request.args.get('type', 'all')  # farmers, fpos, bulk_buyers, drivers

    query = "SELECT id, phone, email, role, subtype, approval_status, created_at FROM users WHERE approval_status = 'pending'"
    params = []

    if target_type == 'farmers':
        query += " AND subtype = 'farmer'"
    elif target_type == 'fpos':
        query += " AND subtype = 'fpo'"
    elif target_type == 'bulk_buyers':
        query += " AND subtype = 'bulk_buyer'"
    elif target_type == 'drivers':
        query += " AND subtype = 'driver'"

    query += " ORDER BY created_at ASC"
    pending_users = query_db(query, params)

    detailed_queue = []
    for u in pending_users:
        u_dict = dict(u)
        uid = u['id']
        if u['subtype'] == 'farmer':
            u_dict['details'] = query_db("SELECT * FROM farmer_profiles WHERE user_id = ?", (uid,), one=True)
        elif u['subtype'] == 'fpo':
            u_dict['details'] = query_db("SELECT * FROM fpo_profiles WHERE user_id = ?", (uid,), one=True)
        elif u['subtype'] == 'bulk_buyer':
            u_dict['details'] = query_db("SELECT * FROM buyer_profiles WHERE user_id = ?", (uid,), one=True)
        elif u['subtype'] == 'driver':
            u_dict['details'] = query_db("SELECT * FROM driver_profiles WHERE user_id = ?", (uid,), one=True)
        detailed_queue.append(u_dict)

    return jsonify({"status": "success", "data": detailed_queue}), 200

@admin_bp.route('/verifications/<int:user_id>/action', methods=['POST'])
@roles_required(allowed_roles=['admin'])
def action_verification(admin, user_id):
    data = request.get_json(silent=True) or {}
    action = data.get('action')  # approve or reject
    reason = str(data.get('reason', '')).strip()

    if action not in ['approve', 'reject']:
        return jsonify({"status": "error", "message": "Action must be 'approve' or 'reject'."}), 400

    if action == 'reject' and not reason:
        return jsonify({"status": "error", "message": "Rejection reason is required."}), 400

    target_user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if not target_user:
        return jsonify({"status": "error", "message": "Target user not found."}), 404

    new_status = 'verified' if action == 'approve' else 'rejected'
    execute_db("UPDATE users SET approval_status = ?, rejection_reason = ? WHERE id = ?", (new_status, reason if action == 'reject' else None, user_id))

    # Send Notification to user (Step 4.5: "User gets a notification either way")
    notif_msg = "Congratulations! Your account has been verified by the administrator. You now have full access." if action == 'approve' else f"Your account application was reviewed and could not be approved. Reason: {reason}"
    execute_db("""
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, ?, ?, 'system')
    """, (user_id, f"Account {new_status.title()}", notif_msg))

    # Audit log
    execute_db("""
        INSERT INTO admin_audit_logs (admin_id, action, target_entity, target_id, details)
        VALUES (?, ?, 'user_verification', ?, ?)
    """, (admin['id'], f"{action}_user", user_id, f"Set status to {new_status}. Reason: {reason}"))

    return jsonify({
        "status": "success",
        "message": f"User application marked as {new_status}."
    }), 200

# ----------------- User Management -----------------

@admin_bp.route('/users', methods=['GET'])
@roles_required(allowed_roles=['admin'])
def list_users(admin):
    search = request.args.get('search', '').strip()
    role_filter = request.args.get('subtype', '').strip()
    status_filter = request.args.get('status', '').strip()

    query = "SELECT id, phone, email, role, subtype, approval_status, is_blocked, created_at FROM users WHERE role != 'admin'"
    params = []

    if search:
        query += " AND (phone LIKE ? OR email LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if role_filter and role_filter != 'all':
        query += " AND subtype = ?"
        params.append(role_filter)
    if status_filter and status_filter != 'all':
        query += " AND approval_status = ?"
        params.append(status_filter)

    query += " ORDER BY created_at DESC"
    users = query_db(query, params)

    return jsonify({"status": "success", "data": users}), 200

@admin_bp.route('/users/<int:user_id>/block-toggle', methods=['POST'])
@roles_required(allowed_roles=['admin'])
def toggle_user_block(admin, user_id):
    target = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
    if not target:
        return jsonify({"status": "error", "message": "User not found."}), 404

    is_currently_blocked = target['approval_status'] == 'blocked' or target['is_blocked'] == 1
    new_blocked_val = 0 if is_currently_blocked else 1
    new_status = 'verified' if is_currently_blocked else 'blocked'

    execute_db("UPDATE users SET is_blocked = ?, approval_status = ? WHERE id = ?", (new_blocked_val, new_status, user_id))

    execute_db("""
        INSERT INTO admin_audit_logs (admin_id, action, target_entity, target_id, details)
        VALUES (?, ?, 'users', ?, ?)
    """, (admin['id'], "unblock" if is_currently_blocked else "block", user_id, f"Status updated to {new_status}"))

    return jsonify({
        "status": "success",
        "message": f"User has been {'unblocked' if is_currently_blocked else 'blocked'}."
    }), 200

# ----------------- Listing Moderation -----------------

@admin_bp.route('/listings', methods=['GET'])
@roles_required(allowed_roles=['admin'])
def list_all_listings(admin):
    listings = query_db("""
        SELECT l.*, fu.phone as farmer_phone, fu.approval_status as farmer_status,
               fp.full_name as farmer_name
        FROM listings l
        JOIN users fu ON l.farmer_id = fu.id
        LEFT JOIN farmer_profiles fp ON fu.id = fp.user_id
        ORDER BY l.created_at DESC
    """)
    return jsonify({"status": "success", "data": listings}), 200

@admin_bp.route('/listings/<int:listing_id>/moderate', methods=['POST'])
@roles_required(allowed_roles=['admin'])
def moderate_listing(admin, listing_id):
    data = request.get_json(silent=True) or {}
    action = data.get('action')  # pause, remove, restore
    reason = str(data.get('reason', '')).strip()

    if action not in ['pause', 'remove', 'restore']:
        return jsonify({"status": "error", "message": "Action must be pause, remove, or restore."}), 400

    new_status = 'active'
    if action == 'pause': new_status = 'paused'
    elif action == 'remove': new_status = 'removed'

    execute_db("UPDATE listings SET status = ?, flagged_reason = ? WHERE id = ?", (new_status, reason, listing_id))

    execute_db("""
        INSERT INTO admin_audit_logs (admin_id, action, target_entity, target_id, details)
        VALUES (?, ?, 'listings', ?, ?)
    """, (admin['id'], f"listing_{action}", listing_id, reason))

    return jsonify({"status": "success", "message": f"Listing {action}d successfully."}), 200

# ----------------- Issues Moderation -----------------

@admin_bp.route('/issues', methods=['GET'])
@roles_required(allowed_roles=['admin'])
def get_issues(admin):
    issues = query_db("""
        SELECT i.*, o.quantity, o.unit, o.total_amount,
               ru.phone as reporter_phone
        FROM issues i
        JOIN orders o ON i.order_id = o.id
        JOIN users ru ON i.reporter_user_id = ru.id
        ORDER BY i.created_at DESC
    """)
    return jsonify({"status": "success", "data": issues}), 200

@admin_bp.route('/issues/<int:issue_id>/resolve', methods=['POST'])
@roles_required(allowed_roles=['admin'])
def resolve_issue(admin, issue_id):
    data = request.get_json(silent=True) or {}
    admin_notes = str(data.get('admin_notes', '')).strip()
    resolution = data.get('resolution', 'resolved')  # resolved or dismissed

    execute_db("UPDATE issues SET status = ?, admin_notes = ? WHERE id = ?", (resolution, admin_notes, issue_id))
    return jsonify({"status": "success", "message": f"Issue marked as {resolution}."}), 200

# ----------------- Admin Invites (Super Admin Only) -----------------

@admin_bp.route('/invites', methods=['GET', 'POST'])
@roles_required(allowed_roles=['admin'])
def manage_admin_invites(admin):
    if admin['subtype'] != 'super_admin':
        return jsonify({"status": "error", "message": "Only Super Admins can invite new administrators."}), 403

    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        email = str(data.get('email', '')).strip()
        admin_level = data.get('admin_level', 'moderator')  # super_admin or moderator

        if not email:
            return jsonify({"status": "error", "message": "Email is required to send invite."}), 400

        invite_code = secrets.token_hex(8)
        execute_db("""
            INSERT INTO admin_invites (inviter_admin_id, invite_code, email, admin_level)
            VALUES (?, ?, ?, ?)
        """, (admin['id'], invite_code, email, admin_level))

        return jsonify({
            "status": "success",
            "message": f"Admin invite generated for {email}.",
            "invite_code": invite_code
        }), 201

    invites = query_db("SELECT * FROM admin_invites ORDER BY created_at DESC")
    return jsonify({"status": "success", "data": invites}), 200
