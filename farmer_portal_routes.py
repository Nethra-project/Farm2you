from datetime import datetime, date
import json
import random
from flask import Blueprint, request, jsonify
from database import query_db, execute_db
from auth_helper import login_required, roles_required

farmer_bp = Blueprint('farmer_bp', __name__, url_prefix='/farmer')

@farmer_bp.route('/dashboard', methods=['GET'])
@roles_required(allowed_roles=['producer'])
def farmer_dashboard(user):
    user_id = user['id']
    is_fpo = user['subtype'] == 'fpo'

    # Profile lookup
    if is_fpo:
        profile = query_db("SELECT * FROM fpo_profiles WHERE user_id = ?", (user_id,), one=True) or {}
        crops_str = profile.get('crops_handled', '')
    else:
        profile = query_db("SELECT * FROM farmer_profiles WHERE user_id = ?", (user_id,), one=True) or {}
        crops_str = profile.get('crops_grown', '')

    # 1. Summary Cards
    active_listings_count = query_db(
        "SELECT COUNT(*) as count FROM listings WHERE farmer_id = ? AND status = 'active'",
        (user_id,), one=True
    )['count']

    new_orders_count = query_db(
        "SELECT COUNT(*) as count FROM orders WHERE farmer_id = ? AND status = 'new'",
        (user_id,), one=True
    )['count']

    in_progress_count = query_db(
        "SELECT COUNT(*) as count FROM orders WHERE farmer_id = ? AND status IN ('accepted', 'ready_for_pickup', 'driver_assigned', 'picked_up', 'out_for_delivery')",
        (user_id,), one=True
    )['count']

    earnings_stat = query_db(
        "SELECT COALESCE(SUM(crop_total_price), 0.0) as total FROM orders WHERE farmer_id = ? AND status = 'delivered'",
        (user_id,), one=True
    )
    total_earnings = earnings_stat['total'] if earnings_stat else 0.0

    # 2. Today's mandi price for his crops
    user_crops = [c.strip() for c in crops_str.split(',') if c.strip()]
    district = profile.get('district', '')

    mandi_prices = []
    if user_crops:
        placeholders = ','.join(['?'] * len(user_crops))
        query = f"SELECT * FROM mandi_prices WHERE crop_name IN ({placeholders})"
        params = list(user_crops)
        if district:
            query += " AND district = ?"
            params.append(district)
        query += " ORDER BY date DESC LIMIT 6"
        mandi_prices = query_db(query, params)

    if not mandi_prices:
        # Fallback to general mandi prices
        mandi_prices = query_db("SELECT * FROM mandi_prices ORDER BY date DESC LIMIT 6")

    # 3. Recent notifications
    notifications = query_db(
        "SELECT * FROM notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
        (user_id,)
    )

    return jsonify({
        "status": "success",
        "data": {
            "account_status": user['approval_status'],
            "is_verified": user['approval_status'] == 'verified',
            "is_fpo": is_fpo,
            "profile": profile,
            "summary": {
                "active_listings": active_listings_count,
                "new_orders": new_orders_count,
                "in_progress_orders": in_progress_count,
                "total_earnings": round(total_earnings, 2)
            },
            "today_mandi_prices": mandi_prices,
            "recent_notifications": notifications
        }
    }), 200

