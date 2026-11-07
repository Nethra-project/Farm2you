from datetime import datetime, date
from flask import Blueprint, request, jsonify
from database import query_db, execute_db
from auth_helper import roles_required

driver_bp = Blueprint('driver_bp', __name__, url_prefix='/driver')

@driver_bp.route('/dashboard', methods=['GET'])
@roles_required(allowed_roles=['driver'])
def driver_dashboard(user):
    user_id = user['id']
    profile = query_db("SELECT * FROM driver_profiles WHERE user_id = ?", (user_id,), one=True) or {}

    # Verification check: Step 2 "Until approved, the driver cannot see jobs."
    is_approved = user['approval_status'] == 'verified'

    today_str = datetime.now().strftime('%Y-%m-%d')

    # Metrics
    jobs_today_cnt = query_db("""
        SELECT COUNT(*) as c FROM delivery_jobs
        WHERE driver_id = ? AND DATE(created_at) = ?
    """, (user_id, today_str), one=True)['c']

    earnings_today_amt = query_db("""
        SELECT COALESCE(SUM(amount), 0.0) as amt FROM driver_earnings
        WHERE driver_id = ? AND DATE(created_at) = ?
    """, (user_id, today_str), one=True)['amt']

    total_deliveries = profile.get('total_deliveries', 0)

    # Current active job (if any)
    current_job = None
    if is_approved:
        current_job_rec = query_db("""
            SELECT j.*, o.quantity, o.unit, o.crop_total_price, o.payment_method, o.total_amount,
                   l.crop_name, l.variety,
                   fp.full_name as farmer_name, fu.phone as farmer_phone,
                   bp.full_name as buyer_name, bu.phone as buyer_phone
            FROM delivery_jobs j
            JOIN orders o ON j.order_id = o.id
            JOIN listings l ON o.listing_id = l.id
            JOIN users fu ON o.farmer_id = fu.id
            LEFT JOIN farmer_profiles fp ON fu.id = fp.user_id
            JOIN users bu ON o.buyer_id = bu.id
            LEFT JOIN buyer_profiles bp ON bu.id = bp.user_id
            WHERE j.driver_id = ? AND j.status IN ('accepted', 'picked_up')
            LIMIT 1
        """, (user_id,), one=True)

        if current_job_rec:
            current_job = dict(current_job_rec)
            # Build route optimization stops list
            current_job['stops'] = [
                {
                    "step": 1,
                    "type": "pickup",
                    "title": f"Farm: {current_job['pickup_village']}",
                    "address": current_job['pickup_address'],
                    "contact_name": current_job['farmer_name'],
                    "contact_phone": current_job['farmer_phone'],
                    "action_required": "Enter Farmer's Pickup Code"
                },
                {
                    "step": 2,
                    "type": "drop",
                    "title": f"Drop: {current_job['drop_city']}",
                    "address": current_job['drop_address'],
                    "contact_name": current_job['buyer_name'],
                    "contact_phone": current_job['buyer_phone'],
                    "action_required": "Enter Buyer's Delivery Code"
                }
            ]

    # Available jobs nearby
    available_jobs = []
    if is_approved and profile.get('is_online', 0):
        available_jobs = query_db("""
            SELECT j.*, l.crop_name, l.variety
            FROM delivery_jobs j
            JOIN orders o ON j.order_id = o.id
            JOIN listings l ON o.listing_id = l.id
            WHERE j.status = 'open' AND (j.driver_id IS NULL OR j.driver_id = ?)
            ORDER BY j.created_at DESC LIMIT 10
        """, (user_id,))

    return jsonify({
        "status": "success",
        "data": {
            "account_status": user['approval_status'],
            "is_verified": is_approved,
            "is_online": bool(profile.get('is_online', 0)),
            "profile": profile,
            "metrics": {
                "jobs_today": jobs_today_cnt,
                "earnings_today": round(earnings_today_amt, 2),
                "total_deliveries": total_deliveries
            },
            "current_job": current_job,
            "available_jobs": available_jobs
        }
    }), 200

