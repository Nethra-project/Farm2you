import re
from datetime import datetime, timedelta
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from database import query_db, execute_db
from auth_helper import generate_token, login_required

auth_bp = Blueprint('auth_bp', __name__, url_prefix='/auth')

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json(silent=True) or {}
    phone = str(data.get('phone', '')).strip()

    # Clean phone digits
    phone_digits = re.sub(r'\D', '', phone)
    if len(phone_digits) < 10:
        return jsonify({"status": "error", "message": "Please enter a valid 10-digit mobile number."}), 400

    phone = phone_digits[-10:]
    otp_code = "123456"  # Standard development & test OTP
    expires_at = datetime.now() + timedelta(minutes=15)

    execute_db(
        "INSERT INTO otp_codes (phone, otp_code, expires_at) VALUES (?, ?, ?)",
        (phone, otp_code, expires_at)
    )

    return jsonify({
        "status": "success",
        "message": f"Verification code sent to +91 {phone}.",
        "otp_code": otp_code
    }), 200

@auth_bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json(silent=True) or {}
    phone = str(data.get('phone', '')).strip()
    otp_code = str(data.get('otp_code', '')).strip()

    phone_digits = re.sub(r'\D', '', phone)[-10:]
    if not phone_digits or not otp_code:
        return jsonify({"status": "error", "message": "Phone number and OTP code are required."}), 400

    record = query_db(
        "SELECT * FROM otp_codes WHERE phone = ? AND otp_code = ? AND is_verified = 0 ORDER BY id DESC LIMIT 1",
        (phone_digits, otp_code),
        one=True
    )

    if not record:
        return jsonify({"status": "error", "message": "Invalid or expired OTP code."}), 400

    execute_db("UPDATE otp_codes SET is_verified = 1 WHERE id = ?", (record['id'],))

    return jsonify({
        "status": "success",
        "message": "Mobile number successfully verified."
    }), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json(silent=True) or {}
    role = data.get('role')  # producer, consumer, driver
    subtype = data.get('subtype')  # farmer, fpo, retail_buyer, bulk_buyer, driver
    phone = str(data.get('phone', '')).strip()
    phone_digits = re.sub(r'\D', '', phone)[-10:]
    password = str(data.get('password', '')).strip()
    preferred_lang = data.get('preferred_language', 'en')

    if not phone_digits or len(phone_digits) != 10:
        return jsonify({"status": "error", "message": "Valid 10-digit mobile number required."}), 400
    if not password or len(password) < 6:
        return jsonify({"status": "error", "message": "Password must be at least 6 characters long."}), 400
    if not role or not subtype:
        return jsonify({"status": "error", "message": "User role and subtype must be selected."}), 400

    # Ensure phone was verified via OTP
    otp_check = query_db(
        "SELECT id FROM otp_codes WHERE phone = ? AND is_verified = 1 ORDER BY id DESC LIMIT 1",
        (phone_digits,),
        one=True
    )
    if not otp_check:
        return jsonify({"status": "error", "message": "Please verify your mobile number with OTP first."}), 403

    # Check if user already exists
    existing = query_db("SELECT id FROM users WHERE phone = ?", (phone_digits,), one=True)
    if existing:
        return jsonify({"status": "error", "message": "This mobile number is already registered. Please log in."}), 409

    # Determine approval status based on exact document specifications:
    # Consumer (retail buyer) gets instant access ('verified')
    # Farmer, FPO, Bulk Buyer, Driver start as 'pending' for admin review
    if subtype == 'retail_buyer':
        approval_status = 'verified'
    else:
        approval_status = 'pending'

    password_hash = generate_password_hash(password)
    email = data.get('email')

    try:
        user_id, _ = execute_db("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (phone_digits, email, password_hash, role, subtype, approval_status, preferred_lang))

        # Populate profile table based on subtype
        if subtype == 'farmer':
            execute_db("""
                INSERT INTO farmer_profiles (
                    user_id, full_name, village, district, state, pincode,
                    crops_grown, upi_id, bank_account_no, ifsc_code, fpo_name, profile_photo_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get('full_name', ''),
                data.get('village', ''),
                data.get('district', ''),
                data.get('state', ''),
                data.get('pincode', ''),
                data.get('crops_grown', ''),
                data.get('upi_id', ''),
                data.get('bank_account_no', ''),
                data.get('ifsc_code', ''),
                data.get('fpo_name', ''),
                data.get('profile_photo_url', '')
            ))
        elif subtype == 'fpo':
            execute_db("""
                INSERT INTO fpo_profiles (
                    user_id, fpo_name, registration_type, registration_number, registration_year,
                    contact_person_name, designation, email, office_address, district, state, pincode,
                    member_count, crops_handled, storage_available, storage_capacity_kg, gstin,
                    bank_account_no, ifsc_code, cert_file_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get('fpo_name', ''),
                data.get('registration_type', 'company'),
                data.get('registration_number', ''),
                int(data.get('registration_year', 2022) or 2022),
                data.get('contact_person_name', ''),
                data.get('designation', ''),
                email,
                data.get('office_address', ''),
                data.get('district', ''),
                data.get('state', ''),
                data.get('pincode', ''),
                int(data.get('member_count', 0) or 0),
                data.get('crops_handled', ''),
                1 if data.get('storage_available') in [True, 1, '1', 'yes'] else 0,
                float(data.get('storage_capacity_kg', 0) or 0),
                data.get('gstin', ''),
                data.get('bank_account_no', ''),
                data.get('ifsc_code', ''),
                data.get('cert_file_url', '')
            ))
        elif subtype in ['retail_buyer', 'bulk_buyer']:
            execute_db("""
                INSERT INTO buyer_profiles (
                    user_id, buyer_type, full_name, business_name, business_type,
                    contact_person_name, email, gstin, delivery_address, landmark,
                    city, district, pincode, crops_needed, approx_monthly_qty, business_proof_url
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                subtype,
                data.get('full_name', data.get('business_name', 'Buyer')),
                data.get('business_name', ''),
                data.get('business_type', ''),
                data.get('contact_person_name', ''),
                email,
                data.get('gstin', ''),
                data.get('delivery_address', ''),
                data.get('landmark', ''),
                data.get('city', ''),
                data.get('district', data.get('city', '')),
                data.get('pincode', ''),
                data.get('crops_needed', ''),
                data.get('approx_monthly_qty', ''),
                data.get('business_proof_url', '')
            ))
            # Also save default delivery address
            if data.get('delivery_address'):
                execute_db("""
                    INSERT INTO buyer_addresses (user_id, label, address_line, landmark, city, district, pincode, is_default)
                    VALUES (?, 'Primary Delivery', ?, ?, ?, ?, ?, 1)
                """, (
                    user_id,
                    data.get('delivery_address'),
                    data.get('landmark', ''),
                    data.get('city', ''),
                    data.get('district', data.get('city', '')),
                    data.get('pincode', '')
                ))
        elif subtype == 'driver':
            execute_db("""
                INSERT INTO driver_profiles (
                    user_id, full_name, city, district, pincodes_served,
                    vehicle_type, vehicle_number, load_capacity_kg, licence_photo_url,
                    upi_id, bank_account_no, ifsc_code
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                data.get('full_name', 'Driver'),
                data.get('city', ''),
                data.get('district', data.get('city', '')),
                data.get('pincodes_served', ''),
                data.get('vehicle_type', 'tempo'),
                str(data.get('vehicle_number', '')).upper(),
                float(data.get('load_capacity_kg', 500) or 500),
                data.get('licence_photo_url', ''),
                data.get('upi_id', ''),
                data.get('bank_account_no', ''),
                data.get('ifsc_code', '')
            ))

        # Add initial welcome notification
        execute_db("""
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, ?, ?, 'system')
        """, (
            user_id,
            "Welcome to Farm2you!",
            f"Your account as {subtype.replace('_', ' ').title()} was created. Status: {approval_status}."
        ))

        user = query_db("SELECT * FROM users WHERE id = ?", (user_id,), one=True)
        token = generate_token(user)

        return jsonify({
            "status": "success",
            "message": "Account registered successfully.",
            "token": token,
            "user": {
                "id": user['id'],
                "phone": user['phone'],
                "role": user['role'],
                "subtype": user['subtype'],
                "approval_status": user['approval_status'],
                "preferred_language": user['preferred_language']
            }
        }), 201

    except Exception as e:
        return jsonify({"status": "error", "message": f"Registration failed: {str(e)}"}), 500

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json(silent=True) or {}
    identifier = str(data.get('identifier', data.get('phone', data.get('mobile', data.get('email', ''))))).strip()
    password = str(data.get('password', '')).strip()
    login_with_otp = data.get('login_with_otp', False)
    otp_code = str(data.get('otp_code', '')).strip()

    if not identifier:
        return jsonify({"status": "error", "message": "Mobile number or Email is required."}), 400

    phone_digits = re.sub(r'\D', '', identifier)[-10:]

    user = None
    if len(phone_digits) == 10:
        user = query_db("SELECT * FROM users WHERE phone = ?", (phone_digits,), one=True)
    if not user:
        user = query_db("SELECT * FROM users WHERE email = ?", (identifier,), one=True)

    if not user:
        return jsonify({"status": "error", "message": "No account found with these credentials."}), 404

    # Check blocked status
    if user['approval_status'] == 'blocked' or user['is_blocked']:
        return jsonify({
            "status": "error",
            "approval_status": "blocked",
            "message": "Your account has been blocked by administrators. Please contact support."
        }), 403

    # Authenticate via password or OTP
    if login_with_otp:
        if not otp_code:
            return jsonify({"status": "error", "message": "OTP code is required."}), 400
        otp_rec = query_db(
            "SELECT id FROM otp_codes WHERE phone = ? AND otp_code = ? ORDER BY id DESC LIMIT 1",
            (user['phone'], otp_code),
            one=True
        )
        if not otp_rec:
            return jsonify({"status": "error", "message": "Invalid OTP code."}), 401
    else:
        if not password or not check_password_hash(user['password_hash'], password):
            return jsonify({"status": "error", "message": "Incorrect password."}), 401

    token = generate_token(user)

    # Fetch display name from profile
    name = user['phone']
    if user['subtype'] == 'farmer':
        p = query_db("SELECT full_name FROM farmer_profiles WHERE user_id = ?", (user['id'],), one=True)
        if p and p['full_name']: name = p['full_name']
    elif user['subtype'] == 'fpo':
        p = query_db("SELECT fpo_name FROM fpo_profiles WHERE user_id = ?", (user['id'],), one=True)
        if p and p['fpo_name']: name = p['fpo_name']
    elif user['role'] == 'consumer':
        p = query_db("SELECT full_name, business_name FROM buyer_profiles WHERE user_id = ?", (user['id'],), one=True)
        if p: name = p['business_name'] or p['full_name']
    elif user['subtype'] == 'driver':
        p = query_db("SELECT full_name FROM driver_profiles WHERE user_id = ?", (user['id'],), one=True)
        if p and p['full_name']: name = p['full_name']

    return jsonify({
        "status": "success",
        "message": "Login successful.",
        "token": token,
        "user": {
            "id": user['id'],
            "name": name,
            "phone": user['phone'],
            "email": user['email'],
            "role": user['role'],
            "subtype": user['subtype'],
            "approval_status": user['approval_status'],
            "preferred_language": user['preferred_language']
        }
    }), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json(silent=True) or {}
    phone = str(data.get('phone', '')).strip()
    phone_digits = re.sub(r'\D', '', phone)[-10:]
    otp_code = str(data.get('otp_code', '')).strip()
    new_password = str(data.get('new_password', '')).strip()

    if not phone_digits or not otp_code or not new_password:
        return jsonify({"status": "error", "message": "Phone number, OTP code, and new password are required."}), 400

    otp_rec = query_db(
        "SELECT id FROM otp_codes WHERE phone = ? AND otp_code = ? AND is_verified = 1 ORDER BY id DESC LIMIT 1",
        (phone_digits, otp_code),
        one=True
    )
    if not otp_rec:
        return jsonify({"status": "error", "message": "Invalid or unverified OTP."}), 400

    user = query_db("SELECT id FROM users WHERE phone = ?", (phone_digits,), one=True)
    if not user:
        return jsonify({"status": "error", "message": "User not found."}), 404

    pwd_hash = generate_password_hash(new_password)
    execute_db("UPDATE users SET password_hash = ? WHERE id = ?", (pwd_hash, user['id']))

    return jsonify({"status": "success", "message": "Password updated successfully. Please log in with your new password."}), 200

@auth_bp.route('/me', methods=['GET'])
@login_required
def get_current_user_profile(user):
    profile_data = {}
    if user['subtype'] == 'farmer':
        profile_data = query_db("SELECT * FROM farmer_profiles WHERE user_id = ?", (user['id'],), one=True) or {}
    elif user['subtype'] == 'fpo':
        profile_data = query_db("SELECT * FROM fpo_profiles WHERE user_id = ?", (user['id'],), one=True) or {}
    elif user['role'] == 'consumer':
        profile_data = query_db("SELECT * FROM buyer_profiles WHERE user_id = ?", (user['id'],), one=True) or {}
    elif user['subtype'] == 'driver':
        profile_data = query_db("SELECT * FROM driver_profiles WHERE user_id = ?", (user['id'],), one=True) or {}

    return jsonify({
        "status": "success",
        "user": {
            "id": user['id'],
            "phone": user['phone'],
            "email": user['email'],
            "role": user['role'],
            "subtype": user['subtype'],
            "approval_status": user['approval_status'],
            "preferred_language": user['preferred_language']
        },
        "profile": profile_data
    }), 200

@auth_bp.route('/change-language', methods=['POST'])
@login_required
def change_language(user):
    data = request.get_json(silent=True) or {}
    lang = data.get('language', 'en')
    if lang not in ['en', 'hi', 'ta', 'te']:
        return jsonify({"status": "error", "message": "Supported languages: en, hi, ta, te"}), 400

    execute_db("UPDATE users SET preferred_language = ? WHERE id = ?", (lang, user['id']))
    return jsonify({"status": "success", "message": f"Language updated to {lang}."}), 200
