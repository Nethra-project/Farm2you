from datetime import datetime, date, timedelta
import json
import random
from flask import Blueprint, request, jsonify
from database import query_db, execute_db
from auth_helper import login_required, roles_required

buyer_bp = Blueprint('buyer_bp', __name__, url_prefix='/buyer')

@buyer_bp.route('/dashboard', methods=['GET'])
@roles_required(allowed_roles=['consumer'])
def buyer_dashboard(user):
    user_id = user['id']
    is_bulk = user['subtype'] == 'bulk_buyer'

    profile = query_db("SELECT * FROM buyer_profiles WHERE user_id = ?", (user_id,), one=True) or {}

    # Active orders strip
    active_orders = query_db("""
        SELECT o.*, l.crop_name, l.variety, l.quality_grade, d.full_name as driver_name, d.phone as driver_phone
        FROM orders o
        JOIN listings l ON o.listing_id = l.id
        LEFT JOIN users du ON o.driver_id = du.id
        LEFT JOIN driver_profiles d ON du.id = d.user_id
        WHERE o.buyer_id = ? AND o.status NOT IN ('delivered', 'cancelled', 'rejected')
        ORDER BY o.created_at DESC LIMIT 5
    """, (user_id,))

    # Today's featured listings
    featured_listings = query_db("""
        SELECT l.*, fp.full_name as farmer_name, fp.village as farmer_village, fp.rating_avg as farmer_rating
        FROM listings l
        JOIN users u ON l.farmer_id = u.id
        LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
        WHERE l.status = 'active' AND l.quantity_left > 0
        ORDER BY l.created_at DESC LIMIT 6
    """)
    for f in featured_listings:
        if f['photo_urls']:
            try: f['photo_urls'] = json.loads(f['photo_urls'])
            except Exception: f['photo_urls'] = [f['photo_urls']]
        else: f['photo_urls'] = []

    # Saved addresses
    addresses = query_db("SELECT * FROM buyer_addresses WHERE user_id = ? ORDER BY is_default DESC", (user_id,))

    return jsonify({
        "status": "success",
        "data": {
            "is_bulk": is_bulk,
            "account_status": user['approval_status'],
            "profile": profile,
            "categories": ["vegetables", "fruits", "grains"],
            "active_orders": active_orders,
            "featured_listings": featured_listings,
            "saved_addresses": addresses
        }
    }), 200

@buyer_bp.route('/listings', methods=['GET'])
@roles_required(allowed_roles=['consumer'])
def browse_listings(user):
    search = request.args.get('search', '').strip()
    category = request.args.get('category', '').strip()
    quality_grade = request.args.get('grade', '').strip()
    district = request.args.get('district', '').strip()
    min_price = request.args.get('min_price')
    max_price = request.args.get('max_price')
    sort_by = request.args.get('sort', 'freshest')  # price_low_to_high, nearest, freshest

    query = """
        SELECT l.*, fp.full_name as farmer_name, fp.village, fp.district as farmer_district,
               fp.rating_avg as farmer_rating, fp.rating_count
        FROM listings l
        JOIN users u ON l.farmer_id = u.id
        LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
        WHERE l.status = 'active' AND l.quantity_left > 0
    """
    params = []

    if search:
        query += " AND (l.crop_name LIKE ? OR l.variety LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    if category and category != 'all':
        query += " AND l.category = ?"
        params.append(category)
    if quality_grade:
        query += " AND l.quality_grade = ?"
        params.append(quality_grade)
    if district:
        query += " AND (l.pickup_location LIKE ? OR fp.district LIKE ?)"
        params.extend([f"%{district}%", f"%{district}%"])
    if min_price:
        query += " AND l.asking_price_per_kg >= ?"
        params.append(float(min_price))
    if max_price:
        query += " AND l.asking_price_per_kg <= ?"
        params.append(float(max_price))

    if sort_by == 'price_low_to_high':
        query += " ORDER BY l.asking_price_per_kg ASC"
    elif sort_by == 'freshest':
        query += " ORDER BY l.harvest_date DESC, l.created_at DESC"
    else:
        query += " ORDER BY l.created_at DESC"

    listings = query_db(query, params)
    for l in listings:
        if l['photo_urls']:
            try: l['photo_urls'] = json.loads(l['photo_urls'])
            except Exception: l['photo_urls'] = [l['photo_urls']]
        else: l['photo_urls'] = []

    return jsonify({"status": "success", "data": listings}), 200