@farmer_bp.route('/listings', methods=['GET', 'POST'])
@roles_required(allowed_roles=['producer'])
def handle_listings(user):
    user_id = user['id']

    if request.method == 'POST':
        # Step 3 check: "Until approved, the dashboard opens but the Add Listing button is locked with a message."
        if user['approval_status'] != 'verified':
            return jsonify({
                "status": "error",
                "message": "Account pending administrative approval. Adding listings is locked until your account is verified."
            }), 403

        data = request.get_json(silent=True) or {}
        crop_name = str(data.get('crop_name', '')).strip()
        variety = str(data.get('variety', '')).strip()
        category = str(data.get('category', 'vegetables')).strip()
        quantity = float(data.get('quantity', 0) or 0)
        unit = str(data.get('unit', 'kg')).strip()
        quality_grade = str(data.get('quality_grade', 'A')).strip()
        harvest_date = data.get('harvest_date') or str(date.today())
        available_from = data.get('available_from') or str(date.today())
        available_until = data.get('available_until')
        asking_price = float(data.get('asking_price_per_kg', 0) or 0)
        mandi_hint = float(data.get('mandi_price_hint', 0) or 0)
        min_order_qty = float(data.get('min_order_qty', 1) or 1)
        max_order_qty = float(data.get('max_order_qty', 0) or 0) if data.get('max_order_qty') else None
        pickup_location = str(data.get('pickup_location', '')).strip()
        description = str(data.get('description', '')).strip()
        photo_urls = data.get('photo_urls', [])
        if isinstance(photo_urls, list):
            photo_urls_str = json.dumps(photo_urls)
        else:
            photo_urls_str = str(photo_urls)

        fpo_member_id = data.get('fpo_member_id')
        is_pooled = 1 if data.get('is_pooled') else 0

        if not crop_name or quantity <= 0 or asking_price <= 0:
            return jsonify({"status": "error", "message": "Crop name, valid quantity and asking price are required."}), 400

        listing_id, _ = execute_db("""
            INSERT INTO listings (
                farmer_id, fpo_member_id, is_pooled, crop_name, variety, category,
                quantity, quantity_left, unit, quality_grade, harvest_date,
                available_from, available_until, asking_price_per_kg, mandi_price_hint,
                min_order_qty, max_order_qty, pickup_location, photo_urls, description, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
        """, (
            user_id, fpo_member_id, is_pooled, crop_name, variety, category,
            quantity, quantity, unit, quality_grade, harvest_date,
            available_from, available_until, asking_price, mandi_hint,
            min_order_qty, max_order_qty, pickup_location, photo_urls_str, description
        ))

        return jsonify({
            "status": "success",
            "message": "Listing published and live!",
            "listing_id": listing_id
        }), 201

    # GET listings
    status_filter = request.args.get('status')
    query = "SELECT * FROM listings WHERE farmer_id = ?"
    params = [user_id]
    if status_filter and status_filter != 'all':
        query += " AND status = ?"
        params.append(status_filter)
    query += " ORDER BY created_at DESC"

    listings = query_db(query, params)
    for l in listings:
        if l['photo_urls']:
            try:
                l['photo_urls'] = json.loads(l['photo_urls'])
            except Exception:
                l['photo_urls'] = [l['photo_urls']]
        else:
            l['photo_urls'] = []

    return jsonify({"status": "success", "data": listings}), 200

@farmer_bp.route('/listings/<int:listing_id>', methods=['PUT', 'DELETE'])
@roles_required(allowed_roles=['producer'])
def modify_listing(user, listing_id):
    user_id = user['id']
    listing = query_db("SELECT * FROM listings WHERE id = ? AND farmer_id = ?", (listing_id, user_id), one=True)
    if not listing:
        return jsonify({"status": "error", "message": "Listing not found or access denied."}), 404

    if request.method == 'DELETE':
        execute_db("DELETE FROM listings WHERE id = ?", (listing_id,))
        return jsonify({"status": "success", "message": "Listing removed."}), 200

    # PUT update
    data = request.get_json(silent=True) or {}
    new_status = data.get('status', listing['status'])  # active, paused, sold_out
    price = float(data.get('asking_price_per_kg', listing['asking_price_per_kg']))
    quantity_left = float(data.get('quantity_left', listing['quantity_left']))
    description = data.get('description', listing['description'])

    execute_db("""
        UPDATE listings
        SET status = ?, asking_price_per_kg = ?, quantity_left = ?, description = ?
        WHERE id = ?
    """, (new_status, price, quantity_left, description, listing_id))

    return jsonify({"status": "success", "message": "Listing updated successfully."}), 200