@driver_bp.route('/toggle-online', methods=['POST'])
@roles_required(allowed_roles=['driver'])
def toggle_online(user):
    user_id = user['id']
    profile = query_db("SELECT is_online FROM driver_profiles WHERE user_id = ?", (user_id,), one=True)
    if not profile:
        return jsonify({"status": "error", "message": "Driver profile missing."}), 404

    new_state = 0 if profile['is_online'] else 1
    execute_db("UPDATE driver_profiles SET is_online = ? WHERE user_id = ?", (new_state, user_id))

    return jsonify({
        "status": "success",
        "is_online": bool(new_state),
        "message": "Status set to Online (ready for jobs)." if new_state else "Status set to Offline."
    }), 200

@driver_bp.route('/jobs/available', methods=['GET'])
@roles_required(allowed_roles=['driver'])
def get_available_jobs(user):
    # Step 2: "Until approved, the driver cannot see jobs."
    if user['approval_status'] != 'verified':
        return jsonify({
            "status": "error",
            "message": "Account pending administrative approval. Documents must be verified before seeing jobs."
        }), 403

    jobs = query_db("""
        SELECT j.*, l.crop_name, l.variety, o.quantity, o.unit
        FROM delivery_jobs j
        JOIN orders o ON j.order_id = o.id
        JOIN listings l ON o.listing_id = l.id
        WHERE j.status = 'open'
        ORDER BY j.created_at DESC
    """)
    return jsonify({"status": "success", "data": jobs}), 200

@driver_bp.route('/jobs/<int:job_id>/accept', methods=['POST'])
@roles_required(allowed_roles=['driver'])
def accept_delivery_job(user, job_id):
    user_id = user['id']
    if user['approval_status'] != 'verified':
        return jsonify({"status": "error", "message": "Cannot accept jobs: Account verification pending."}), 403

    # Check if driver already has an active job
    active = query_db("SELECT id FROM delivery_jobs WHERE driver_id = ? AND status IN ('accepted', 'picked_up')", (user_id,), one=True)
    if active:
        return jsonify({"status": "error", "message": "You already have an active job in progress."}), 400

    # First to accept gets it (Step 5.2)
    job = query_db("SELECT * FROM delivery_jobs WHERE id = ?", (job_id,), one=True)
    if not job:
        return jsonify({"status": "error", "message": "Job not found."}), 404
    if job['status'] != 'open':
        return jsonify({"status": "error", "message": "Job has already been accepted by another driver."}), 409

    execute_db("UPDATE delivery_jobs SET status = 'accepted', driver_id = ? WHERE id = ?", (user_id, job_id))
    execute_db("UPDATE orders SET driver_id = ?, status = 'driver_assigned' WHERE id = ?", (user_id, job['order_id']))

    return jsonify({"status": "success", "message": "Job accepted! Proceeding to pickup location."}), 200