@buyer_bp.route('/listings/<int:listing_id>', methods=['GET'])
@roles_required(allowed_roles=['consumer'])
def listing_detail(user, listing_id):
    listing = query_db("""
        SELECT l.*, fp.full_name as farmer_name, fp.village, fp.district as farmer_district,
               fp.rating_avg as farmer_rating, fp.rating_count
        FROM listings l
        JOIN users u ON l.farmer_id = u.id
        LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
        WHERE l.id = ?
    """, (listing_id,), one=True)

    if not listing:
        return jsonify({"status": "error", "message": "Listing not found."}), 404

    listing_dict = dict(listing)
    if listing_dict['photo_urls']:
        try: listing_dict['photo_urls'] = json.loads(listing_dict['photo_urls'])
        except Exception: listing_dict['photo_urls'] = [listing_dict['photo_urls']]
    else: listing_dict['photo_urls'] = []

    # Get mandi price benchmark
    mandi = query_db(
        "SELECT * FROM mandi_prices WHERE crop_name = ? ORDER BY date DESC LIMIT 1",
        (listing_dict['crop_name'],),
        one=True
    )
    listing_dict['mandi_benchmark'] = mandi

    return jsonify({"status": "success", "data": listing_dict}), 200

@buyer_bp.route('/orders/quote-price', methods=['POST'])
@roles_required(allowed_roles=['consumer'])
def quote_order_price(user):
    data = request.get_json(silent=True) or {}
    listing_id = data.get('listing_id')
    quantity = float(data.get('quantity', 0) or 0)

    listing = query_db("SELECT * FROM listings WHERE id = ?", (listing_id,), one=True)
    if not listing:
        return jsonify({"status": "error", "message": "Listing not found."}), 404

    crop_price = quantity * float(listing['asking_price_per_kg'])
    transport_fee = 100.0 + (quantity * 1.5)  # Dynamic transport base
    platform_fee = round(crop_price * 0.02, 2)  # 2% platform fee
    total = round(crop_price + transport_fee + platform_fee, 2)

    return jsonify({
        "status": "success",
        "data": {
            "crop_price": round(crop_price, 2),
            "transport_fee": round(transport_fee, 2),
            "platform_fee": round(platform_fee, 2),
            "total_amount": total
        }
    }), 200