@farmer_bp.route('/orders', methods=['GET'])
@roles_required(allowed_roles=['producer'])
def farmer_orders(user):
    user_id = user['id']
    status_tab = request.args.get('status', 'all')

    query = """
        SELECT o.*, l.crop_name, l.variety, l.quality_grade,
               b.phone as buyer_raw_phone, bp.full_name as buyer_name, bp.delivery_address as buyer_area
        FROM orders o
        JOIN listings l ON o.listing_id = l.id
        JOIN users b ON o.buyer_id = b.id
        LEFT JOIN buyer_profiles bp ON b.id = bp.user_id
        WHERE o.farmer_id = ?
    """
    params = [user_id]
    if status_tab != 'all':
        query += " AND o.status = ?"
        params.append(status_tab)
    query += " ORDER BY o.created_at DESC"

    orders = query_db(query, params)

    # Step 8 rule: "Buyer phone number is revealed only after accepting"
    result = []
    for o in orders:
        o_dict = dict(o)
        if o['status'] == 'new':
            o_dict['buyer_phone'] = "Hidden until order accepted"
        else:
            o_dict['buyer_phone'] = o['buyer_raw_phone'] or o['buyer_phone']
        result.append(o_dict)

    return jsonify({"status": "success", "data": result}), 200

@farmer_bp.route('/orders/<int:order_id>/accept', methods=['POST'])
@roles_required(allowed_roles=['producer'])
def accept_order(user, order_id):
    user_id = user['id']
    order = query_db("SELECT * FROM orders WHERE id = ? AND farmer_id = ?", (order_id, user_id), one=True)
    if not order:
        return jsonify({"status": "error", "message": "Order not found."}), 404
    if order['status'] != 'new':
        return jsonify({"status": "error", "message": f"Cannot accept order in '{order['status']}' state."}), 400

    listing = query_db("SELECT * FROM listings WHERE id = ?", (order['listing_id'],), one=True)
    if not listing:
        return jsonify({"status": "error", "message": "Associated listing not found."}), 404

    # Automatic quantity left deduction (Step 7: Quantity left drops automatically as orders are accepted)
    new_qty_left = max(0.0, float(listing['quantity_left']) - float(order['quantity']))
    listing_status = 'sold_out' if new_qty_left == 0 else listing['status']
    execute_db("UPDATE listings SET quantity_left = ?, status = ? WHERE id = ?", (new_qty_left, listing_status, listing['id']))

    # Generate 6-digit pickup code
    pickup_code = str(random.randint(100000, 999999))
    delivery_code = order['delivery_code'] or str(random.randint(100000, 999999))

    # Update order status to accepted
    execute_db("""
        UPDATE orders
        SET status = 'accepted', pickup_code = ?, delivery_code = ?
        WHERE id = ?
    """, (pickup_code, delivery_code, order_id))

    # Create Delivery Job for Drivers
    # Lookup farmer location
    farmer_p = query_db("SELECT village, district FROM farmer_profiles WHERE user_id = ?", (user_id,), one=True)
    pickup_village = farmer_p['village'] if farmer_p else "Farm Location"
    pickup_district = farmer_p['district'] if farmer_p else "Farm District"

    job_exists = query_db("SELECT id FROM delivery_jobs WHERE order_id = ?", (order_id,), one=True)
    if not job_exists:
        driver_pay = 150.0 + (float(order['quantity']) * 0.5)
        execute_db("""
            INSERT INTO delivery_jobs (
                order_id, pickup_village, pickup_address, drop_city, drop_address,
                total_weight_kg, distance_km, driver_pay, farmer_pickup_code, buyer_delivery_code, status
            ) VALUES (?, ?, ?, ?, ?, ?, 15.0, ?, ?, ?, 'open')
        """, (
            order_id, pickup_village, f"{pickup_village}, {pickup_district}",
            "Delivery Hub", order['buyer_address'] or "Buyer Destination",
            float(order['quantity']), driver_pay, pickup_code, delivery_code
        ))

    # Notify Buyer
    execute_db("""
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, 'Order Accepted!', ?, 'order')
    """, (order['buyer_id'], f"Your order #{order_id} has been accepted by the producer and is being prepared."))

    return jsonify({
        "status": "success",
        "message": "Order accepted! Buyer phone is now revealed.",
        "pickup_code": pickup_code
    }), 200

