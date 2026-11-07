-- Farm2you Complete Database Schema
-- Implements all 4 Interfaces & Common Specifications

-- 1. Users Table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE,
    email TEXT UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL,                  -- 'producer', 'consumer', 'driver', 'admin'
    subtype TEXT NOT NULL,               -- 'farmer', 'fpo', 'retail_buyer', 'bulk_buyer', 'driver', 'super_admin', 'moderator'
    approval_status TEXT NOT NULL DEFAULT 'pending', -- 'pending', 'verified', 'rejected', 'blocked'
    rejection_reason TEXT,
    preferred_language TEXT DEFAULT 'en', -- 'en', 'hi', 'ta', 'te'
    is_blocked INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 2. OTP Codes Table
CREATE TABLE IF NOT EXISTS otp_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,
    otp_code TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    is_verified INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 3. Farmer Profiles Table
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
);

-- 4. FPO Profiles Table
CREATE TABLE IF NOT EXISTS fpo_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    fpo_name TEXT NOT NULL,
    registration_type TEXT NOT NULL,     -- 'company', 'society', 'cooperative'
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
);

-- 5. FPO Member Farmers Table
CREATE TABLE IF NOT EXISTS fpo_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fpo_user_id INTEGER NOT NULL,
    member_name TEXT NOT NULL,
    phone TEXT,
    village TEXT,
    crops_grown TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (fpo_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 6. Buyer Profiles Table
CREATE TABLE IF NOT EXISTS buyer_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    buyer_type TEXT NOT NULL,            -- 'retail_buyer', 'bulk_buyer'
    full_name TEXT NOT NULL,
    business_name TEXT,
    business_type TEXT,                  -- 'hotel', 'restaurant', 'mess', 'retailer', 'processor', 'other'
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
);

-- 7. Buyer Saved Addresses Table
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
);

-- 8. Driver Profiles Table
CREATE TABLE IF NOT EXISTS driver_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    city TEXT NOT NULL,
    district TEXT NOT NULL,
    pincodes_served TEXT NOT NULL,
    vehicle_type TEXT NOT NULL,          -- 'bike', 'tempo', 'pickup_truck', 'mini_truck'
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
);

-- 9. Listings Table
CREATE TABLE IF NOT EXISTS listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    farmer_id INTEGER NOT NULL,
    fpo_member_id INTEGER,
    is_pooled INTEGER DEFAULT 0,
    crop_name TEXT NOT NULL,
    variety TEXT,
    category TEXT DEFAULT 'vegetables',  -- 'vegetables', 'fruits', 'grains'
    quantity REAL NOT NULL,
    quantity_left REAL NOT NULL,
    unit TEXT DEFAULT 'kg',              -- 'kg', 'quintal'
    quality_grade TEXT DEFAULT 'A',      -- 'A', 'B', 'C'
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
    status TEXT DEFAULT 'active',        -- 'active', 'paused', 'sold_out', 'expired', 'flagged', 'removed'
    flagged_reason TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (fpo_member_id) REFERENCES fpo_members(id) ON DELETE SET NULL
);

-- 10. Orders Table
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
    payment_method TEXT DEFAULT 'COD',    -- 'COD', 'UPI'
    payment_status TEXT DEFAULT 'unpaid', -- 'unpaid', 'paid'
    status TEXT DEFAULT 'new',           -- 'new', 'accepted', 'ready_for_pickup', 'driver_assigned', 'picked_up', 'out_for_delivery', 'delivered', 'cancelled', 'rejected'
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
);

-- 11. Delivery Jobs Table
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
    status TEXT DEFAULT 'open',          -- 'open', 'accepted', 'picked_up', 'delivered', 'failed', 'cancelled'
    failure_reason TEXT,
    failure_photo_url TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    picked_up_at DATETIME,
    delivered_at DATETIME,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 12. Driver Earnings Table
CREATE TABLE IF NOT EXISTS driver_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL,
    job_id INTEGER UNIQUE NOT NULL,
    amount REAL NOT NULL,
    payment_status TEXT DEFAULT 'pending', -- 'pending', 'paid'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (job_id) REFERENCES delivery_jobs(id) ON DELETE CASCADE
);

-- 13. RFQs Table (Bulk buyers)
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
    status TEXT DEFAULT 'open',          -- 'open', 'fulfilled', 'closed'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (buyer_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 14. RFQ Quotes Table
CREATE TABLE IF NOT EXISTS rfq_quotes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rfq_id INTEGER NOT NULL,
    farmer_id INTEGER NOT NULL,
    price_per_kg REAL NOT NULL,
    quantity_offered REAL NOT NULL,
    note TEXT,
    status TEXT DEFAULT 'pending',       -- 'pending', 'accepted', 'rejected'
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (rfq_id) REFERENCES rfqs(id) ON DELETE CASCADE,
    FOREIGN KEY (farmer_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 15. Mandi Prices Table
CREATE TABLE IF NOT EXISTS mandi_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    crop_name TEXT NOT NULL,
    variety TEXT,
    district TEXT NOT NULL,
    price_per_kg REAL NOT NULL,
    date DATE NOT NULL
);

-- 16. Notifications Table
CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    type TEXT DEFAULT 'general',
    is_read INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 17. Feedback Table
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    subject TEXT,
    category TEXT DEFAULT 'general',
    message TEXT NOT NULL,
    rating INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 18. Ratings Table
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
);

-- 19. Issues Table
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    reporter_user_id INTEGER NOT NULL,
    reporter_role TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    reason TEXT NOT NULL,
    photo_url TEXT,
    status TEXT DEFAULT 'open',          -- 'open', 'resolved', 'dismissed'
    admin_notes TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
    FOREIGN KEY (reporter_user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 20. Admin Invites Table
CREATE TABLE IF NOT EXISTS admin_invites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    inviter_admin_id INTEGER,
    invite_code TEXT UNIQUE NOT NULL,
    email TEXT UNIQUE NOT NULL,
    admin_level TEXT DEFAULT 'moderator', -- 'super_admin', 'moderator'
    is_used INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (inviter_admin_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 21. Admin Audit Logs Table
CREATE TABLE IF NOT EXISTS admin_audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_entity TEXT NOT NULL,
    target_id INTEGER,
    details TEXT,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (admin_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 22. System Settings Table
CREATE TABLE IF NOT EXISTS system_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL
);

-- 23. FPO Payment Splits Table
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
);