@buyer_bp.route('/orders', methods=['POST'])
@roles_required(allowed_roles=['consumer'])
def place_order(user):
    user_id = user['id']
    data = request.get_json(silent=True) or {}
    listing_id = data.get('listing_id')
    quantity = float(data.get('quantity', 0) or 0)
    delivery_address = str(data.get('delivery_address', '')).strip()
    delivery_date = data.get('delivery_date') or str(date.today() + timedelta(days=2))
    payment_method = str(data.get('payment_method', 'COD')).strip().upper()  # COD or UPI

    listing = query_db("SELECT * FROM listings WHERE id = ? AND status = 'active'", (listing_id,), one=True)
    if not listing:
        return jsonify({"status": "error", "message": "This produce listing is no longer active."}), 404

    # Quantity checks (Step 7: "Enter quantity (must meet the minimum order and max order qty)")
    min_order = float(listing['min_order_qty'] or 1)
    if quantity < min_order:
        return jsonify({"status": "error", "message": f"Minimum order quantity is {min_order} {listing['unit']}."}), 400

    if user['subtype'] == 'retail_buyer':
        max_order = float(listing['max_order_qty'] or 100)
        if quantity > max_order:
            return jsonify({"status": "error", "message": f"Maximum retail limit is {max_order} {listing['unit']}."}), 400

    if quantity > float(listing['quantity_left']):
        return jsonify({"status": "error", "message": f"Only {listing['quantity_left']} {listing['unit']} remaining in stock."}), 400

    # Bulk buyer check: (Step 3: "Bulk buyer: OTP, then admin approves (needed before placing large orders)")
    if user['subtype'] == 'bulk_buyer' and user['approval_status'] != 'verified':
        return jsonify({
            "status": "error",
            "message": "Bulk buyer account pending verification. Please wait for admin approval before placing orders."
        }), 403

    # Calculate final price breakdown
    crop_total = round(quantity * float(listing['asking_price_per_kg']), 2)
    transport_fee = round(100.0 + (quantity * 1.5), 2)
    platform_fee = round(crop_total * 0.02, 2)
    total_amount = round(crop_total + transport_fee + platform_fee, 2)

    # 6-digit delivery code shown to buyer, told to driver at drop
    delivery_code = str(random.randint(100000, 999999))
    pickup_code = str(random.randint(100000, 999999))

    buyer_phone = user['phone']

    order_id, _ = execute_db("""
        INSERT INTO orders (
            listing_id, farmer_id, buyer_id, quantity, unit, unit_price,
            crop_total_price, transport_fee, platform_fee, total_amount,
            payment_method, payment_status, status, buyer_address, buyer_phone,
            delivery_date, pickup_code, delivery_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unpaid', 'new', ?, ?, ?, ?, ?)
    """, (
        listing_id, listing['farmer_id'], user_id, quantity, listing['unit'],
        float(listing['asking_price_per_kg']), crop_total, transport_fee,
        platform_fee, total_amount, payment_method, delivery_address,
        buyer_phone, delivery_date, pickup_code, delivery_code
    ))

    # Notify Farmer
    execute_db("""
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, 'New Order Received', ?, 'order')
    """, (listing['farmer_id'], f"New order #{order_id} for {quantity} {listing['unit']} of {listing['crop_name']}."))

    return jsonify({
        "status": "success",
        "message": "Order placed! Waiting for farmer acceptance.",
        "data": {
            "order_id": order_id,
            "status": "placed",
            "delivery_code": delivery_code,
            "total_amount": total_amount
        }
    }), 201

@buyer_bp.route('/orders', methods=['GET'])
@roles_required(allowed_roles=['consumer'])
def buyer_orders(user):
    user_id = user['id']
    orders = query_db("""
        SELECT o.*, l.crop_name, l.variety, l.quality_grade,
               fp.full_name as farmer_name, fp.village as farmer_village,
               d.full_name as driver_name, d.vehicle_number, d.vehicle_type,
               du.phone as driver_phone
        FROM orders o
        JOIN listings l ON o.listing_id = l.id
        JOIN users fu ON o.farmer_id = fu.id
        LEFT JOIN farmer_profiles fp ON fu.id = fp.user_id
        LEFT JOIN users du ON o.driver_id = du.id
        LEFT JOIN driver_profiles d ON du.id = d.user_id
        WHERE o.buyer_id = ?
        ORDER BY o.created_at DESC
    """, (user_id,))

    return jsonify({"status": "success", "data": orders}), 200

@buyer_bp.route('/orders/<int:order_id>', methods=['GET'])
@roles_required(allowed_roles=['consumer'])
def buyer_order_detail(user, order_id):
    user_id = user['id']
    order = query_db("""
        SELECT o.*, l.crop_name, l.variety, l.quality_grade,
               fp.full_name as farmer_name, fp.village as farmer_village,
               d.full_name as driver_name, d.vehicle_number, du.phone as driver_phone
        FROM orders o
        JOIN listings l ON o.listing_id = l.id
        JOIN users fu ON o.farmer_id = fu.id
        LEFT JOIN farmer_profiles fp ON fu.id = fp.user_id
        LEFT JOIN users du ON o.driver_id = du.id
        LEFT JOIN driver_profiles d ON du.id = d.user_id
        WHERE o.id = ? AND o.buyer_id = ?
    """, (order_id, user_id), one=True)

    if not order:
        return jsonify({"status": "error", "message": "Order not found."}), 404

    # Check if rating exists
    existing_rating = query_db("SELECT rating, review FROM ratings WHERE order_id = ?", (order_id,), one=True)

    order_dict = dict(order)
    order_dict['user_rating'] = existing_rating

    return jsonify({"status": "success", "data": order_dict}), 200

