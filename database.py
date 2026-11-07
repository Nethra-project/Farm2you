import sqlite3
import os
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

DB_NAME = 'farm_db.sqlite'
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), DB_NAME)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def query_db(query, args=(), one=False):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    r = cur.fetchall()
    cur.close()
    conn.close()
    return (dict(r[0]) if r else None) if one else [dict(row) for row in r]

def execute_db(query, args=(), commit=True):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    if commit:
        conn.commit()
    last_id = cur.lastrowid
    row_count = cur.rowcount
    cur.close()
    conn.close()
    return last_id, row_count

def init_db():
    conn = get_db_connection()
    cur = conn.cursor()

    # 1. Users Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT UNIQUE,
        email TEXT UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL,
        subtype TEXT NOT NULL,
        approval_status TEXT NOT NULL DEFAULT 'pending',
        rejection_reason TEXT,
        preferred_language TEXT DEFAULT 'en',
        is_blocked INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 2. OTP Codes Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS otp_codes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        phone TEXT NOT NULL,
        otp_code TEXT NOT NULL,
        expires_at DATETIME NOT NULL,
        is_verified INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    # 3. Farmer Profiles Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS farmer_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        village TEXT NOT NULL,
        district TEXT NOT NULL,
        state TEXT NOT NULL,
        pincode TEXT NOT NULL,
        crops_grown TEXT,
        upi_id TEXT,
        bank_account_no TEXT,
        ifsc_code TEXT,
        fpo_name TEXT,
        profile_photo_url TEXT,
        rating_avg REAL DEFAULT 5.0,
        rating_count INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 4. FPO Profiles Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS fpo_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        fpo_name TEXT NOT NULL,
        registration_type TEXT NOT NULL,
        registration_number TEXT UNIQUE NOT NULL,
        registration_year INTEGER NOT NULL,
        contact_person_name TEXT NOT NULL,
        designation TEXT NOT NULL,
        email TEXT,
        office_address TEXT NOT NULL,
        district TEXT NOT NULL,
        state TEXT NOT NULL,
        pincode TEXT NOT NULL,
        member_count INTEGER DEFAULT 0,
        crops_handled TEXT,
        storage_available INTEGER DEFAULT 0,
        storage_capacity_kg REAL DEFAULT 0,
        gstin TEXT,
        bank_account_no TEXT,
        ifsc_code TEXT,
        cert_file_url TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 5. FPO Member Farmers Table (FPO extras)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS fpo_members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fpo_user_id INTEGER NOT NULL,
        member_name TEXT NOT NULL,
        phone TEXT,
        village TEXT,
        crops_grown TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (fpo_user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 6. Buyer Profiles Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS buyer_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        buyer_type TEXT NOT NULL,
        full_name TEXT NOT NULL,
        business_name TEXT,
        business_type TEXT,
        contact_person_name TEXT,
        email TEXT,
        gstin TEXT,
        delivery_address TEXT NOT NULL,
        landmark TEXT,
        city TEXT NOT NULL,
        district TEXT,
        pincode TEXT NOT NULL,
        crops_needed TEXT,
        approx_monthly_qty TEXT,
        business_proof_url TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 7. Buyer Saved Addresses Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS buyer_addresses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        label TEXT DEFAULT 'Home',
        address_line TEXT NOT NULL,
        landmark TEXT,
        city TEXT NOT NULL,
        district TEXT,
        pincode TEXT NOT NULL,
        is_default INTEGER DEFAULT 0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 8. Driver Profiles Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS driver_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE NOT NULL,
        full_name TEXT NOT NULL,
        city TEXT NOT NULL,
        district TEXT NOT NULL,
        pincodes_served TEXT NOT NULL,
        vehicle_type TEXT NOT NULL,
        vehicle_number TEXT UNIQUE NOT NULL,
        load_capacity_kg REAL NOT NULL,
        licence_photo_url TEXT,
        upi_id TEXT,
        bank_account_no TEXT,
        ifsc_code TEXT,
        is_online INTEGER DEFAULT 0,
        total_deliveries INTEGER DEFAULT 0,
        rating_avg REAL DEFAULT 5.0,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 9. Listings Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS listings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_id INTEGER NOT NULL,
        fpo_member_id INTEGER,
        is_pooled INTEGER DEFAULT 0,
        crop_name TEXT NOT NULL,
        variety TEXT,
        category TEXT DEFAULT 'vegetables',
        quantity REAL NOT NULL,
        quantity_left REAL NOT NULL,
        unit TEXT DEFAULT 'kg',
        quality_grade TEXT DEFAULT 'A',
        harvest_date DATE,
        available_from DATE,
        available_until DATE,
        asking_price_per_kg REAL NOT NULL,
        mandi_price_hint REAL,
        min_order_qty REAL DEFAULT 1,
        max_order_qty REAL,
        pickup_location TEXT NOT NULL,
        photo_urls TEXT,
        description TEXT,
        status TEXT DEFAULT 'active',
        flagged_reason TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (fpo_member_id) REFERENCES fpo_members(id) ON DELETE SET NULL
    )
    ''')

    # 10. Orders Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        listing_id INTEGER NOT NULL,
        farmer_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL,
        quantity REAL NOT NULL,
        unit TEXT DEFAULT 'kg',
        unit_price REAL NOT NULL,
        crop_total_price REAL NOT NULL,
        transport_fee REAL DEFAULT 0.0,
        platform_fee REAL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        payment_method TEXT DEFAULT 'COD',
        payment_status TEXT DEFAULT 'unpaid',
        status TEXT DEFAULT 'new',
        rejection_reason TEXT,
        buyer_address TEXT,
        buyer_phone TEXT,
        delivery_date DATE,
        pickup_code TEXT,
        delivery_code TEXT,
        driver_id INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        delivered_at DATETIME,
        FOREIGN KEY (listing_id) REFERENCES listings(id) ON DELETE CASCADE,
        FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # 11. Delivery Jobs Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS delivery_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER UNIQUE NOT NULL,
        driver_id INTEGER,
        pickup_village TEXT NOT NULL,
        pickup_address TEXT NOT NULL,
        drop_city TEXT NOT NULL,
        drop_address TEXT NOT NULL,
        total_weight_kg REAL NOT NULL,
        distance_km REAL DEFAULT 15.0,
        driver_pay REAL NOT NULL,
        farmer_pickup_code TEXT NOT NULL,
        buyer_delivery_code TEXT NOT NULL,
        pickup_photo_url TEXT,
        cash_collected REAL DEFAULT 0.0,
        status TEXT DEFAULT 'open',
        failure_reason TEXT,
        failure_photo_url TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        picked_up_at DATETIME,
        delivered_at DATETIME,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # 12. Driver Earnings Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS driver_earnings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        driver_id INTEGER NOT NULL,
        job_id INTEGER UNIQUE NOT NULL,
        amount REAL NOT NULL,
        payment_status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (job_id) REFERENCES delivery_jobs(id) ON DELETE CASCADE
    )
    ''')

    # 13. RFQs Table (Bulk buyer)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS rfqs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        buyer_id INTEGER NOT NULL,
        crop_name TEXT NOT NULL,
        variety TEXT,
        min_order_qty REAL NOT NULL,
        unit TEXT DEFAULT 'kg',
        quality_grade TEXT,
        needed_by_date DATE NOT NULL,
        target_price REAL,
        delivery_location TEXT NOT NULL,
        status TEXT DEFAULT 'open',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 14. RFQ Quotes Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS rfq_quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rfq_id INTEGER NOT NULL,
        farmer_id INTEGER NOT NULL,
        price_per_kg REAL NOT NULL,
        quantity_offered REAL NOT NULL,
        note TEXT,
        status TEXT DEFAULT 'pending',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (rfq_id) REFERENCES rfqs(id) ON DELETE CASCADE,
        FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 15. Mandi Prices Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS mandi_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crop_name TEXT NOT NULL,
        variety TEXT,
        district TEXT NOT NULL,
        price_per_kg REAL NOT NULL,
        date DATE NOT NULL
    )
    ''')

    # 16. Notifications Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        type TEXT DEFAULT 'general',
        is_read INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 17. Feedback Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        subject TEXT,
        category TEXT DEFAULT 'general',
        message TEXT NOT NULL,
        rating INTEGER,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 18. Ratings Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS ratings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL,
        farmer_id INTEGER NOT NULL,
        rating INTEGER NOT NULL,
        review TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 19. Issues Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS issues (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        reporter_user_id INTEGER NOT NULL,
        reporter_role TEXT NOT NULL,
        issue_type TEXT NOT NULL,
        reason TEXT NOT NULL,
        photo_url TEXT,
        status TEXT DEFAULT 'open',
        admin_notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (reporter_user_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 20. Admin Invites Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS admin_invites (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        inviter_admin_id INTEGER,
        invite_code TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        admin_level TEXT DEFAULT 'moderator',
        is_used INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (inviter_admin_id) REFERENCES users(id) ON DELETE SET NULL
    )
    ''')

    # 21. Admin Audit Logs Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS admin_audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER NOT NULL,
        action TEXT NOT NULL,
        target_entity TEXT NOT NULL,
        target_id INTEGER,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
    )
    ''')

    # 22. System Settings Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS system_settings (
        setting_key TEXT PRIMARY KEY,
        setting_value TEXT NOT NULL
    )
    ''')

    # 23. FPO Payment Splits Table
    cur.execute('''
    CREATE TABLE IF NOT EXISTS fpo_payment_splits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        fpo_user_id INTEGER NOT NULL,
        member_id INTEGER NOT NULL,
        share_amount REAL NOT NULL,
        notes TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
        FOREIGN KEY (fpo_user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (member_id) REFERENCES fpo_members(id) ON DELETE CASCADE
    )
    ''')

    # Seed System Settings
    settings = [
        ('platform_fee_percent', '2.0'),
        ('transport_rate_per_km', '8.0'),
        ('transport_base_km', '15.0'),
        ('crop_categories', '["vegetables", "fruits", "grains"]'),
        ('languages', '["English", "Hindi", "Tamil", "Telugu"]')
    ]
    for k, v in settings:
        cur.execute("INSERT OR IGNORE INTO system_settings (setting_key, setting_value) VALUES (?, ?)", (k, v))

    # Seed Admin Users (Step 1 Admin requirement)
    cur.execute("SELECT id FROM users WHERE role = 'admin' AND subtype = 'super_admin'")
    if not cur.fetchone():
        super_admin_pass = generate_password_hash("SuperAdminPass123!")
        cur.execute("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES (?, ?, ?, 'admin', 'super_admin', 'verified', 'en')
        """, ('9999900001', 'admin@platform.com', super_admin_pass))

        moderator_pass = generate_password_hash("ModPass123!")
        cur.execute("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES (?, ?, ?, 'admin', 'moderator', 'verified', 'en')
        """, ('9999900002', 'moderator@platform.com', moderator_pass))

    # Seed Mandi Prices (for farmer comparison and buyer hints)
    today_str = datetime.now().strftime('%Y-%m-%d')
    sample_mandi = [
        ('Tomato', 'Hybrid', 'Nashik', 24.50, today_str),
        ('Tomato', 'Desi', 'Nashik', 21.00, today_str),
        ('Potato', 'Jyoti', 'Agra', 18.00, today_str),
        ('Onion', 'Red', 'Pune', 28.50, today_str),
        ('Wheat', 'Sharbati', 'Indore', 32.00, today_str),
        ('Rice', 'Basmati 1121', 'Karnal', 65.00, today_str),
        ('Rice', 'Sona Masoori', 'Guntur', 42.00, today_str),
        ('Banana', 'Robusta', 'Theni', 22.00, today_str),
        ('Green Chilli', 'G4', 'Kolhapur', 45.00, today_str),
        ('Cotton', 'Medium Staple', 'Rajkot', 72.00, today_str)
    ]
    cur.execute("SELECT COUNT(*) as cnt FROM mandi_prices")
    if cur.fetchone()[0] == 0:
        for crop, variety, district, price, dt in sample_mandi:
            cur.execute("""
                INSERT INTO mandi_prices (crop_name, variety, district, price_per_kg, date)
                VALUES (?, ?, ?, ?, ?)
            """, (crop, variety, district, price, dt))

    # Seed Demo Accounts for testing if none exist
    cur.execute("SELECT COUNT(*) FROM users WHERE role != 'admin'")
    if cur.fetchone()[0] == 0:
        pwd = generate_password_hash("Pass1234!")

        # 1. Verified Farmer
        cur.execute("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES ('9876543210', 'ramesh.farmer@example.com', ?, 'producer', 'farmer', 'verified', 'en')
        """, (pwd,))
        farmer_uid = cur.lastrowid
        cur.execute("""
            INSERT INTO farmer_profiles (user_id, full_name, village, district, state, pincode, crops_grown, upi_id, bank_account_no, ifsc_code)
            VALUES (?, 'Ramesh Kumar', 'Khed Shivapur', 'Pune', 'Maharashtra', '412205', 'Tomato, Onion, Potato', 'ramesh@upi', '123456789012', 'SBIN0001234')
        """, (farmer_uid,))

        # 2. Pending Farmer (to test approval queue)
        cur.execute("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES ('9876543211', 'suresh.farmer@example.com', ?, 'producer', 'farmer', 'pending', 'hi')
        """, (pwd,))
        p_farmer_uid = cur.lastrowid
        cur.execute("""
            INSERT INTO farmer_profiles (user_id, full_name, village, district, state, pincode, crops_grown, upi_id)
            VALUES (?, 'Suresh Patel', 'Baramati', 'Pune', 'Maharashtra', '413102', 'Wheat, Gram', 'suresh@upi')
        """, (p_farmer_uid,))

        # 3. FPO Producer
        cur.execute("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES ('9876543220', 'contact@sahayadri-fpo.org', ?, 'producer', 'fpo', 'verified', 'en')
        """, (pwd,))
        fpo_uid = cur.lastrowid
        cur.execute("""
            INSERT INTO fpo_profiles (user_id, fpo_name, registration_type, registration_number, registration_year, contact_person_name, designation, email, office_address, district, state, pincode, member_count, crops_handled, storage_available, storage_capacity_kg, bank_account_no, ifsc_code)
            VALUES (?, 'Sahyadri Agro FPO', 'cooperative', 'FPO-MH-2021-9988', 2021, 'Anand Deshmukh', 'Managing Director', 'contact@sahayadri-fpo.org', 'Agro Complex, Nashik Road', 'Nashik', 'Maharashtra', '422001', 120, 'Tomato, Grapes, Pomegranate', 1, 50000, '987654321099', 'HDFC0001234')
        """, (fpo_uid,))
        # FPO members
        cur.execute("INSERT INTO fpo_members (fpo_user_id, member_name, phone, village, crops_grown) VALUES (?, 'Govind Shinde', '9876500001', 'Ozar', 'Tomato')", (fpo_uid,))
        cur.execute("INSERT INTO fpo_members (fpo_user_id, member_name, phone, village, crops_grown) VALUES (?, 'Baban Patil', '9876500002', 'Dindori', 'Pomegranate')", (fpo_uid,))

        # 4. Consumer (Household buyer) - Instant verified
        cur.execute("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES ('9876543230', 'priya.sharma@example.com', ?, 'consumer', 'retail_buyer', 'verified', 'en')
        """, (pwd,))
        consumer_uid = cur.lastrowid
        cur.execute("""
            INSERT INTO buyer_profiles (user_id, buyer_type, full_name, email, delivery_address, landmark, city, district, pincode)
            VALUES (?, 'retail_buyer', 'Priya Sharma', 'priya.sharma@example.com', 'Flat 402, Green Meadows', 'Near City Mall', 'Pune', 'Pune', '411038')
        """, (consumer_uid,))
        cur.execute("""
            INSERT INTO buyer_addresses (user_id, label, address_line, landmark, city, district, pincode, is_default)
            VALUES (?, 'Home', 'Flat 402, Green Meadows, Kothrud', 'Near City Mall', 'Pune', 'Pune', '411038', 1)
        """, (consumer_uid,))

        # 5. Bulk Buyer - Pending approval
        cur.execute("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES ('9876543240', 'procurement@tajhotel.com', ?, 'consumer', 'bulk_buyer', 'pending', 'en')
        """, (pwd,))
        bulk_uid = cur.lastrowid
        cur.execute("""
            INSERT INTO buyer_profiles (user_id, buyer_type, full_name, business_name, business_type, contact_person_name, email, gstin, delivery_address, city, district, pincode, crops_needed, approx_monthly_qty)
            VALUES (?, 'bulk_buyer', 'Taj Dining Group', 'Grand Vista Foods & Hospitality', 'hotel', 'Vikram Malhotra', 'procurement@tajhotel.com', '27AABCU9603R1ZM', 'Gate 3, Logistics Hub, Hadapsar', 'Pune', 'Pune', '411028', 'Tomato, Potato, Onion, Rice', '5000 kg')
        """, (bulk_uid,))

        # 6. Delivery Driver - Verified
        cur.execute("""
            INSERT INTO users (phone, email, password_hash, role, subtype, approval_status, preferred_language)
            VALUES ('9876543250', 'satish.driver@example.com', ?, 'driver', 'driver', 'verified', 'en')
        """, (pwd,))
        driver_uid = cur.lastrowid
        cur.execute("""
            INSERT INTO driver_profiles (user_id, full_name, city, district, pincodes_served, vehicle_type, vehicle_number, load_capacity_kg, upi_id, is_online, total_deliveries)
            VALUES (?, 'Satish Gaikwad', 'Pune', 'Pune', '411038, 411028, 412205', 'tempo', 'MH-12-AB-3456', 1200, 'satish@upi', 1, 14)
        """, (driver_uid,))

        # 7. Sample Listings
        cur.execute("""
            INSERT INTO listings (farmer_id, crop_name, variety, category, quantity, quantity_left, unit, quality_grade, harvest_date, available_from, available_until, asking_price_per_kg, mandi_price_hint, min_order_qty, max_order_qty, pickup_location, photo_urls, description, status)
            VALUES (?, 'Tomato', 'Hybrid Red', 'vegetables', 800, 750, 'kg', 'A', ?, ?, ?, 23.00, 24.50, 10, 500, 'Khed Shivapur Farm, Pune', '["https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=500"]', 'Freshly harvested firm red tomatoes suitable for daily consumption or restaurant use.', 'active')
        """, (farmer_uid, today_str, today_str, (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')))
        listing1_id = cur.lastrowid

        cur.execute("""
            INSERT INTO listings (farmer_id, crop_name, variety, category, quantity, quantity_left, unit, quality_grade, harvest_date, available_from, available_until, asking_price_per_kg, mandi_price_hint, min_order_qty, max_order_qty, pickup_location, photo_urls, description, status)
            VALUES (?, 'Potato', 'Jyoti A-Grade', 'vegetables', 1500, 1500, 'kg', 'A', ?, ?, ?, 17.50, 18.00, 20, 1000, 'Khed Shivapur Storage, Pune', '["https://images.unsplash.com/photo-1518977676601-b53f82aba655?w=500"]', 'Grade A clean dry potatoes with excellent shelf life.', 'active')
        """, (farmer_uid, today_str, today_str, (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d')))

        cur.execute("""
            INSERT INTO listings (farmer_id, crop_name, variety, category, quantity, quantity_left, unit, quality_grade, harvest_date, available_from, available_until, asking_price_per_kg, mandi_price_hint, min_order_qty, max_order_qty, pickup_location, photo_urls, description, status)
            VALUES (?, 'Onion', 'Nashik Red', 'vegetables', 2000, 2000, 'kg', 'A', ?, ?, ?, 27.00, 28.50, 50, 2000, 'Sahyadri Agro Center, Nashik', '["https://images.unsplash.com/photo-1618512496248-a07fe83aa8cb?w=500"]', 'Top quality Nashik red onions, sorted and graded.', 'active')
        """, (fpo_uid, today_str, today_str, (datetime.now() + timedelta(days=20)).strftime('%Y-%m-%d')))

        # 8. Sample Order & Delivery Job
        cur.execute("""
            INSERT INTO orders (listing_id, farmer_id, buyer_id, quantity, unit, unit_price, crop_total_price, transport_fee, platform_fee, total_amount, payment_method, payment_status, status, buyer_address, buyer_phone, delivery_date, pickup_code, delivery_code, driver_id)
            VALUES (?, ?, ?, 50, 'kg', 23.00, 1150.00, 120.00, 23.00, 1293.00, 'COD', 'unpaid', 'accepted', 'Flat 402, Green Meadows, Kothrud, Pune', '9876543230', ?, '123456', '654321', ?)
        """, (listing1_id, farmer_uid, consumer_uid, today_str, driver_uid))
        order1_id = cur.lastrowid

        cur.execute("""
            INSERT INTO delivery_jobs (order_id, driver_id, pickup_village, pickup_address, drop_city, drop_address, total_weight_kg, distance_km, driver_pay, farmer_pickup_code, buyer_delivery_code, status)
            VALUES (?, ?, 'Khed Shivapur', 'Khed Shivapur Farm, Pune', 'Pune', 'Flat 402, Green Meadows, Kothrud', 50, 18.5, 180.00, '123456', '654321', 'accepted')
        """, (order1_id, driver_uid))

        # Sample Notification
        cur.execute("""
            INSERT INTO notifications (user_id, title, message, type)
            VALUES (?, 'New Order Received', 'You received an order for 50 kg of Tomato (Order #1).', 'order')
        """, (farmer_uid,))

        # Sample RFQ from bulk buyer
        cur.execute("""
            INSERT INTO rfqs (buyer_id, crop_name, variety, min_order_qty, unit, quality_grade, needed_by_date, target_price, delivery_location, status)
            VALUES (?, 'Potato', 'Jyoti', 1000, 'kg', 'A', ?, 17.00, 'Hadapsar, Pune', 'open')
        """, (bulk_uid, (datetime.now() + timedelta(days=5)).strftime('%Y-%m-%d')))

    conn.commit()
    conn.close()
    print("Database schema and seed initialized successfully.")

if __name__ == '__main__':
    init_db()
