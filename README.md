# Farm2you - Agricultural B2B & Direct Supply Network

>  **Live Web Application:** [https://farm2you-1.onrender.com](https://farm2you-1.onrender.com)  
>  **Pre-Seeded Test Accounts:** Listed below under [Pre-Seeded Test Accounts](#pre-seeded-test-accounts) (Farmer, FPO, Retail Buyer, Bulk Buyer, Driver, Admin).

A full-stack agricultural marketplace platform connecting Farmers & FPOs directly with Retail Consumers, Bulk Commercial Buyers, and On-Demand Delivery Drivers with fair Mandi benchmark pricing.

---

## Key Features & 4 Interfaces

### 1. Farmers & Producer Organizations (FPOs) (`/farmer`)
* **Listing Management**: Publish crop harvests with quality grades (A, B, C), asking price, and live Mandi benchmark hints. Active stock is automatically deducted upon order acceptance.
* **Order Management**: Status workflow (`new`, `accepted`, `ready_for_pickup`, `picked_up`, `delivered`), complete fee breakdown (farmer payout, transport fee, 2% platform fee).
* **Privacy by Design**: Buyer phone number is concealed for new orders and revealed only upon acceptance.
* **Handover Verification**: Farmer shares a secure 6-digit pickup code with the fleet driver upon vehicle loading.
* **Mandi Benchmark Comparison**: Compare realized earnings vs. prevailing daily Mandi APMC rates.
* **FPO-Only Extras**: Member farmer roster, cooperative pooling, and order payout split accounting.

### 2. Consumers & Commercial Bulk Buyers (`/buyer`)
* **Retail Consumers**: Instant mobile OTP verification and streamlined produce checkout.
* **Bulk Commercial Buyers**: Hotels, restaurants, and food processors with admin verification for institutional procurement.
* **Marketplace Catalog**: Real-time search, category filters (vegetables, fruits, grains), quality grade tags, and sorting (freshest, price low-to-high, nearest).
* **Transparent Price Composition**: Instant calculation of crop produce cost, distance transport fee, and 2% platform fee.
* **Visual Fulfillment Pipeline**: Real-time tracking from `placed` through `accepted`, `driver_assigned`, `picked_up`, `out_for_delivery`, to `delivered`.
* **Handover Security PIN**: 6-digit delivery drop code shared with the driver upon physical receipt.
* **Commercial RFQ Tenders**: Post institutional requirements, review farmer quotations side-by-side, and convert winning bids into orders.
* **Post-Delivery Operations**: Confirm receipt, submit dispute tickets, submit farmer ratings (1-5 stars), download GST invoice, and repeat order.

### 3. Logistics & Fleet Drivers (`/driver`)
* **Availability Toggle**: Online / Offline switch for route dispatch.
* **Job Board**: Available delivery jobs showing pickup village, drop destination, total cargo weight, and guaranteed driver pay.
* **Multi-Stop Route Plan**: Coordinated pickup address and buyer drop destination.
* **Two-Step PIN Verification**:
  1. Farm Pickup: Enter farmer's 6-digit `pickup_code`.
  2. Buyer Drop: Enter buyer's 6-digit `delivery_code` and confirm Cash on Delivery (COD) collection.
* **Driver Ledger**: Automatic payout crediting and trip history.

### 4. Platform Administration & Governance (`/admin`)
* **Role-Based Access Control**: Super Admin and Moderator privileges; new admins join via verified email or secure invite code.
* **Executive KPI Dashboard**: User distribution by role, active catalog listings, daily order volume, delivered orders, pending approvals, and buyer savings.
* **KYC Verification Queue**: Review submitted identity documents and licenses for Farmers, FPOs, Bulk Buyers, and Drivers with **Approve** or **Reject** (with mandatory reason dispatched via notification).
* **User Directory Governance**: Filter users by subtype and status (`pending`, `verified`, `rejected`, `blocked`) with instantaneous account suspension and restoration controls.
* **Catalog Moderation**: Review, flag, or delist entries violating agricultural quality standards.

---

## 🌐 Multilingual Support
Built-in instant language switching across the entire platform:
* **English**
* **हिन्दी (Hindi)**
* **தமிழ் (Tamil)**
* **తెలుగు (Telugu)**

---

## Tech Stack & Architecture
* **Backend**: Python 3, Flask, Flask-CORS, Flask-JWT-Extended, Werkzeug
* **Database**: SQLite (`farm_db.sqlite`) with automated schema initialization and seeding
* **Frontend**: Vanilla JavaScript (SPA), HTML5, CSS3, FontAwesome icons
* **Deployment**: Production WSGI server (`gunicorn`), `Procfile` ready for Render / Railway / Heroku

---

## Local Setup & Running

1. **Install dependencies**:
   ```powershell
   pip install -r requirements.txt
   ```

2. **Run the server**:
   ```powershell
   python main.py
   ```

3. **Open in browser**:
   ```text
   http://127.0.0.1:5000
   ```

---

## Pre-Seeded Test Accounts

| Role | Identifier / Mobile | Password | Notes |
|---|---|---|---|
| **Super Admin** | `admin@platform.com` | `SuperAdminPass123!` | Full control center |
| **Moderator** | `moderator@platform.com` | `ModPass123!` | Verification & orders |
| **Verified Farmer** | `9876543210` | `Pass1234!` | Ramesh Kumar (Active listings & orders) |
| **Pending Farmer** | `9876543211` | `Pass1234!` | Suresh Patel (Tests approval lock) |
| **FPO Producer** | `9876543220` | `Pass1234!` | Sahyadri Agro FPO (With members) |
| **Retail Consumer** | `9876543230` | `Pass1234!` | Priya Sharma (Instant access) |
| **Bulk Buyer** | `9876543240` | `Pass1234!` | Taj Dining Group (Pending review) |
| **Delivery Driver** | `9876543250` | `Pass1234!` | Satish Gaikwad (Tempo driver) |

*(Note: For any new registration, test mobile OTP code is `123456`)*

---

## Automated Testing
Run the integration test suite:
```powershell
python test_integration.py
python test_features.py
```