@buyer_bp.route('/orders/<int:order_id>/confirm-received', methods=['POST'])
@roles_required(allowed_roles=['consumer'])
def confirm_order_received(user, order_id):
    user_id = user['id']
    order = query_db("SELECT * FROM orders WHERE id = ? AND buyer_id = ?", (order_id, user_id), one=True)
    if not order:
        return jsonify({"status": "error", "message": "Order not found."}), 404

    execute_db("UPDATE orders SET status = 'delivered', delivered_at = CURRENT_TIMESTAMP WHERE id = ?", (order_id,))
    return jsonify({"status": "success", "message": "Produce confirmed as received."}), 200

@buyer_bp.route('/orders/<int:order_id>/rate', methods=['POST'])
@roles_required(allowed_roles=['consumer'])
def rate_farmer(user, order_id):
    user_id = user['id']
    data = request.get_json(silent=True) or {}
    rating = int(data.get('rating', 5))
    review = str(data.get('review', '')).strip()

    order = query_db("SELECT * FROM orders WHERE id = ? AND buyer_id = ?", (order_id, user_id), one=True)
    if not order:
        return jsonify({"status": "error", "message": "Order not found."}), 404

    execute_db("""
        INSERT INTO ratings (order_id, buyer_id, farmer_id, rating, review)
        VALUES (?, ?, ?, ?, ?)
    """, (order_id, user_id, order['farmer_id'], rating, review))

    # Recalculate farmer avg rating
    avg_stat = query_db("SELECT AVG(rating) as avg_r, COUNT(*) as cnt FROM ratings WHERE farmer_id = ?", (order['farmer_id'],), one=True)
    if avg_stat:
        execute_db("UPDATE farmer_profiles SET rating_avg = ?, rating_count = ? WHERE user_id = ?", (round(avg_stat['avg_r'], 1), avg_stat['cnt'], order['farmer_id']))

    return jsonify({"status": "success", "message": "Rating submitted. Thank you for your feedback!"}), 200

@buyer_bp.route('/orders/<int:order_id>/report-issue', methods=['POST'])
@roles_required(allowed_roles=['consumer'])
def report_order_issue(user, order_id):
    user_id = user['id']
    data = request.get_json(silent=True) or {}
    issue_type = data.get('issue_type', 'poor_quality')  # wrong_quantity, poor_quality, other
    reason = str(data.get('reason', '')).strip()
    photo_url = data.get('photo_url', '')

    if not reason:
        return jsonify({"status": "error", "message": "Reason description is required."}), 400

    order = query_db("SELECT * FROM orders WHERE id = ? AND buyer_id = ?", (order_id, user_id), one=True)
    if not order:
        return jsonify({"status": "error", "message": "Order not found."}), 404

    issue_id, _ = execute_db("""
        INSERT INTO issues (order_id, reporter_user_id, reporter_role, issue_type, reason, photo_url, status)
        VALUES (?, ?, 'consumer', ?, ?, ?, 'open')
    """, (order_id, user_id, issue_type, reason, photo_url))

    return jsonify({"status": "success", "message": "Issue recorded. Our moderation team will investigate.", "issue_id": issue_id}), 201