@farmer_bp.route('/orders/<int:order_id>/reject', methods=['POST'])
@roles_required(allowed_roles=['producer'])
def reject_order(user, order_id):
    user_id = user['id']
    data = request.get_json(silent=True) or {}
    reason = str(data.get('reason', '')).strip()
    if not reason:
        return jsonify({"status": "error", "message": "Rejection reason is required."}), 400

    order = query_db("SELECT * FROM orders WHERE id = ? AND farmer_id = ?", (order_id, user_id), one=True)
    if not order:
        return jsonify({"status": "error", "message": "Order not found."}), 404
    if order['status'] != 'new':
        return jsonify({"status": "error", "message": "Can only reject orders in 'new' status."}), 400

    execute_db("UPDATE orders SET status = 'cancelled', rejection_reason = ? WHERE id = ?", (reason, order_id))

    # Notify buyer
    execute_db("""
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, 'Order Update', ?, 'order')
    """, (order['buyer_id'], f"Your order #{order_id} could not be accepted. Reason: {reason}"))

    return jsonify({"status": "success", "message": "Order rejected."}), 200

@farmer_bp.route('/orders/<int:order_id>/ready-pickup', methods=['POST'])
@roles_required(allowed_roles=['producer'])
def mark_ready_for_pickup(user, order_id):
    user_id = user['id']
    order = query_db("SELECT * FROM orders WHERE id = ? AND farmer_id = ?", (order_id, user_id), one=True)
    if not order:
        return jsonify({"status": "error", "message": "Order not found."}), 404

    pickup_code = order['pickup_code'] or str(random.randint(100000, 999999))
    execute_db("UPDATE orders SET status = 'ready_for_pickup', pickup_code = ? WHERE id = ?", (pickup_code, order_id))

    return jsonify({
        "status": "success",
        "message": "Marked ready for pickup. Provide this pickup code to the driver upon load handover.",
        "pickup_code": pickup_code
    }), 200

@farmer_bp.route('/earnings', methods=['GET'])
@roles_required(allowed_roles=['producer'])
def farmer_earnings(user):
    user_id = user['id']

    total_earned = query_db(
        "SELECT COALESCE(SUM(crop_total_price), 0.0) as s FROM orders WHERE farmer_id = ? AND status = 'delivered' AND payment_status = 'paid'",
        (user_id,), one=True
    )['s']

    pending_payments = query_db(
        "SELECT COALESCE(SUM(crop_total_price), 0.0) as s FROM orders WHERE farmer_id = ? AND (status != 'delivered' OR payment_status = 'unpaid') AND status NOT IN ('cancelled', 'rejected')",
        (user_id,), one=True
    )['s']

    order_history = query_db("""
        SELECT o.id, o.quantity, o.unit, o.unit_price, o.crop_total_price,
               o.payment_method, o.payment_status, o.status, o.created_at,
               l.crop_name, l.variety, l.mandi_price_hint
        FROM orders o
        JOIN listings l ON o.listing_id = l.id
        WHERE o.farmer_id = ?
        ORDER BY o.created_at DESC
    """, (user_id,))

    # Comparison vs Mandi price
    history_with_diff = []
    for item in order_history:
        it = dict(item)
        mandi = it['mandi_price_hint'] or it['unit_price']
        it['mandi_comparison_diff'] = round(it['unit_price'] - mandi, 2)
        history_with_diff.append(it)

    return jsonify({
        "status": "success",
        "data": {
            "total_earned": round(total_earned, 2),
            "pending_payments": round(pending_payments, 2),
            "completed_payments": round(total_earned, 2),
            "orders": history_with_diff
        }
    }), 200