@driver_bp.route('/jobs/<int:job_id>/verify-pickup', methods=['POST'])
@roles_required(allowed_roles=['driver'])
def verify_farm_pickup(user, job_id):
    user_id = user['id']
    data = request.get_json(silent=True) or {}
    entered_code = str(data.get('pickup_code', '')).strip()
    photo_url = data.get('photo_url', '')

    job = query_db("SELECT * FROM delivery_jobs WHERE id = ? AND driver_id = ?", (job_id, user_id), one=True)
    if not job:
        return jsonify({"status": "error", "message": "Active job not found."}), 404

    # Validate farmer's pickup code (Step 5.5: "At the farm: enter the pickup code the farmer shows")
    if entered_code != job['farmer_pickup_code']:
        return jsonify({"status": "error", "message": "Invalid pickup code provided by farmer."}), 400

    execute_db("""
        UPDATE delivery_jobs
        SET status = 'picked_up', pickup_photo_url = ?, picked_up_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (photo_url, job_id))

    execute_db("UPDATE orders SET status = 'picked_up' WHERE id = ?", (job['order_id'],))

    return jsonify({
        "status": "success",
        "message": "Produce pickup verified! Load marked as Picked Up. Proceeding to buyer."
    }), 200

@driver_bp.route('/jobs/<int:job_id>/verify-delivery', methods=['POST'])
@roles_required(allowed_roles=['driver'])
def verify_drop_delivery(user, job_id):
    user_id = user['id']
    data = request.get_json(silent=True) or {}
    entered_code = str(data.get('delivery_code', '')).strip()
    cash_collected = float(data.get('cash_collected', 0) or 0)

    job = query_db("SELECT * FROM delivery_jobs WHERE id = ? AND driver_id = ?", (job_id, user_id), one=True)
    if not job:
        return jsonify({"status": "error", "message": "Job not found."}), 404

    # Validate buyer's delivery code (Step 5.8: "At the drop: enter the buyer's delivery code, confirm quantity")
    if entered_code != job['buyer_delivery_code']:
        return jsonify({"status": "error", "message": "Invalid delivery code provided by buyer."}), 400

    # Mark delivered
    execute_db("""
        UPDATE delivery_jobs
        SET status = 'delivered', cash_collected = ?, delivered_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (cash_collected, job_id))

    execute_db("""
        UPDATE orders
        SET status = 'delivered', payment_status = 'paid', delivered_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (job['order_id'],))

    # Record driver earning
    execute_db("""
        INSERT INTO driver_earnings (driver_id, job_id, amount, payment_status)
        VALUES (?, ?, ?, 'pending')
    """, (user_id, job_id, job['driver_pay']))

    # Increment total deliveries in driver profile
    execute_db("UPDATE driver_profiles SET total_deliveries = total_deliveries + 1 WHERE user_id = ?", (user_id,))

    return jsonify({
        "status": "success",
        "message": f"Delivery completed successfully! Payout of ₹{job['driver_pay']} credited to your account.",
        "payout_amount": job['driver_pay']
    }), 200

@driver_bp.route('/jobs/<int:job_id>/report-issue', methods=['POST'])
@roles_required(allowed_roles=['driver'])
def driver_report_issue(user, job_id):
    user_id = user['id']
    data = request.get_json(silent=True) or {}
    reason = str(data.get('reason', '')).strip()
    photo_url = data.get('photo_url', '')

    if not reason:
        return jsonify({"status": "error", "message": "Issue explanation is required."}), 400

    job = query_db("SELECT * FROM delivery_jobs WHERE id = ? AND driver_id = ?", (job_id, user_id), one=True)
    if not job:
        return jsonify({"status": "error", "message": "Job not found."}), 404

    execute_db("""
        UPDATE delivery_jobs
        SET status = 'failed', failure_reason = ?, failure_photo_url = ?
        WHERE id = ?
    """, (reason, photo_url, job_id))

    execute_db("""
        INSERT INTO issues (order_id, reporter_user_id, reporter_role, issue_type, reason, photo_url, status)
        VALUES (?, ?, 'driver', 'delivery_issue', ?, ?, 'open')
    """, (job['order_id'], user_id, reason, photo_url))

    return jsonify({"status": "success", "message": "Job issue reported and logged."}), 200

@driver_bp.route('/earnings', methods=['GET'])
@roles_required(allowed_roles=['driver'])
def driver_earnings_history(user):
    user_id = user['id']

    total_earned = query_db(
        "SELECT COALESCE(SUM(amount), 0.0) as amt FROM driver_earnings WHERE driver_id = ?",
        (user_id,), one=True
    )['amt']

    paid_amt = query_db(
        "SELECT COALESCE(SUM(amount), 0.0) as amt FROM driver_earnings WHERE driver_id = ? AND payment_status = 'paid'",
        (user_id,), one=True
    )['amt']

    pending_amt = query_db(
        "SELECT COALESCE(SUM(amount), 0.0) as amt FROM driver_earnings WHERE driver_id = ? AND payment_status = 'pending'",
        (user_id,), one=True
    )['amt']

    jobs_history = query_db("""
        SELECT j.id, j.pickup_village, j.drop_city, j.total_weight_kg, j.driver_pay,
               j.status, j.created_at, e.payment_status
        FROM delivery_jobs j
        LEFT JOIN driver_earnings e ON j.id = e.job_id
        WHERE j.driver_id = ?
        ORDER BY j.created_at DESC
    """, (user_id,))

    return jsonify({
        "status": "success",
        "data": {
            "total_earnings": round(total_earned, 2),
            "paid_earnings": round(paid_amt, 2),
            "pending_earnings": round(pending_amt, 2),
            "jobs": jobs_history
        }
    }), 200