@buyer_bp.route('/orders/<int:order_id>/repeat', methods=['POST'])
@roles_required(allowed_roles=['consumer'])
def repeat_order(user, order_id):
    user_id = user['id']
    old_order = query_db("SELECT * FROM orders WHERE id = ? AND buyer_id = ?", (order_id, user_id), one=True)
    if not old_order:
        return jsonify({"status": "error", "message": "Original order not found."}), 404

    listing = query_db("SELECT * FROM listings WHERE id = ? AND status = 'active'", (old_order['listing_id'],), one=True)
    if not listing or float(listing['quantity_left']) < float(old_order['quantity']):
        return jsonify({"status": "error", "message": "Cannot repeat order: Produce is currently out of stock."}), 400

    # Place re-order
    delivery_code = str(random.randint(100000, 999999))
    pickup_code = str(random.randint(100000, 999999))

    new_order_id, _ = execute_db("""
        INSERT INTO orders (
            listing_id, farmer_id, buyer_id, quantity, unit, unit_price,
            crop_total_price, transport_fee, platform_fee, total_amount,
            payment_method, payment_status, status, buyer_address, buyer_phone,
            delivery_date, pickup_code, delivery_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unpaid', 'new', ?, ?, ?, ?, ?)
    """, (
        listing['id'], listing['farmer_id'], user_id, old_order['quantity'],
        old_order['unit'], float(listing['asking_price_per_kg']),
        old_order['crop_total_price'], old_order['transport_fee'],
        old_order['platform_fee'], old_order['total_amount'],
        old_order['payment_method'], old_order['buyer_address'],
        old_order['buyer_phone'], str(date.today() + timedelta(days=2)),
        pickup_code, delivery_code
    ))

    return jsonify({"status": "success", "message": "Repeat order placed!", "order_id": new_order_id}), 201

# ----------------- Bulk Buyer RFQ -----------------

@buyer_bp.route('/rfqs', methods=['GET', 'POST'])
@roles_required(allowed_roles=['consumer'])
def handle_rfqs(user):
    user_id = user['id']
    if request.method == 'POST':
        if user['subtype'] != 'bulk_buyer':
            return jsonify({"status": "error", "message": "Bulk RFQs are reserved for verified bulk buyers."}), 403

        data = request.get_json(silent=True) or {}
        crop_name = str(data.get('crop_name', '')).strip()
        variety = str(data.get('variety', '')).strip()
        min_order_qty = float(data.get('min_order_qty', 0) or 0)
        unit = str(data.get('unit', 'kg')).strip()
        quality_grade = str(data.get('quality_grade', 'A')).strip()
        needed_by_date = data.get('needed_by_date') or str(date.today() + timedelta(days=5))
        target_price = float(data.get('target_price', 0) or 0)
        delivery_location = str(data.get('delivery_location', '')).strip()

        if not crop_name or min_order_qty <= 0 or not delivery_location:
            return jsonify({"status": "error", "message": "Crop name, minimum quantity and delivery location are required."}), 400

        rfq_id, _ = execute_db("""
            INSERT INTO rfqs (
                buyer_id, crop_name, variety, min_order_qty, unit,
                quality_grade, needed_by_date, target_price, delivery_location, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open')
        """, (
            user_id, crop_name, variety, min_order_qty, unit,
            quality_grade, needed_by_date, target_price, delivery_location
        ))

        return jsonify({"status": "success", "message": "Bulk RFQ requirement posted successfully.", "rfq_id": rfq_id}), 201

    # GET buyer's RFQs with quotes
    rfqs = query_db("SELECT * FROM rfqs WHERE buyer_id = ? ORDER BY created_at DESC", (user_id,))
    for r in rfqs:
        quotes = query_db("""
            SELECT q.*, fp.full_name as farmer_name, fp.village, fp.rating_avg as farmer_rating
            FROM rfq_quotes q
            JOIN users u ON q.farmer_id = u.id
            LEFT JOIN farmer_profiles fp ON u.id = fp.user_id
            WHERE q.rfq_id = ?
            ORDER BY q.price_per_kg ASC
        """, (r['id'],))
        r['quotes'] = quotes

    return jsonify({"status": "success", "data": rfqs}), 200