@farmer_bp.route('/ratings', methods=['GET'])
@roles_required(allowed_roles=['producer'])
def farmer_ratings(user):
    user_id = user['id']
    ratings = query_db("""
        SELECT r.*, bp.full_name as buyer_name
        FROM ratings r
        LEFT JOIN buyer_profiles bp ON r.buyer_id = bp.user_id
        WHERE r.farmer_id = ?
        ORDER BY r.created_at DESC
    """, (user_id,))
    return jsonify({"status": "success", "data": ratings}), 200

# ----------------- FPO Extras -----------------

@farmer_bp.route('/fpo/members', methods=['GET', 'POST'])
@roles_required(allowed_roles=['producer'], allowed_subtypes=['fpo'])
def manage_fpo_members(user):
    fpo_id = user['id']
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        member_name = str(data.get('member_name', '')).strip()
        phone = str(data.get('phone', '')).strip()
        village = str(data.get('village', '')).strip()
        crops_grown = str(data.get('crops_grown', '')).strip()

        if not member_name:
            return jsonify({"status": "error", "message": "Member name is required."}), 400

        m_id, _ = execute_db("""
            INSERT INTO fpo_members (fpo_user_id, member_name, phone, village, crops_grown)
            VALUES (?, ?, ?, ?, ?)
        """, (fpo_id, member_name, phone, village, crops_grown))

        # Update member count
        cnt = query_db("SELECT COUNT(*) as c FROM fpo_members WHERE fpo_user_id = ?", (fpo_id,), one=True)['c']
        execute_db("UPDATE fpo_profiles SET member_count = ? WHERE user_id = ?", (cnt, fpo_id))

        return jsonify({"status": "success", "message": "Member added successfully.", "member_id": m_id}), 201

    members = query_db("SELECT * FROM fpo_members WHERE fpo_user_id = ? ORDER BY created_at DESC", (fpo_id,))
    return jsonify({"status": "success", "data": members}), 200

@farmer_bp.route('/fpo/members/<int:member_id>', methods=['DELETE'])
@roles_required(allowed_roles=['producer'], allowed_subtypes=['fpo'])
def delete_fpo_member(user, member_id):
    fpo_id = user['id']
    execute_db("DELETE FROM fpo_members WHERE id = ? AND fpo_user_id = ?", (member_id, fpo_id))
    cnt = query_db("SELECT COUNT(*) as c FROM fpo_members WHERE fpo_user_id = ?", (fpo_id,), one=True)['c']
    execute_db("UPDATE fpo_profiles SET member_count = ? WHERE user_id = ?", (cnt, fpo_id))
    return jsonify({"status": "success", "message": "Member removed."}), 200

@farmer_bp.route('/fpo/payment-splits', methods=['GET', 'POST'])
@roles_required(allowed_roles=['producer'], allowed_subtypes=['fpo'])
def fpo_payment_splits(user):
    fpo_id = user['id']
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        order_id = data.get('order_id')
        member_id = data.get('member_id')
        share_amount = float(data.get('share_amount', 0) or 0)
        notes = str(data.get('notes', ''))

        if not order_id or not member_id or share_amount <= 0:
            return jsonify({"status": "error", "message": "Order ID, member ID and positive share amount required."}), 400

        execute_db("""
            INSERT INTO fpo_payment_splits (order_id, fpo_user_id, member_id, share_amount, notes)
            VALUES (?, ?, ?, ?, ?)
        """, (order_id, fpo_id, member_id, share_amount, notes))

        return jsonify({"status": "success", "message": "Payment split recorded."}), 201

    splits = query_db("""
        SELECT s.*, m.member_name, o.crop_total_price
        FROM fpo_payment_splits s
        JOIN fpo_members m ON s.member_id = m.id
        JOIN orders o ON s.order_id = o.id
        WHERE s.fpo_user_id = ?
        ORDER BY s.created_at DESC
    """, (fpo_id,))
    return jsonify({"status": "success", "data": splits}), 200