@buyer_bp.route('/rfqs/<int:rfq_id>/accept-quote/<int:quote_id>', methods=['POST'])
@roles_required(allowed_roles=['consumer'], allowed_subtypes=['bulk_buyer'])
def accept_rfq_quote(user, rfq_id, quote_id):
    user_id = user['id']
    quote = query_db("SELECT * FROM rfq_quotes WHERE id = ? AND rfq_id = ?", (quote_id, rfq_id), one=True)
    if not quote:
        return jsonify({"status": "error", "message": "Quote not found."}), 404

    rfq = query_db("SELECT * FROM rfqs WHERE id = ? AND buyer_id = ?", (rfq_id, user_id), one=True)
    if not rfq:
        return jsonify({"status": "error", "message": "RFQ not found or access denied."}), 404

    # Convert quote into an order
    qty = float(quote['quantity_offered'])
    unit_price = float(quote['price_per_kg'])
    crop_total = round(qty * unit_price, 2)
    transport_fee = round(200.0 + (qty * 1.0), 2)
    platform_fee = round(crop_total * 0.02, 2)
    total_amount = round(crop_total + transport_fee + platform_fee, 2)

    delivery_code = str(random.randint(100000, 999999))
    pickup_code = str(random.randint(100000, 999999))

    # Create dummy listing link or placeholder listing if needed
    listing_id, _ = execute_db("""
        INSERT INTO listings (
            farmer_id, crop_name, variety, category, quantity, quantity_left,
            unit, quality_grade, asking_price_per_kg, pickup_location, status
        ) VALUES (?, ?, ?, 'vegetables', ?, 0, ?, ?, ?, ?, 'sold_out')
    """, (quote['farmer_id'], rfq['crop_name'], rfq['variety'], qty, rfq['unit'], rfq['quality_grade'], unit_price, "Farmer Site"))

    order_id, _ = execute_db("""
        INSERT INTO orders (
            listing_id, farmer_id, buyer_id, quantity, unit, unit_price,
            crop_total_price, transport_fee, platform_fee, total_amount,
            payment_method, payment_status, status, buyer_address, buyer_phone,
            delivery_date, pickup_code, delivery_code
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'COD', 'unpaid', 'accepted', ?, ?, ?, ?, ?)
    """, (
        listing_id, quote['farmer_id'], user_id, qty, rfq['unit'], unit_price,
        crop_total, transport_fee, platform_fee, total_amount,
        rfq['delivery_location'], user['phone'], rfq['needed_by_date'],
        pickup_code, delivery_code
    ))

    # Mark quote accepted, others rejected
    execute_db("UPDATE rfq_quotes SET status = 'accepted' WHERE id = ?", (quote_id,))
    execute_db("UPDATE rfq_quotes SET status = 'rejected' WHERE rfq_id = ? AND id != ?", (rfq_id, quote_id))
    execute_db("UPDATE rfqs SET status = 'fulfilled' WHERE id = ?", (rfq_id,))

    # Notify farmer
    execute_db("""
        INSERT INTO notifications (user_id, title, message, type)
        VALUES (?, 'RFQ Quote Accepted!', ?, 'order')
    """, (quote['farmer_id'], f"Your quote on RFQ #{rfq_id} was accepted! Order #{order_id} is generated."))

    return jsonify({
        "status": "success",
        "message": "Quote accepted! Order generated automatically.",
        "order_id": order_id
    }), 200

# ----------------- Buyer Saved Addresses -----------------

@buyer_bp.route('/addresses', methods=['GET', 'POST'])
@roles_required(allowed_roles=['consumer'])
def manage_addresses(user):
    user_id = user['id']
    if request.method == 'POST':
        data = request.get_json(silent=True) or {}
        label = data.get('label', 'Home')
        address_line = str(data.get('address_line', '')).strip()
        landmark = data.get('landmark', '')
        city = str(data.get('city', '')).strip()
        district = data.get('district', city)
        pincode = str(data.get('pincode', '')).strip()
        is_default = 1 if data.get('is_default') else 0

        if not address_line or not city or not pincode:
            return jsonify({"status": "error", "message": "Address line, city and pincode are required."}), 400

        if is_default:
            execute_db("UPDATE buyer_addresses SET is_default = 0 WHERE user_id = ?", (user_id,))

        addr_id, _ = execute_db("""
            INSERT INTO buyer_addresses (user_id, label, address_line, landmark, city, district, pincode, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (user_id, label, address_line, landmark, city, district, pincode, is_default))

        return jsonify({"status": "success", "message": "Address saved.", "address_id": addr_id}), 201

    addresses = query_db("SELECT * FROM buyer_addresses WHERE user_id = ? ORDER BY is_default DESC, id DESC", (user_id,))
    return jsonify({"status": "success", "data": addresses}), 200
