// Farm2you Frontend Application Engine
const API_BASE = '';
let currentToken = localStorage.getItem('farm2you_token') || localStorage.getItem('krishi_token') || '';
let currentUser = null;
let currentLang = localStorage.getItem('farm2you_lang') || localStorage.getItem('krishi_lang') || 'en';

let signupRole = 'producer';
let signupSubtype = 'farmer';
let isOtpVerified = false;
let currentListingForCheckout = null;

// Multilingual Dictionary (English, Hindi, Tamil, Telugu)
const I18N = {
    en: {
        app_title: "🌾 Farm2you",
        app_subtitle: "Direct Agri Trade & Logistics",
        hero_title: "Transparent Direct Agricultural Marketplace",
        hero_desc: "Connecting Farmers & FPOs directly with Retail Consumers, Bulk Commercial Buyers, and On-Demand Delivery Drivers with fair mandi pricing benchmarks.",
        btn_getstarted: "Create an Account",
        btn_login: "Sign In",
        lbl_signup: "Sign Up",
        lbl_login: "Log In"
    },
    hi: {
        app_title: "🌾 Farm2you (फार्म टू यू)",
        app_subtitle: "प्रत्यक्ष कृषि व्यापार एवं रसद",
        hero_title: "पारदर्शी प्रत्यक्ष कृषि बाज़ार",
        hero_desc: "किसानों और एफपीओ को सीधे उपभोक्ताओं, थोक खरीदारों और डिलीवरी ड्राइवरों से निष्पक्ष मंडी मूल्य संकेतों के साथ जोड़ना।",
        btn_getstarted: "खाता बनाएं",
        btn_login: "लॉग इन करें",
        lbl_signup: "साइन अप",
        lbl_login: "लॉग इन"
    },
    ta: {
        app_title: "🌾 Farm2you (பார்ம் டு யூ)",
        app_subtitle: "நேரடி விவசாய வர்த்தகம் & விநியோகம்",
        hero_title: "நேரடி விவசாய சந்தை",
        hero_desc: "விவசாயிகளையும் எஃப்பிஓ-க்களையும் நுகர்வோர் மற்றும் மொத்த வாங்குபவர்களுடன் நேரடியாக இணைக்கிறது.",
        btn_getstarted: "பதிவு செய்க",
        btn_login: "உள்நுழைக",
        lbl_signup: "பதிவு",
        lbl_login: "உள்நுழைவு"
    },
    te: {
        app_title: "🌾 Farm2you (ఫార్మ్ టు యు)",
        app_subtitle: "ప్రత్యక్ష వ్యవసాయ వాణిజ్యం & రవాణా",
        hero_title: "ప్రత్యక్ష వ్యవసాయ మార్కెట్",
        hero_desc: "రైతులు మరియు FPOలను నేరుగా వినియోగదారులు మరియు హోల్‌సేల్ వ్యాపారులతో అనుసంధానించడం.",
        btn_getstarted: "ఖాతా తెరవండి",
        btn_login: "లాగిన్ అవ్వండి",
        lbl_signup: "సైన్ అప్",
        lbl_login: "లాగిన్"
    }
};

// Initialization
document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('lang-picker').value = currentLang;
    applyLanguage(currentLang);
    checkAuthSession();
});

function applyLanguage(lang) {
    currentLang = lang;
    localStorage.setItem('farm2you_lang', lang);
    const strings = I18N[lang] || I18N.en;

    document.getElementById('app-title').innerText = strings.app_title;
    document.getElementById('app-subtitle').innerText = strings.app_subtitle;
    if (document.getElementById('txt-hero-title')) document.getElementById('txt-hero-title').innerText = strings.hero_title;
    if (document.getElementById('txt-hero-desc')) document.getElementById('txt-hero-desc').innerText = strings.hero_desc;
    if (document.getElementById('txt-btn-getstarted')) document.getElementById('txt-btn-getstarted').innerText = strings.btn_getstarted;
    if (document.getElementById('txt-btn-login')) document.getElementById('txt-btn-login').innerText = strings.btn_login;
    if (document.getElementById('lbl-signup')) document.getElementById('lbl-signup').innerText = strings.lbl_signup;
    if (document.getElementById('lbl-login')) document.getElementById('lbl-login').innerText = strings.lbl_login;
}

function changeLanguage(lang) {
    applyLanguage(lang);
    if (currentUser) {
        apiFetch('/auth/change-language', {
            method: 'POST',
            body: JSON.stringify({ language: lang })
        });
    }
}

// HTTP Helper with Token
async function apiFetch(endpoint, options = {}) {
    const headers = options.headers || {};
    headers['Content-Type'] = 'application/json';
    if (currentToken) {
        headers['Authorization'] = `Bearer ${currentToken}`;
    }
    options.headers = headers;

    try {
        const response = await fetch(API_BASE + endpoint, options);
        const data = await response.json();
        return { ok: response.ok, status: response.status, data };
    } catch (err) {
        console.error('API Error:', err);
        return { ok: false, status: 500, data: { status: 'error', message: 'Network connectivity failure.' } };
    }
}

// Navigation & View Routing
function showView(viewId) {
    document.querySelectorAll('.view-panel').forEach(el => el.classList.remove('active'));
    const target = document.getElementById(viewId);
    if (target) target.classList.add('active');
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function goHome() {
    if (!currentUser) {
        showView('view-landing');
    } else {
        routeToUserDashboard(currentUser);
    }
}

function showSignupRoleSelect() {
    showView('view-role-select');
}

function showLoginView() {
    showView('view-login');
}

// Check session on load
async function checkAuthSession() {
    if (!currentToken) {
        updateNavbarState(null);
        showView('view-landing');
        return;
    }

    const res = await apiFetch('/auth/me');
    if (res.ok && res.data.user) {
        currentUser = res.data.user;
        updateNavbarState(currentUser);
        routeToUserDashboard(currentUser);
        fetchUnreadNotificationCount();
    } else {
        logoutUser(false);
    }
}

function updateNavbarState(user) {
    const authBar = document.getElementById('auth-user-bar');
    const guestBar = document.getElementById('guest-bar');
    const notifBtn = document.getElementById('notif-btn');

    if (user) {
        authBar.style.display = 'flex';
        guestBar.style.display = 'none';
        notifBtn.style.display = 'flex';
        
        document.getElementById('nav-avatar').innerText = (user.name || user.subtype || 'U')[0].toUpperCase();
        document.getElementById('nav-username').innerText = `${user.name || user.phone} (${user.subtype.replace('_', ' ')})`;
        
        const badge = document.getElementById('nav-badge');
        badge.className = `status-badge ${user.approval_status}`;
        badge.innerText = user.approval_status;
    } else {
        authBar.style.display = 'none';
        guestBar.style.display = 'flex';
        notifBtn.style.display = 'none';
    }
}

function routeToUserDashboard(user) {
    if (user.role === 'producer') {
        showView('view-farmer-portal');
        loadFarmerDashboard();
    } else if (user.role === 'consumer') {
        showView('view-buyer-portal');
        loadBuyerDashboard();
    } else if (user.role === 'driver') {
        showView('view-driver-portal');
        loadDriverDashboard();
    } else if (user.role === 'admin') {
        showView('view-admin-portal');
        loadAdminDashboard();
    } else {
        showView('view-landing');
    }
}

function logoutUser(redirect = true) {
    currentToken = '';
    currentUser = null;
    localStorage.removeItem('farm2you_token');
    localStorage.removeItem('krishi_token');
    updateNavbarState(null);
    if (redirect) showView('view-landing');
}

// Quick Demo Login helper
async function demoLogin(phone, password) {
    const res = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ identifier: phone, password })
    });
    if (res.ok && res.data.token) {
        currentToken = res.data.token;
        currentUser = res.data.user;
        localStorage.setItem('farm2you_token', currentToken);
        updateNavbarState(currentUser);
        routeToUserDashboard(currentUser);
    } else {
        alert(res.data.message || 'Demo login failed');
    }
}

async function demoAdminLogin(email, password) {
    const res = await apiFetch('/admin/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    });
    if (res.ok && res.data.token) {
        currentToken = res.data.token;
        currentUser = {
            id: res.data.admin.id,
            email: res.data.admin.email,
            role: 'admin',
            subtype: res.data.admin.subtype,
            approval_status: res.data.admin.approval_status,
            name: res.data.admin.subtype === 'super_admin' ? 'Super Admin' : 'Moderator'
        };
        localStorage.setItem('farm2you_token', currentToken);
        updateNavbarState(currentUser);
        routeToUserDashboard(currentUser);
    } else {
        alert(res.data.message || 'Admin login failed');
    }
}

// ==================== AUTH & SIGNUP ====================
function startSignup(role, subtype) {
    signupRole = role;
    signupSubtype = subtype;
    isOtpVerified = false;

    document.getElementById('btn-submit-reg').disabled = true;
    document.getElementById('otp-verify-section').style.display = 'none';
    document.getElementById('otp-status-msg').innerText = '';
    document.getElementById('reg-mobile').value = '';
    document.getElementById('reg-otp').value = '';
    document.getElementById('reg-terms').checked = false;

    const titleEl = document.getElementById('signup-title');
    const subtitleEl = document.getElementById('signup-subtitle');
    const container = document.getElementById('dynamic-signup-fields');

    let html = `
        <div class="form-row">
            <div>
                <label>Create Password (min 6 characters) *</label>
                <input type="password" id="reg-password" minlength="6" placeholder="Create strong password" required>
            </div>
            <div>
                <label>Confirm Password *</label>
                <input type="password" id="reg-confirm-password" minlength="6" placeholder="Confirm password" required>
            </div>
        </div>
    `;

    if (subtype === 'farmer') {
        titleEl.innerText = "Step 2a: Farmer Registration";
        subtitleEl.innerText = "Account verified by admin after mobile OTP. Skip Aadhaar (protects your privacy).";
        html += `
            <div class="form-row">
                <div><label>Full Name *</label><input type="text" id="reg-fullname" placeholder="Farmer Name" required></div>
                <div><label>Village *</label><input type="text" id="reg-village" placeholder="Village Name" required></div>
            </div>
            <div class="form-row">
                <div><label>District *</label><input type="text" id="reg-district" placeholder="District" required></div>
                <div><label>State *</label><input type="text" id="reg-state" placeholder="State" required></div>
                <div><label>Pincode *</label><input type="text" id="reg-pincode" maxlength="6" placeholder="6-digit pincode" required></div>
            </div>
            <div>
                <label>Crops Grown (Multi-select / comma-separated) *</label>
                <input type="text" id="reg-crops" placeholder="e.g. Tomato, Onion, Potato, Wheat" required>
            </div>
            <div class="form-row">
                <div><label>UPI ID (for instant direct payments)</label><input type="text" id="reg-upi" placeholder="e.g. name@upi"></div>
                <div><label>Bank Account Number</label><input type="text" id="reg-bank" placeholder="Account Number"></div>
                <div><label>IFSC Code</label><input type="text" id="reg-ifsc" placeholder="e.g. SBIN0001234"></div>
            </div>
            <div>
                <label>FPO Name (if you belong to one - optional dropdown)</label>
                <select id="reg-fpo-name">
                    <option value="">None / Independent Farmer</option>
                    <option value="Sahyadri Agro FPO">Sahyadri Agro FPO</option>
                    <option value="MahaAgri Farmer Producer Co">MahaAgri Farmer Producer Co</option>
                    <option value="Kisan Vikas Cooperative">Kisan Vikas Cooperative</option>
                </select>
            </div>
        `;
    } else if (subtype === 'fpo') {
        titleEl.innerText = "Step 2b: FPO Registration";
        subtitleEl.innerText = "Farmer Producer Organization: Companies, Cooperatives, Societies.";
        html += `
            <div class="form-row">
                <div><label>FPO Name *</label><input type="text" id="reg-fpo-name-input" placeholder="e.g. Sahyadri Agro FPO" required></div>
                <div>
                    <label>Registration Type *</label>
                    <select id="reg-fpo-type">
                        <option value="company">Producer Company</option>
                        <option value="society">Society</option>
                        <option value="cooperative">Cooperative</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div><label>Registration Number *</label><input type="text" id="reg-fpo-regno" placeholder="Registration No" required></div>
                <div><label>Year of Registration *</label><input type="number" id="reg-fpo-year" value="2021" required></div>
            </div>
            <div class="form-row">
                <div><label>Contact Person Name *</label><input type="text" id="reg-fpo-contact" placeholder="Manager Name" required></div>
                <div><label>Designation *</label><input type="text" id="reg-fpo-desig" placeholder="e.g. Managing Director" required></div>
                <div><label>Official Email *</label><input type="email" id="reg-email" placeholder="contact@fpo.org" required></div>
            </div>
            <div>
                <label>Office Address, District, State, Pincode *</label>
                <input type="text" id="reg-fpo-addr" placeholder="Registered office address" required>
            </div>
            <div class="form-row">
                <div><label>District *</label><input type="text" id="reg-district" placeholder="District" required></div>
                <div><label>State *</label><input type="text" id="reg-state" placeholder="State" required></div>
                <div><label>Pincode *</label><input type="text" id="reg-pincode" placeholder="Pincode" required></div>
            </div>
            <div class="form-row">
                <div><label>Number of Member Farmers *</label><input type="number" id="reg-fpo-members" value="50" required></div>
                <div><label>Crops Handled *</label><input type="text" id="reg-crops" placeholder="e.g. Tomato, Grapes, Pomegranate" required></div>
            </div>
            <div class="form-row">
                <div>
                    <label>Storage / Collection Point Available? *</label>
                    <select id="reg-fpo-storage"><option value="yes">Yes</option><option value="no">No</option></select>
                </div>
                <div><label>Storage Capacity (kg)</label><input type="number" id="reg-fpo-cap" placeholder="e.g. 50000"></div>
                <div><label>GSTIN (Optional)</label><input type="text" id="reg-gstin" placeholder="GSTIN"></div>
            </div>
            <div class="form-row">
                <div><label>Bank Account Number *</label><input type="text" id="reg-bank" placeholder="FPO Bank Account" required></div>
                <div><label>IFSC Code *</label><input type="text" id="reg-ifsc" placeholder="IFSC Code" required></div>
            </div>
            <div>
                <label>Upload Registration Certificate URL (or proof document link) *</label>
                <input type="text" id="reg-cert" placeholder="Certificate link or document reference" value="https://doc.platform.org/cert-sample.pdf" required>
            </div>
        `;
    } else if (subtype === 'retail_buyer') {
        titleEl.innerText = "Step 2a: Household Consumer Registration";
        subtitleEl.innerText = "Instant verification via OTP. Start buying fresh produce directly from farms!";
        html += `
            <div class="form-row">
                <div><label>Full Name *</label><input type="text" id="reg-fullname" placeholder="Your Name" required></div>
                <div><label>Email (Optional)</label><input type="email" id="reg-email" placeholder="email@example.com"></div>
            </div>
            <div>
                <label>Delivery Address & Landmark *</label>
                <input type="text" id="reg-addr" placeholder="House/Flat No, Apartment, Street, Landmark" required>
            </div>
            <div class="form-row">
                <div><label>City *</label><input type="text" id="reg-city" placeholder="City" required></div>
                <div><label>Pincode *</label><input type="text" id="reg-pincode" maxlength="6" placeholder="Pincode" required></div>
                <div>
                    <label>Preferred Language</label>
                    <select id="reg-pref-lang">
                        <option value="en">English</option>
                        <option value="hi">हिन्दी</option>
                        <option value="ta">தமிழ்</option>
                        <option value="te">తెలుగు</option>
                    </select>
                </div>
            </div>
        `;
    } else if (subtype === 'bulk_buyer') {
        titleEl.innerText = "Step 2b: Bulk Commercial Buyer Registration";
        subtitleEl.innerText = "Hotels, restaurants, messes, retailers and processors. Verified by admin for large orders.";
        html += `
            <div class="form-row">
                <div><label>Business Name *</label><input type="text" id="reg-bizname" placeholder="e.g. Grand Vista Hotels" required></div>
                <div>
                    <label>Business Type *</label>
                    <select id="reg-biztype" required>
                        <option value="hotel">Hotel</option>
                        <option value="restaurant">Restaurant</option>
                        <option value="mess">Mess or Canteen</option>
                        <option value="retailer">Retailer / Supermarket</option>
                        <option value="processor">Food Processor</option>
                        <option value="other">Other</option>
                    </select>
                </div>
            </div>
            <div class="form-row">
                <div><label>Contact Person Name *</label><input type="text" id="reg-fullname" placeholder="Procurement Manager" required></div>
                <div><label>Business Email *</label><input type="email" id="reg-email" placeholder="procurement@biz.com" required></div>
                <div><label>GSTIN (Optional, with format check)</label><input type="text" id="reg-gstin" placeholder="e.g. 27AABCU9603R1ZM"></div>
            </div>
            <div>
                <label>Delivery Warehouse / Kitchen Address *</label>
                <input type="text" id="reg-addr" placeholder="Receiving warehouse or restaurant address" required>
            </div>
            <div class="form-row">
                <div><label>City *</label><input type="text" id="reg-city" placeholder="City" required></div>
                <div><label>Pincode *</label><input type="text" id="reg-pincode" placeholder="Pincode" required></div>
            </div>
            <div class="form-row">
                <div><label>Crops Needed *</label><input type="text" id="reg-crops" placeholder="e.g. Potato, Onion, Tomato" required></div>
                <div><label>Approx. Monthly Quantity *</label><input type="text" id="reg-monthly-qty" placeholder="e.g. 5000 kg" required></div>
            </div>
        `;
    } else if (subtype === 'driver') {
        titleEl.innerText = "Step 1: Delivery Driver Registration";
        subtitleEl.innerText = "Admin checks driving licence & vehicle details. Once verified, job requests appear.";
        html += `
            <div class="form-row">
                <div><label>Full Name *</label><input type="text" id="reg-fullname" placeholder="Driver Full Name" required></div>
                <div><label>City & District You Serve *</label><input type="text" id="reg-city" placeholder="e.g. Pune" required></div>
            </div>
            <div>
                <label>Pincodes You Serve (comma-separated) *</label>
                <input type="text" id="reg-pincodes" placeholder="e.g. 411038, 411028, 412205" required>
            </div>
            <div class="form-row">
                <div>
                    <label>Vehicle Type *</label>
                    <select id="reg-vtype" required>
                        <option value="tempo">Tempo</option>
                        <option value="pickup_truck">Pickup Truck</option>
                        <option value="mini_truck">Mini Truck</option>
                        <option value="bike">Bike (under 50kg)</option>
                    </select>
                </div>
                <div><label>Vehicle Number *</label><input type="text" id="reg-vnum" placeholder="e.g. MH-12-AB-3456" required></div>
                <div><label>Load Capacity (kg) *</label><input type="number" id="reg-cap" placeholder="e.g. 1000" required></div>
            </div>
            <div>
                <label>Driving Licence Photo URL *</label>
                <input type="text" id="reg-licence" placeholder="Licence document link or photo reference" value="https://doc.platform.org/licence-sample.jpg" required>
            </div>
            <div class="form-row">
                <div><label>UPI ID for Payouts</label><input type="text" id="reg-upi" placeholder="driver@upi"></div>
                <div><label>Bank Account Number</label><input type="text" id="reg-bank" placeholder="Account Number"></div>
                <div><label>IFSC Code</label><input type="text" id="reg-ifsc" placeholder="IFSC Code"></div>
            </div>
        `;
    }

    container.innerHTML = html;
    showView('view-signup-form');
}

async function sendOtpRequest() {
    const mobile = document.getElementById('reg-mobile').value.trim();
    if (!mobile || mobile.length !== 10) {
        alert("Please enter a valid 10-digit mobile number.");
        return;
    }

    const res = await apiFetch('/auth/send-otp', {
        method: 'POST',
        body: JSON.stringify({ phone: mobile })
    });

    if (res.ok) {
        document.getElementById('otp-verify-section').style.display = 'block';
        document.getElementById('reg-otp').value = res.data.otp_code || '123456';
        document.getElementById('otp-status-msg').innerHTML = `<span style="color: green;">${res.data.message}</span>`;
    } else {
        alert(res.data.message || 'Failed to send OTP.');
    }
}

async function verifyOtpRequest() {
    const mobile = document.getElementById('reg-mobile').value.trim();
    const otp = document.getElementById('reg-otp').value.trim();

    const res = await apiFetch('/auth/verify-otp', {
        method: 'POST',
        body: JSON.stringify({ phone: mobile, otp_code: otp })
    });

    if (res.ok) {
        isOtpVerified = true;
        document.getElementById('btn-submit-reg').disabled = false;
        document.getElementById('otp-status-msg').innerHTML = `<span style="color: green; font-weight: bold;"><i class="fa-solid fa-circle-check"></i> Mobile number verified successfully!</span>`;
    } else {
        alert(res.data.message || 'OTP verification failed.');
    }
}

async function handleRegistrationSubmit(e) {
    e.preventDefault();
    if (!isOtpVerified) {
        alert("Please verify your mobile number with OTP before submitting.");
        return;
    }

    const pwd = document.getElementById('reg-password').value;
    const confirmPwd = document.getElementById('reg-confirm-password').value;
    if (pwd !== confirmPwd) {
        alert("Passwords do not match.");
        return;
    }

    const payload = {
        role: signupRole,
        subtype: signupSubtype,
        phone: document.getElementById('reg-mobile').value.trim(),
        password: pwd,
        preferred_language: currentLang
    };

    if (signupSubtype === 'farmer') {
        payload.full_name = document.getElementById('reg-fullname').value;
        payload.village = document.getElementById('reg-village').value;
        payload.district = document.getElementById('reg-district').value;
        payload.state = document.getElementById('reg-state').value;
        payload.pincode = document.getElementById('reg-pincode').value;
        payload.crops_grown = document.getElementById('reg-crops').value;
        payload.upi_id = document.getElementById('reg-upi').value;
        payload.bank_account_no = document.getElementById('reg-bank').value;
        payload.ifsc_code = document.getElementById('reg-ifsc').value;
        payload.fpo_name = document.getElementById('reg-fpo-name').value;
    } else if (signupSubtype === 'fpo') {
        payload.fpo_name = document.getElementById('reg-fpo-name-input').value;
        payload.registration_type = document.getElementById('reg-fpo-type').value;
        payload.registration_number = document.getElementById('reg-fpo-regno').value;
        payload.registration_year = document.getElementById('reg-fpo-year').value;
        payload.contact_person_name = document.getElementById('reg-fpo-contact').value;
        payload.designation = document.getElementById('reg-fpo-desig').value;
        payload.email = document.getElementById('reg-email').value;
        payload.office_address = document.getElementById('reg-fpo-addr').value;
        payload.district = document.getElementById('reg-district').value;
        payload.state = document.getElementById('reg-state').value;
        payload.pincode = document.getElementById('reg-pincode').value;
        payload.member_count = document.getElementById('reg-fpo-members').value;
        payload.crops_handled = document.getElementById('reg-crops').value;
        payload.storage_available = document.getElementById('reg-fpo-storage').value;
        payload.storage_capacity_kg = document.getElementById('reg-fpo-cap').value;
        payload.gstin = document.getElementById('reg-gstin').value;
        payload.bank_account_no = document.getElementById('reg-bank').value;
        payload.ifsc_code = document.getElementById('reg-ifsc').value;
        payload.cert_file_url = document.getElementById('reg-cert').value;
    } else if (signupSubtype === 'retail_buyer') {
        payload.full_name = document.getElementById('reg-fullname').value;
        payload.email = document.getElementById('reg-email').value;
        payload.delivery_address = document.getElementById('reg-addr').value;
        payload.city = document.getElementById('reg-city').value;
        payload.district = document.getElementById('reg-city').value;
        payload.pincode = document.getElementById('reg-pincode').value;
        payload.preferred_language = document.getElementById('reg-pref-lang').value;
    } else if (signupSubtype === 'bulk_buyer') {
        payload.business_name = document.getElementById('reg-bizname').value;
        payload.business_type = document.getElementById('reg-biztype').value;
        payload.full_name = document.getElementById('reg-fullname').value;
        payload.contact_person_name = document.getElementById('reg-fullname').value;
        payload.email = document.getElementById('reg-email').value;
        payload.gstin = document.getElementById('reg-gstin').value;
        payload.delivery_address = document.getElementById('reg-addr').value;
        payload.city = document.getElementById('reg-city').value;
        payload.district = document.getElementById('reg-city').value;
        payload.pincode = document.getElementById('reg-pincode').value;
        payload.crops_needed = document.getElementById('reg-crops').value;
        payload.approx_monthly_qty = document.getElementById('reg-monthly-qty').value;
    } else if (signupSubtype === 'driver') {
        payload.full_name = document.getElementById('reg-fullname').value;
        payload.city = document.getElementById('reg-city').value;
        payload.district = document.getElementById('reg-city').value;
        payload.pincodes_served = document.getElementById('reg-pincodes').value;
        payload.vehicle_type = document.getElementById('reg-vtype').value;
        payload.vehicle_number = document.getElementById('reg-vnum').value;
        payload.load_capacity_kg = document.getElementById('reg-cap').value;
        payload.licence_photo_url = document.getElementById('reg-licence').value;
        payload.upi_id = document.getElementById('reg-upi').value;
        payload.bank_account_no = document.getElementById('reg-bank').value;
        payload.ifsc_code = document.getElementById('reg-ifsc').value;
    }

    const res = await apiFetch('/auth/register', {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (res.ok && res.data.token) {
        currentToken = res.data.token;
        currentUser = res.data.user;
        localStorage.setItem('farm2you_token', currentToken);
        updateNavbarState(currentUser);

        alert(`Registration successful! Your account status is: ${currentUser.approval_status}`);
        routeToUserDashboard(currentUser);
    } else {
        alert(res.data.message || 'Registration failed');
    }
}

// Login
let isOtpLoginMode = false;
function switchLoginMode(mode) {
    isOtpLoginMode = mode === 'otp';
    document.getElementById('tab-login-pwd').classList.toggle('active', !isOtpLoginMode);
    document.getElementById('tab-login-otp').classList.toggle('active', isOtpLoginMode);
    document.getElementById('login-pwd-group').style.display = isOtpLoginMode ? 'none' : 'block';
    document.getElementById('login-otp-group').style.display = isOtpLoginMode ? 'block' : 'none';
}

async function sendLoginOtp() {
    const identifier = document.getElementById('login-identifier').value.trim();
    if (!identifier) {
        alert("Please enter your registered mobile number.");
        return;
    }
    const res = await apiFetch('/auth/send-otp', {
        method: 'POST',
        body: JSON.stringify({ phone: identifier })
    });
    if (res.ok) {
        alert(res.data.message);
        document.getElementById('login-otp').value = res.data.otp_code || '123456';
    } else {
        alert(res.data.message || 'Failed to send OTP.');
    }
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    const identifier = document.getElementById('login-identifier').value.trim();
    const password = document.getElementById('login-password').value;
    const otp_code = document.getElementById('login-otp').value;

    const payload = {
        identifier,
        login_with_otp: isOtpLoginMode,
        password,
        otp_code
    };

    const res = await apiFetch('/auth/login', {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (res.ok && res.data.token) {
        currentToken = res.data.token;
        currentUser = res.data.user;
        localStorage.setItem('farm2you_token', currentToken);
        updateNavbarState(currentUser);
        routeToUserDashboard(currentUser);
    } else {
        alert(res.data.message || 'Invalid credentials');
    }
}

// ==================== INTERFACE 1: FARMER & FPO ====================
let farmerActiveTab = 'listings';
let farmerListings = [];
let farmerOrders = [];

async function loadFarmerDashboard() {
    const res = await apiFetch('/farmer/dashboard');
    if (!res.ok) return;

    const data = res.data.data;
    const statusBanner = document.getElementById('farmer-status-banner');
    const addListingBtn = document.getElementById('btn-add-listing-trigger');

    // Step 3 logic: Until approved, the dashboard opens but the Add Listing button is locked with a message
    if (data.account_status === 'pending') {
        statusBanner.innerHTML = `
            <div class="alert-notice alert-warning">
                <i class="fa-solid fa-hourglass-half" style="font-size: 20px;"></i>
                <div>
                    <strong>Waiting for Administrative Approval:</strong> Your account details are currently in the verification queue.
                    <br><span style="font-size: 13px;">You can view the dashboard and market mandi rates, but publishing new crop listings is locked until verified.</span>
                </div>
            </div>
        `;
        addListingBtn.disabled = true;
        addListingBtn.style.opacity = '0.6';
        addListingBtn.title = 'Add Listing is locked until admin verifies account.';
    } else if (data.account_status === 'rejected') {
        statusBanner.innerHTML = `
            <div class="alert-notice alert-warning" style="background:#fee2e2; border-color:#fca5a5; color:#991b1b;">
                <i class="fa-solid fa-circle-xmark" style="font-size: 20px;"></i>
                <div><strong>Account Review Rejected:</strong> Please contact administrator or update details.</div>
            </div>
        `;
        addListingBtn.disabled = true;
    } else {
        statusBanner.innerHTML = '';
        addListingBtn.disabled = false;
        addListingBtn.style.opacity = '1';
    }

    // Set Welcome Title & FPO Extras Tab
    const isFpo = data.is_fpo;
    document.getElementById('farmer-welcome-title').innerText = isFpo
        ? `🏛️ ${data.profile.fpo_name || 'FPO'} Dashboard`
        : `👨‍🌾 Welcome, ${data.profile.full_name || 'Farmer'}`;

    document.getElementById('tab-fpo-members-btn').style.display = isFpo ? 'inline-block' : 'none';

    // Summary Cards
    document.getElementById('farmer-stat-listings').innerText = data.summary.active_listings;
    document.getElementById('farmer-stat-new-orders').innerText = data.summary.new_orders;
    document.getElementById('farmer-stat-progress').innerText = data.summary.in_progress_orders;
    document.getElementById('farmer-stat-earnings').innerText = `₹${data.summary.total_earnings}`;

    // Mandi Price Strip
    const strip = document.getElementById('farmer-mandi-prices-strip');
    if (data.today_mandi_prices && data.today_mandi_prices.length > 0) {
        strip.innerHTML = data.today_mandi_prices.map(m => `
            <div style="background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 14px; font-size: 13px;">
                <strong>${m.crop_name}</strong> (${m.variety || 'Standard'}): <span style="color: var(--primary); font-weight: bold;">₹${m.price_per_kg}/kg</span>
                <span style="font-size: 11px; color: var(--text-muted); display: block;">Mandi: ${m.district}</span>
            </div>
        `).join('');
    } else {
        strip.innerHTML = '<span style="font-size: 13px; color: var(--text-muted);">No specific mandi price quotes available today.</span>';
    }

    loadFarmerListings();
    loadFarmerOrders();
    loadFarmerEarnings();
    if (isFpo) loadFpoMembers();
    loadFarmerRatings();
}

function switchFarmerTab(tab) {
    farmerActiveTab = tab;
    ['listings', 'orders', 'earnings', 'fpo_members', 'ratings'].forEach(t => {
        const el = document.getElementById(`farmer-tab-${t.replace('_', '-')}`);
        if (el) el.style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('#view-farmer-portal .tab-button').forEach(btn => {
        btn.classList.toggle('active', btn.innerText.toLowerCase().includes(tab.split('_')[0]));
    });
}

async function loadFarmerListings(status = 'all') {
    const res = await apiFetch(`/farmer/listings?status=${status}`);
    if (!res.ok) return;

    farmerListings = res.data.data;
    const container = document.getElementById('farmer-listings-table-container');

    if (farmerListings.length === 0) {
        container.innerHTML = `<div class="card" style="text-align: center; color: var(--text-muted);">No crop listings found in this filter. Tap 'Add New Listing' to sell produce!</div>`;
        return;
    }

    container.innerHTML = `
        <div class="card" style="padding: 0; overflow: hidden;">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Crop & Variety</th>
                            <th>Category</th>
                            <th>Quantity Left</th>
                            <th>Asking Price</th>
                            <th>Quality Grade</th>
                            <th>Status</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${farmerListings.map(l => `
                            <tr>
                                <td>
                                    <strong>${l.crop_name}</strong> ${l.variety ? `(${l.variety})` : ''}
                                    <div style="font-size: 11px; color: var(--text-muted);">${l.pickup_location}</div>
                                </td>
                                <td>${l.category}</td>
                                <td><strong>${l.quantity_left}</strong> / ${l.quantity} ${l.unit}</td>
                                <td><strong style="color: var(--primary);">₹${l.asking_price_per_kg}</strong> / ${l.unit}</td>
                                <td><span class="status-badge" style="background:#e0f2fe; color:#0369a1;">Grade ${l.quality_grade}</span></td>
                                <td><span class="status-badge ${l.status}">${l.status}</span></td>
                                <td>
                                    <div style="display: flex; gap: 6px;">
                                        ${l.status === 'active' ? `
                                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 12px;" onclick="toggleListingStatus(${l.id}, 'paused')">Pause</button>
                                        ` : l.status === 'paused' ? `
                                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 12px;" onclick="toggleListingStatus(${l.id}, 'active')">Activate</button>
                                        ` : ''}
                                        <button class="btn-secondary" style="padding: 4px 8px; font-size: 12px;" onclick="toggleListingStatus(${l.id}, 'sold_out')">Sold Out</button>
                                        <button class="btn-danger" style="padding: 4px 8px; font-size: 12px;" onclick="deleteFarmerListing(${l.id})"><i class="fa-solid fa-trash"></i></button>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function filterFarmerListings(status, btn) {
    btn.parentElement.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    loadFarmerListings(status);
}

async function toggleListingStatus(listingId, status) {
    const res = await apiFetch(`/farmer/listings/${listingId}`, {
        method: 'PUT',
        body: JSON.stringify({ status })
    });
    if (res.ok) {
        loadFarmerListings();
        loadFarmerDashboard();
    } else {
        alert(res.data.message);
    }
}

async function deleteFarmerListing(listingId) {
    if (!confirm("Are you sure you want to delete this listing?")) return;
    const res = await apiFetch(`/farmer/listings/${listingId}`, { method: 'DELETE' });
    if (res.ok) {
        loadFarmerListings();
        loadFarmerDashboard();
    }
}

// Farmer Orders
async function loadFarmerOrders(status = 'all') {
    const res = await apiFetch(`/farmer/orders?status=${status}`);
    if (!res.ok) return;

    farmerOrders = res.data.data;
    const container = document.getElementById('farmer-orders-list-container');

    if (farmerOrders.length === 0) {
        container.innerHTML = `<div class="card" style="text-align:center; color:var(--text-muted);">No orders in this status tab.</div>`;
        return;
    }

    container.innerHTML = farmerOrders.map(o => `
        <div class="card" style="margin-bottom: 16px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-bottom: 12px;">
                <div>
                    <h3 style="font-size: 17px;">Order #${o.id}: ${o.crop_name} (${o.quantity} ${o.unit})</h3>
                    <div style="font-size: 13px; color: var(--text-muted);">Buyer: <strong>${o.buyer_name || 'Consumer'}</strong> | Area: ${o.buyer_area || 'Delivery Destination'}</div>
                    <div style="font-size: 12px; color: #475569; margin-top: 4px;">
                        <i class="fa-solid fa-phone"></i> Buyer Phone: <strong>${o.buyer_phone}</strong>
                    </div>
                </div>
                <div style="text-align: right;">
                    <span class="status-badge ${o.status}" style="font-size: 13px;">${o.status.replace('_', ' ')}</span>
                    <div style="font-size: 12px; color: var(--text-muted); margin-top: 4px;">Payment: <strong>${o.payment_method}</strong> (${o.payment_status})</div>
                </div>
            </div>

            <!-- Price Breakdown (Step 8: what you get, transport, platform fee, buyer pays) -->
            <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 14px; display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; font-size: 13px;">
                <div><span style="color:var(--text-muted);">Farmer Payout:</span> <strong style="color:var(--primary); font-size: 15px;">₹${o.crop_total_price}</strong></div>
                <div><span style="color:var(--text-muted);">Transport Fee:</span> ₹${o.transport_fee}</div>
                <div><span style="color:var(--text-muted);">Platform Fee (2%):</span> ₹${o.platform_fee}</div>
                <div><span style="color:var(--text-muted);">Buyer Total:</span> <strong>₹${o.total_amount}</strong></div>
            </div>

            <!-- Action Buttons based on status -->
            <div style="display: flex; justify-content: flex-end; gap: 10px; align-items: center;">
                ${o.status === 'new' ? `
                    <button class="btn-danger" onclick="rejectOrderWithReason(${o.id})"><i class="fa-solid fa-xmark"></i> Reject Order</button>
                    <button class="btn-primary" onclick="acceptFarmerOrder(${o.id})"><i class="fa-solid fa-check"></i> Accept Order</button>
                ` : o.status === 'accepted' ? `
                    <button class="btn-accent" onclick="markReadyForPickup(${o.id})"><i class="fa-solid fa-box"></i> Mark Ready for Pickup</button>
                ` : o.status === 'ready_for_pickup' ? `
                    <div style="background: #fef3c7; border: 1px solid #fcd34d; padding: 8px 14px; border-radius: 6px; font-size: 13px; color: #92400e;">
                        🔑 Driver Pickup Code: <strong style="letter-spacing: 2px; font-size: 16px;">${o.pickup_code}</strong> (Give this to driver at farm)
                    </div>
                ` : o.status === 'picked_up' ? `
                    <span style="color: #0369a1; font-weight: 600; font-size: 13px;"><i class="fa-solid fa-truck"></i> Produce picked up by driver. Out for delivery.</span>
                ` : o.status === 'delivered' ? `
                    <span style="color: var(--primary); font-weight: 600; font-size: 13px;"><i class="fa-solid fa-circle-check"></i> Delivered & Completed.</span>
                ` : ''}
            </div>
        </div>
    `).join('');
}

function filterFarmerOrders(status, btn) {
    btn.parentElement.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    loadFarmerOrders(status);
}

async function acceptFarmerOrder(orderId) {
    const res = await apiFetch(`/farmer/orders/${orderId}/accept`, { method: 'POST' });
    if (res.ok) {
        alert(res.data.message);
        loadFarmerOrders();
        loadFarmerDashboard();
    } else {
        alert(res.data.message);
    }
}

async function rejectOrderWithReason(orderId) {
    const reason = prompt("Please provide a reason for rejecting this order:");
    if (!reason) return;
    const res = await apiFetch(`/farmer/orders/${orderId}/reject`, {
        method: 'POST',
        body: JSON.stringify({ reason })
    });
    if (res.ok) {
        alert(res.data.message);
        loadFarmerOrders();
        loadFarmerDashboard();
    } else {
        alert(res.data.message);
    }
}

async function markReadyForPickup(orderId) {
    const res = await apiFetch(`/farmer/orders/${orderId}/ready-pickup`, { method: 'POST' });
    if (res.ok) {
        alert(`Marked ready for pickup! Driver pickup code: ${res.data.pickup_code}`);
        loadFarmerOrders();
    } else {
        alert(res.data.message);
    }
}

// Farmer Earnings
async function loadFarmerEarnings() {
    const res = await apiFetch('/farmer/earnings');
    if (!res.ok) return;

    const d = res.data.data;
    const container = document.getElementById('farmer-earnings-container');

    container.innerHTML = `
        <div class="stat-grid">
            <div class="stat-box">
                <h4>Total Earned</h4>
                <div class="val" style="color: var(--primary);">₹${d.total_earned}</div>
                <div class="sub">Completed & paid payouts</div>
            </div>
            <div class="stat-box">
                <h4>Pending Payments</h4>
                <div class="val" style="color: var(--accent);">₹${d.pending_payments}</div>
                <div class="sub">Orders currently in transit</div>
            </div>
        </div>

        <div class="card">
            <h3><i class="fa-solid fa-scale-balanced"></i> Earnings Per-Order History & Mandi Comparison</h3>
            <p style="font-size: 13px; color: var(--text-muted); margin-bottom: 16px;">Comparison of what you received per kg vs prevailing mandi benchmark.</p>
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Order</th>
                            <th>Produce</th>
                            <th>Your Rate</th>
                            <th>Mandi Rate Hint</th>
                            <th>Difference</th>
                            <th>Total Payout</th>
                            <th>Payment Mode</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${d.orders.map(o => `
                            <tr>
                                <td>#${o.id}</td>
                                <td>${o.crop_name} (${o.quantity} ${o.unit})</td>
                                <td><strong>₹${o.unit_price}</strong></td>
                                <td>₹${o.mandi_price_hint || '-'}</td>
                                <td>
                                    <span style="font-weight: bold; color: ${o.mandi_comparison_diff >= 0 ? 'var(--primary)' : '#e11d48'};">
                                        ${o.mandi_comparison_diff >= 0 ? '+' : ''}₹${o.mandi_comparison_diff}
                                    </span>
                                </td>
                                <td><strong style="color: var(--primary);">₹${o.crop_total_price}</strong></td>
                                <td>${o.payment_method}</td>
                                <td><span class="status-badge ${o.payment_status === 'paid' ? 'verified' : 'pending'}">${o.payment_status}</span></td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

// FPO Extras
async function loadFpoMembers() {
    const res = await apiFetch('/farmer/fpo/members');
    if (!res.ok) return;

    const members = res.data.data;
    const container = document.getElementById('fpo-members-management-container');

    container.innerHTML = `
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <div>
                    <h3>FPO Member Farmers</h3>
                    <p style="font-size:13px; color:var(--text-muted);">Manage registered member farmers and record per-order payment splits.</p>
                </div>
                <button class="btn-primary" onclick="addFpoMemberPrompt()"><i class="fa-solid fa-user-plus"></i> Add Member</button>
            </div>

            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Member Farmer Name</th>
                            <th>Phone</th>
                            <th>Village</th>
                            <th>Crops Grown</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${members.map(m => `
                            <tr>
                                <td><strong>${m.member_name}</strong></td>
                                <td>${m.phone || '-'}</td>
                                <td>${m.village || '-'}</td>
                                <td>${m.crops_grown || '-'}</td>
                                <td>
                                    <button class="btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="removeFpoMember(${m.id})">Remove</button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;

    // Also populate FPO Member dropdown in Add Listing wizard
    const memberSelect = document.getElementById('al-fpo-member-id');
    const memberGroup = document.getElementById('al-fpo-member-group');
    if (memberSelect && memberGroup) {
        memberGroup.style.display = 'block';
        memberSelect.innerHTML = `<option value="">-- FPO General Produce --</option>` + members.map(m => `
            <option value="${m.id}">${m.member_name} (${m.village || 'Member'})</option>
        `).join('');
    }
}

async function addFpoMemberPrompt() {
    const member_name = prompt("Enter Member Farmer Full Name:");
    if (!member_name) return;
    const village = prompt("Enter Village:");
    const phone = prompt("Enter Mobile Number:");
    const crops_grown = prompt("Enter Crops Grown:");

    const res = await apiFetch('/farmer/fpo/members', {
        method: 'POST',
        body: JSON.stringify({ member_name, village, phone, crops_grown })
    });
    if (res.ok) {
        alert("Member farmer added.");
        loadFpoMembers();
    }
}

async function removeFpoMember(memberId) {
    if (!confirm("Remove this member farmer?")) return;
    await apiFetch(`/farmer/fpo/members/${memberId}`, { method: 'DELETE' });
    loadFpoMembers();
}

async function loadFarmerRatings() {
    const res = await apiFetch('/farmer/ratings');
    if (!res.ok) return;

    const ratings = res.data.data;
    const container = document.getElementById('farmer-ratings-container');

    if (ratings.length === 0) {
        container.innerHTML = `<div class="card" style="text-align:center; color:var(--text-muted);">No buyer reviews received yet. Ratings appear after orders are delivered.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="card">
            <h3><i class="fa-solid fa-star" style="color: #f59e0b;"></i> Buyer Feedback & Quality Ratings</h3>
            <div style="display: grid; gap: 14px; margin-top: 16px;">
                ${ratings.map(r => `
                    <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                            <strong>${r.buyer_name || 'Consumer'}</strong>
                            <div style="color: #f59e0b; font-weight: bold;">${'★'.repeat(r.rating)}${'☆'.repeat(5 - r.rating)} (${r.rating}/5)</div>
                        </div>
                        <p style="font-size: 13px; color: #475569;">"${r.review || 'No written comment provided.'}"</p>
                        <span style="font-size: 11px; color: var(--text-muted);">${r.created_at}</span>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// Add Listing Wizard
function openAddListingModal() {
    if (currentUser.approval_status !== 'verified') {
        alert("Your account is pending verification. You can add listings once approved by admin.");
        return;
    }
    document.getElementById('modal-add-listing').classList.add('active');
}

function closeAddListingModal() {
    document.getElementById('modal-add-listing').classList.remove('active');
}

async function updateMandiHintForListing(crop) {
    if (!crop) {
        document.getElementById('al-mandi-hint').value = '';
        return;
    }
    const res = await apiFetch(`/utils/mandi-prices?crop=${crop}`);
    if (res.ok && res.data.data.length > 0) {
        const item = res.data.data[0];
        document.getElementById('al-mandi-hint').value = `₹${item.price_per_kg}/kg (${item.district})`;
        document.getElementById('al-price').value = item.price_per_kg;
    } else {
        document.getElementById('al-mandi-hint').value = '₹22.00/kg (Estimated)';
    }
}

async function handleAddListingSubmit(e) {
    e.preventDefault();
    const payload = {
        crop_name: document.getElementById('al-crop').value,
        variety: document.getElementById('al-variety').value,
        category: document.getElementById('al-category').value,
        quality_grade: document.getElementById('al-grade').value,
        quantity: parseFloat(document.getElementById('al-quantity').value),
        unit: document.getElementById('al-unit').value,
        asking_price_per_kg: parseFloat(document.getElementById('al-price').value),
        mandi_price_hint: parseFloat((document.getElementById('al-mandi-hint').value.match(/\d+(\.\d+)?/) || [0])[0]),
        harvest_date: document.getElementById('al-harvest-date').value,
        available_until: document.getElementById('al-available-until').value,
        min_order_qty: parseFloat(document.getElementById('al-min-qty').value || 1),
        pickup_location: document.getElementById('al-pickup-location').value,
        description: document.getElementById('al-desc').value,
        photo_urls: document.getElementById('al-photo').value ? [document.getElementById('al-photo').value] : []
    };

    const fpoMemberSelect = document.getElementById('al-fpo-member-id');
    if (fpoMemberSelect && fpoMemberSelect.value) {
        payload.fpo_member_id = parseInt(fpoMemberSelect.value);
    }

    const res = await apiFetch('/farmer/listings', {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        alert("Produce listing published live!");
        closeAddListingModal();
        loadFarmerListings();
        loadFarmerDashboard();
    } else {
        alert(res.data.message || 'Failed to add listing');
    }
}

// ==================== INTERFACE 2: CONSUMER & BULK BUYER ====================
let buyerActiveTab = 'catalog';
let catalogListings = [];
let searchDebounceTimeout = null;

async function loadBuyerDashboard() {
    const res = await apiFetch('/buyer/dashboard');
    if (!res.ok) return;

    const data = res.data.data;
    const isBulk = data.is_bulk;

    // Status Banner for Bulk Buyer
    const banner = document.getElementById('buyer-status-banner');
    const rfqBtn = document.getElementById('btn-bulk-rfq-trigger');
    const rfqTabBtn = document.getElementById('tab-buyer-rfq-btn');

    if (isBulk) {
        rfqBtn.style.display = 'inline-flex';
        rfqTabBtn.style.display = 'inline-block';
        document.getElementById('buyer-welcome-title').innerText = `🏢 Bulk Commercial Buyer: ${data.profile.business_name || 'Buyer'}`;

        if (data.account_status === 'pending') {
            banner.innerHTML = `
                <div class="alert-notice alert-warning">
                    <i class="fa-solid fa-clock"></i>
                    <div><strong>Bulk Account Pending Verification:</strong> Admin is reviewing your business details and GSTIN. You can browse produce catalog, while large commercial RFQs will activate upon approval.</div>
                </div>
            `;
        } else {
            banner.innerHTML = '';
        }
    } else {
        rfqBtn.style.display = 'none';
        rfqTabBtn.style.display = 'none';
        document.getElementById('buyer-welcome-title').innerText = `🛒 Fresh Produce Marketplace`;
        banner.innerHTML = '';
    }

    // Active Orders Strip
    const strip = document.getElementById('buyer-active-orders-strip');
    if (data.active_orders && data.active_orders.length > 0) {
        strip.style.display = 'block';
        strip.innerHTML = `
            <div class="card" style="background: #eff6ff; border: 1px solid #bfdbfe; padding: 14px;">
                <h4 style="color: #1e40af; margin-bottom: 8px;"><i class="fa-solid fa-bell"></i> Active Orders in Transit:</h4>
                <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                    ${data.active_orders.map(o => `
                        <div style="background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 8px 14px; font-size: 13px;">
                            <strong>Order #${o.id}</strong>: ${o.crop_name} (${o.quantity} ${o.unit}) - <span class="status-badge ${o.status}">${o.status.replace('_', ' ')}</span>
                            <button class="btn-secondary" style="padding: 2px 8px; font-size: 11px; margin-left: 8px;" onclick="viewOrderTracking(${o.id})">Track</button>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } else {
        strip.style.display = 'none';
    }

    loadCatalogListings();
    loadBuyerOrders();
    if (isBulk) loadBuyerRfqs();
    loadBuyerAddresses();
}

function switchBuyerTab(tab) {
    buyerActiveTab = tab;
    ['catalog', 'orders', 'rfqs', 'addresses'].forEach(t => {
        const el = document.getElementById(`buyer-tab-${t}`);
        if (el) el.style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('#view-buyer-portal .tab-button').forEach(btn => {
        btn.classList.toggle('active', btn.innerText.toLowerCase().includes(tab.split('_')[0]));
    });
}

function debounceSearchCatalog() {
    clearTimeout(searchDebounceTimeout);
    searchDebounceTimeout = setTimeout(loadCatalogListings, 300);
}

function selectCategoryChip(cat, btn) {
    btn.parentElement.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    document.getElementById('catalog-category-filter').value = cat;
    loadCatalogListings();
}

async function loadCatalogListings() {
    const search = document.getElementById('catalog-search').value.trim();
    const category = document.getElementById('catalog-category-filter').value;
    const grade = document.getElementById('catalog-grade-filter').value;
    const sort = document.getElementById('catalog-sort-filter').value;

    const res = await apiFetch(`/buyer/listings?search=${encodeURIComponent(search)}&category=${category}&grade=${grade}&sort=${sort}`);
    if (!res.ok) return;

    catalogListings = res.data.data;
    const grid = document.getElementById('catalog-products-grid');

    if (catalogListings.length === 0) {
        grid.innerHTML = `<div class="card" style="grid-column: 1/-1; text-align: center; color: var(--text-muted); padding: 40px;">No produce listings found matching your filters.</div>`;
        return;
    }

    grid.innerHTML = catalogListings.map(l => {
        const photo = (l.photo_urls && l.photo_urls[0]) || 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=500';
        return `
            <div class="product-card" onclick="openCheckoutModal(${l.id})">
                <img src="${photo}" alt="${l.crop_name}" class="product-img">
                <div class="product-body">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <h4 class="product-title">${l.crop_name} ${l.variety ? `(${l.variety})` : ''}</h4>
                        <span class="status-badge" style="background:#e0f2fe; color:#0369a1;">Grade ${l.quality_grade}</span>
                    </div>
                    <div class="product-meta">
                        <span><i class="fa-solid fa-location-dot"></i> ${l.village || l.pickup_location}</span>
                        <span><i class="fa-solid fa-star" style="color: #f59e0b;"></i> ${l.farmer_rating || 5.0}</span>
                    </div>
                    <p style="font-size: 12px; color: var(--text-muted); margin-bottom: 12px;">Farmer: <strong>${l.farmer_name || 'Local Farm'}</strong></p>
                    <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: auto;">
                        <div>
                            <div class="product-price">₹${l.asking_price_per_kg} <span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">/ ${l.unit}</span></div>
                            <span style="font-size: 11px; color: #16a34a;">${l.quantity_left} ${l.unit} in stock</span>
                        </div>
                        <button class="btn-primary" style="padding: 6px 12px; font-size: 12px;">Order Now</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// Listing Detail & Order Checkout Modal (Step 7)
async function openCheckoutModal(listingId) {
    const res = await apiFetch(`/buyer/listings/${listingId}`);
    if (!res.ok) return;

    currentListingForCheckout = res.data.data;
    const l = currentListingForCheckout;
    const container = document.getElementById('checkout-modal-content');

    const photo = (l.photo_urls && l.photo_urls[0]) || 'https://images.unsplash.com/photo-1592924357228-91a4daadcfea?w=500';
    const minOrder = l.min_order_qty || 1;
    const maxOrder = l.max_order_qty || (currentUser.subtype === 'retail_buyer' ? 100 : 5000);

    container.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 20px; margin-bottom: 20px;">
            <img src="${photo}" style="width: 100%; height: 220px; object-fit: cover; border-radius: 8px;">
            <div>
                <h2>${l.crop_name} ${l.variety ? `(${l.variety})` : ''}</h2>
                <div style="font-size: 13px; color: var(--text-muted); margin: 6px 0;">
                    Farmer: <strong>${l.farmer_name}</strong> | Rating: <span style="color:#f59e0b; font-weight:bold;">★ ${l.farmer_rating || 5.0}</span>
                </div>
                <div style="font-size: 24px; font-weight: 800; color: var(--primary-dark); margin: 8px 0;">
                    ₹${l.asking_price_per_kg} <span style="font-size: 14px; font-weight: normal; color: var(--text-muted);">per ${l.unit}</span>
                </div>
                ${l.mandi_benchmark ? `
                    <div style="font-size: 12px; background: #f0fdf4; border: 1px solid #bbf7d0; padding: 6px 10px; border-radius: 6px; color: #166534; margin-bottom: 8px;">
                        Mandi Benchmark Price: <strong>₹${l.mandi_benchmark.price_per_kg}/kg</strong> (${l.mandi_benchmark.district})
                    </div>
                ` : ''}
                <p style="font-size: 13px; color: #475569;">${l.description || 'Direct farm harvested crop with verified sorting.'}</p>
            </div>
        </div>

        <form onsubmit="handlePlaceOrderSubmit(event)">
            <h4 style="margin-bottom: 12px; border-bottom: 1px solid var(--border); padding-bottom: 6px;">Step 7: Place Order</h4>

            <div class="form-row">
                <div>
                    <label>Order Quantity (${l.unit}) * [Min: ${minOrder}, Max: ${maxOrder}]</label>
                    <input type="number" id="order-qty" min="${minOrder}" max="${Math.min(maxOrder, l.quantity_left)}" value="${minOrder}" step="0.5" oninput="calculateCheckoutBreakdown()" required>
                </div>
                <div>
                    <label>Preferred Delivery Date *</label>
                    <input type="date" id="order-date" required>
                </div>
            </div>

            <div>
                <label>Delivery Address *</label>
                <input type="text" id="order-address" placeholder="Flat, building, area, landmark, pincode" required>
            </div>

            <div class="form-row">
                <div>
                    <label>Payment Method *</label>
                    <select id="order-payment-method">
                        <option value="COD">Cash on Delivery (COD at doorstep)</option>
                        <option value="UPI">Direct UPI to Producer</option>
                    </select>
                </div>
            </div>

            <!-- Price Breakdown Calculation Strip -->
            <div id="checkout-pricing-strip" style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin: 16px 0; font-size: 13px;">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>Crop Produce Price:</span>
                    <span id="price-crop">₹0.00</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>Direct Transport & Driver Fee:</span>
                    <span id="price-transport">₹0.00</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                    <span>Platform Service Fee (2%):</span>
                    <span id="price-platform">₹0.00</span>
                </div>
                <div style="display: flex; justify-content: space-between; font-weight: bold; font-size: 16px; border-top: 1px solid var(--border); padding-top: 6px; margin-top: 6px;">
                    <span>Total Amount:</span>
                    <span id="price-total" style="color: var(--primary);">₹0.00</span>
                </div>
            </div>

            <button type="submit" class="btn-primary" style="width: 100%; padding: 14px; font-size: 16px;">
                <i class="fa-solid fa-lock"></i> Confirm & Place Order
            </button>
        </form>
    `;

    // Set default tomorrow date
    const tmrw = new Date();
    tmrw.setDate(tmrw.getDate() + 2);
    document.getElementById('order-date').value = tmrw.toISOString().split('T')[0];

    // Pre-populate address if available
    apiFetch('/buyer/addresses').then(r => {
        if (r.ok && r.data.data.length > 0) {
            const def = r.data.data[0];
            document.getElementById('order-address').value = `${def.address_line}, ${def.city} - ${def.pincode}`;
        }
    });

    calculateCheckoutBreakdown();
    document.getElementById('modal-checkout').classList.add('active');
}

function closeCheckoutModal() {
    document.getElementById('modal-checkout').classList.remove('active');
}

function calculateCheckoutBreakdown() {
    if (!currentListingForCheckout) return;
    const qty = parseFloat(document.getElementById('order-qty').value || 0);
    const unitPrice = parseFloat(currentListingForCheckout.asking_price_per_kg);

    const cropTotal = qty * unitPrice;
    const transport = 100.0 + (qty * 1.5);
    const platform = cropTotal * 0.02;
    const total = cropTotal + transport + platform;

    document.getElementById('price-crop').innerText = `₹${cropTotal.toFixed(2)}`;
    document.getElementById('price-transport').innerText = `₹${transport.toFixed(2)}`;
    document.getElementById('price-platform').innerText = `₹${platform.toFixed(2)}`;
    document.getElementById('price-total').innerText = `₹${total.toFixed(2)}`;
}

async function handlePlaceOrderSubmit(e) {
    e.preventDefault();
    if (!currentListingForCheckout) return;

    const payload = {
        listing_id: currentListingForCheckout.id,
        quantity: parseFloat(document.getElementById('order-qty').value),
        delivery_address: document.getElementById('order-address').value,
        delivery_date: document.getElementById('order-date').value,
        payment_method: document.getElementById('order-payment-method').value
    };

    const res = await apiFetch('/buyer/orders', {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        alert(`Order placed successfully! Order #${res.data.data.order_id}. You can track driver pickup and delivery in your Orders tab.`);
        closeCheckoutModal();
        switchBuyerTab('orders');
        loadBuyerOrders();
    } else {
        alert(res.data.message || 'Failed to place order');
    }
}

// Buyer Orders Tracking (Step 9)
async function loadBuyerOrders() {
    const res = await apiFetch('/buyer/orders');
    if (!res.ok) return;

    const orders = res.data.data;
    const container = document.getElementById('buyer-orders-container');

    if (orders.length === 0) {
        container.innerHTML = `<div class="card" style="text-align:center; color:var(--text-muted); padding:40px;">You have not placed any orders yet.</div>`;
        return;
    }

    container.innerHTML = orders.map(o => {
        const statuses = ['new', 'accepted', 'driver_assigned', 'picked_up', 'out_for_delivery', 'delivered'];
        const currentIdx = statuses.indexOf(o.status);

        return `
            <div class="card" style="margin-bottom: 20px;">
                <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 10px; margin-bottom: 12px;">
                    <div>
                        <h3>Order #${o.id}: ${o.crop_name} (${o.quantity} ${o.unit})</h3>
                        <p style="font-size: 13px; color: var(--text-muted);">Producer: <strong>${o.farmer_name || 'Farm Producer'}</strong> (${o.farmer_village || ''})</p>
                    </div>
                    <div style="text-align: right;">
                        <span class="status-badge ${o.status}" style="font-size: 13px;">${o.status.replace('_', ' ')}</span>
                        <div style="font-size: 15px; font-weight: bold; color: var(--primary); margin-top: 4px;">Total: ₹${o.total_amount}</div>
                    </div>
                </div>

                <!-- Status Progress Line (Step 9) -->
                <div class="tracking-bar">
                    <div class="track-step ${currentIdx >= 0 ? 'done' : ''} ${currentIdx === 0 ? 'current' : ''}">
                        <div class="track-circle"><i class="fa-solid fa-receipt"></i></div>
                        <span>Placed</span>
                    </div>
                    <div class="track-step ${currentIdx >= 1 ? 'done' : ''} ${currentIdx === 1 ? 'current' : ''}">
                        <div class="track-circle"><i class="fa-solid fa-check"></i></div>
                        <span>Accepted</span>
                    </div>
                    <div class="track-step ${currentIdx >= 2 ? 'done' : ''} ${currentIdx === 2 ? 'current' : ''}">
                        <div class="track-circle"><i class="fa-solid fa-id-card"></i></div>
                        <span>Driver Assigned</span>
                    </div>
                    <div class="track-step ${currentIdx >= 3 ? 'done' : ''} ${currentIdx === 3 ? 'current' : ''}">
                        <div class="track-circle"><i class="fa-solid fa-boxes-packing"></i></div>
                        <span>Picked Up</span>
                    </div>
                    <div class="track-step ${currentIdx >= 4 ? 'done' : ''} ${currentIdx === 4 ? 'current' : ''}">
                        <div class="track-circle"><i class="fa-solid fa-truck"></i></div>
                        <span>Out for Delivery</span>
                    </div>
                    <div class="track-step ${currentIdx >= 5 ? 'done' : ''} ${currentIdx === 5 ? 'current' : ''}">
                        <div class="track-circle"><i class="fa-solid fa-house-chimney"></i></div>
                        <span>Delivered</span>
                    </div>
                </div>

                <!-- Driver Info & Delivery Code (Step 9) -->
                <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 14px; margin: 14px 0; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                    <div>
                        ${o.driver_name ? `
                            <div style="font-size: 13px;">🚚 Assigned Driver: <strong>${o.driver_name}</strong> (${o.vehicle_type} - ${o.vehicle_number})</div>
                            <div style="font-size: 12px; color: var(--text-muted);"><i class="fa-solid fa-phone"></i> Driver Phone: <strong>${o.driver_phone || 'Available'}</strong></div>
                        ` : `
                            <div style="font-size: 13px; color: var(--text-muted);">Driver assignment in progress once producer accepts.</div>
                        `}
                    </div>
                    <div style="background: #e0f2fe; border: 1px solid #bae6fd; padding: 6px 14px; border-radius: 6px; text-align: center;">
                        <span style="font-size: 11px; color: #0369a1; text-transform: uppercase; font-weight: bold;">Your Delivery Code</span>
                        <div style="font-size: 18px; font-weight: 800; letter-spacing: 2px; color: #0c4a6e;">${o.delivery_code}</div>
                        <span style="font-size: 10px; color: #0369a1;">(Tell to driver at drop)</span>
                    </div>
                </div>

                <!-- Post Delivery Actions (Step 10) -->
                <div style="display: flex; justify-content: flex-end; gap: 10px; flex-wrap: wrap;">
                    <button class="btn-secondary" onclick="viewOrderInvoice(${o.id})"><i class="fa-solid fa-file-invoice"></i> View Invoice</button>
                    ${o.status === 'out_for_delivery' || o.status === 'picked_up' ? `
                        <button class="btn-primary" onclick="confirmOrderReceived(${o.id})"><i class="fa-solid fa-circle-check"></i> Confirm Received</button>
                    ` : ''}
                    ${o.status === 'delivered' ? `
                        <button class="btn-secondary" onclick="openRateFarmerPrompt(${o.id})"><i class="fa-solid fa-star" style="color:#f59e0b;"></i> Rate Farmer</button>
                        <button class="btn-secondary" onclick="openReportIssuePrompt(${o.id})"><i class="fa-solid fa-triangle-exclamation" style="color:#e11d48;"></i> Report Issue</button>
                    ` : ''}
                    <button class="btn-accent" onclick="repeatOrderAction(${o.id})"><i class="fa-solid fa-arrow-rotate-right"></i> Repeat Order</button>
                </div>
            </div>
        `;
    }).join('');
}

async function confirmOrderReceived(orderId) {
    const res = await apiFetch(`/buyer/orders/${orderId}/confirm-received`, { method: 'POST' });
    if (res.ok) {
        alert("Produce delivery confirmed! Thank you.");
        loadBuyerOrders();
    }
}

async function openRateFarmerPrompt(orderId) {
    const ratingStr = prompt("Rate farmer from 1 to 5 stars (e.g. 5):", "5");
    if (!ratingStr) return;
    const review = prompt("Write a brief review (optional):", "Produce was very fresh and delivered in good condition!");

    const res = await apiFetch(`/buyer/orders/${orderId}/rate`, {
        method: 'POST',
        body: JSON.stringify({ rating: parseInt(ratingStr), review })
    });
    if (res.ok) alert(res.data.message);
}

async function openReportIssuePrompt(orderId) {
    const reason = prompt("Describe the issue (wrong quantity, poor quality, damages):");
    if (!reason) return;
    const res = await apiFetch(`/buyer/orders/${orderId}/report-issue`, {
        method: 'POST',
        body: JSON.stringify({ reason })
    });
    if (res.ok) alert(res.data.message);
}

async function repeatOrderAction(orderId) {
    if (!confirm("Place this exact order again?")) return;
    const res = await apiFetch(`/buyer/orders/${orderId}/repeat`, { method: 'POST' });
    if (res.ok) {
        alert("Repeat order placed!");
        loadBuyerOrders();
    } else {
        alert(res.data.message);
    }
}

function viewOrderInvoice(orderId) {
    apiFetch(`/buyer/orders/${orderId}`).then(res => {
        if (!res.ok) return;
        const o = res.data.data;
        const container = document.getElementById('checkout-modal-content');
        container.innerHTML = `
            <div style="padding: 10px;">
                <div style="display:flex; justify-content:space-between; align-items:center; border-bottom: 2px solid var(--border); padding-bottom: 12px; margin-bottom: 16px;">
                    <div>
                        <h2>🌾 Farm2you GST Invoice</h2>
                        <div style="font-size: 12px; color: var(--text-muted);">Invoice #${o.id} | Date: ${o.created_at}</div>
                    </div>
                    <button class="btn-secondary" onclick="window.print()"><i class="fa-solid fa-print"></i> Print Invoice</button>
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; font-size: 13px; margin-bottom: 20px;">
                    <div>
                        <strong>Farmer Producer:</strong>
                        <div>${o.farmer_name}</div>
                        <div>${o.farmer_village}</div>
                    </div>
                    <div>
                        <strong>Delivery Destination:</strong>
                        <div>${o.buyer_address}</div>
                        <div>Phone: ${o.buyer_phone}</div>
                    </div>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Item Description</th>
                                <th>Quantity</th>
                                <th>Unit Price</th>
                                <th>Total</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>${o.crop_name} (${o.variety || 'A-Grade'})</td>
                                <td>${o.quantity} ${o.unit}</td>
                                <td>₹${o.unit_price}</td>
                                <td>₹${o.crop_total_price}</td>
                            </tr>
                            <tr>
                                <td colspan="3" style="text-align:right;">Transport Fee:</td>
                                <td>₹${o.transport_fee}</td>
                            </tr>
                            <tr>
                                <td colspan="3" style="text-align:right;">Platform Fee (2%):</td>
                                <td>₹${o.platform_fee}</td>
                            </tr>
                            <tr style="font-weight: bold; font-size: 15px;">
                                <td colspan="3" style="text-align:right;">Total Paid (${o.payment_method}):</td>
                                <td style="color: var(--primary);">₹${o.total_amount}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
        document.getElementById('modal-checkout').classList.add('active');
    });
}

// Bulk RFQs (Step 8)
function openBulkRfqModal() {
    document.getElementById('modal-bulk-rfq').classList.add('active');
}

function closeBulkRfqModal() {
    document.getElementById('modal-bulk-rfq').classList.remove('active');
}

async function handleBulkRfqSubmit(e) {
    e.preventDefault();
    const payload = {
        crop_name: document.getElementById('rfq-crop').value,
        variety: document.getElementById('rfq-variety').value,
        min_order_qty: parseFloat(document.getElementById('rfq-qty').value),
        quality_grade: document.getElementById('rfq-grade').value,
        target_price: parseFloat(document.getElementById('rfq-price').value || 0),
        needed_by_date: document.getElementById('rfq-needed-date').value,
        delivery_location: document.getElementById('rfq-location').value
    };

    const res = await apiFetch('/buyer/rfqs', {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        alert("Bulk RFQ requirement published! Nearby farmers and FPOs will submit quotes.");
        closeBulkRfqModal();
        switchBuyerTab('rfqs');
        loadBuyerRfqs();
    } else {
        alert(res.data.message);
    }
}

async function loadBuyerRfqs() {
    const res = await apiFetch('/buyer/rfqs');
    if (!res.ok) return;

    const rfqs = res.data.data;
    const container = document.getElementById('buyer-rfqs-container');

    if (rfqs.length === 0) {
        container.innerHTML = `<div class="card" style="text-align:center; color:var(--text-muted); padding:30px;">No Bulk RFQ requirements posted yet.</div>`;
        return;
    }

    container.innerHTML = rfqs.map(r => `
        <div class="card" style="margin-bottom: 20px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
                <div>
                    <h3>RFQ #${r.id}: ${r.crop_name} (${r.min_order_qty} ${r.unit})</h3>
                    <p style="font-size: 13px; color: var(--text-muted);">Needed By: <strong>${r.needed_by_date}</strong> | Target Price: ₹${r.target_price}/kg | Location: ${r.delivery_location}</p>
                </div>
                <span class="status-badge ${r.status === 'open' ? 'active' : 'verified'}">${r.status}</span>
            </div>

            <!-- Quotes side-by-side comparison (Step 8.3) -->
            <h4 style="font-size: 14px; margin-bottom: 8px;">Submitted Farmer Quotes (${r.quotes ? r.quotes.length : 0})</h4>
            ${r.quotes && r.quotes.length > 0 ? `
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px;">
                    ${r.quotes.map(q => `
                        <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
                            <div style="display: flex; justify-content: space-between;">
                                <strong>${q.farmer_name}</strong>
                                <span style="font-size: 12px; color: #f59e0b;">★ ${q.farmer_rating || 5.0}</span>
                            </div>
                            <div style="font-size: 12px; color: var(--text-muted);">${q.village || 'Local Farm'}</div>
                            <div style="font-size: 20px; font-weight: 800; color: var(--primary); margin: 8px 0;">
                                ₹${q.price_per_kg} / kg
                            </div>
                            <div style="font-size: 12px;">Supply Quantity: <strong>${q.quantity_offered} ${r.unit}</strong></div>
                            <div style="margin-top: 10px;">
                                ${q.status === 'accepted' ? `
                                    <span class="status-badge verified">Accepted Quote</span>
                                ` : r.status === 'open' ? `
                                    <button class="btn-primary" style="width: 100%; padding: 6px;" onclick="acceptRfqQuote(${r.id}, ${q.id})">Accept & Order</button>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : `
                <div style="font-size: 13px; color: var(--text-muted); font-style: italic;">Awaiting producer quotes...</div>
            `}
        </div>
    `).join('');
}

async function acceptRfqQuote(rfqId, quoteId) {
    if (!confirm("Accept this quote and generate order?")) return;
    const res = await apiFetch(`/buyer/rfqs/${rfqId}/accept-quote/${quoteId}`, { method: 'POST' });
    if (res.ok) {
        alert(res.data.message);
        loadBuyerRfqs();
        loadBuyerOrders();
    } else {
        alert(res.data.message);
    }
}

// Buyer Saved Addresses
async function loadBuyerAddresses() {
    const res = await apiFetch('/buyer/addresses');
    if (!res.ok) return;

    const addresses = res.data.data;
    const container = document.getElementById('buyer-addresses-container');

    container.innerHTML = `
        <div class="card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px;">
                <h3>Saved Delivery Addresses</h3>
                <button class="btn-primary" onclick="addBuyerAddressPrompt()"><i class="fa-solid fa-plus"></i> Add Address</button>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px;">
                ${addresses.map(a => `
                    <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 14px;">
                        <div style="display: flex; justify-content: space-between;">
                            <strong>${a.label}</strong>
                            ${a.is_default ? '<span class="status-badge verified">Default</span>' : ''}
                        </div>
                        <p style="font-size: 13px; color: #475569; margin-top: 6px;">${a.address_line}</p>
                        <div style="font-size: 12px; color: var(--text-muted);">${a.city}, ${a.district} - ${a.pincode}</div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

async function addBuyerAddressPrompt() {
    const address_line = prompt("Enter Address Line:");
    if (!address_line) return;
    const city = prompt("Enter City:");
    const pincode = prompt("Enter Pincode:");

    const res = await apiFetch('/buyer/addresses', {
        method: 'POST',
        body: JSON.stringify({ address_line, city, pincode, is_default: 1 })
    });
    if (res.ok) loadBuyerAddresses();
}

// ==================== INTERFACE 3: PICKUP AND DELIVERY DRIVER ====================
async function loadDriverDashboard() {
    const res = await apiFetch('/driver/dashboard');
    if (!res.ok) return;

    const data = res.data.data;
    const banner = document.getElementById('driver-status-banner');
    const onlineBtn = document.getElementById('btn-driver-online-toggle');
    const onlineText = document.getElementById('lbl-driver-online-text');

    // Verification check (Step 2: Until approved, the driver cannot see jobs)
    if (data.account_status === 'pending') {
        banner.innerHTML = `
            <div class="alert-notice alert-warning">
                <i class="fa-solid fa-hourglass-half"></i>
                <div><strong>Driver Account Pending Verification:</strong> Admin is reviewing your driving licence and vehicle details. Jobs feed will activate once verified.</div>
            </div>
        `;
        onlineBtn.disabled = true;
    } else {
        banner.innerHTML = '';
        onlineBtn.disabled = false;
    }

    // Online toggle
    if (data.is_online) {
        onlineBtn.style.background = '#e11d48';
        onlineText.innerText = 'Go Offline';
    } else {
        onlineBtn.style.background = 'var(--primary)';
        onlineText.innerText = 'Go Online';
    }

    // Metrics
    document.getElementById('driver-stat-jobs-today').innerText = data.metrics.jobs_today;
    document.getElementById('driver-stat-earnings-today').innerText = `₹${data.metrics.earnings_today}`;
    document.getElementById('driver-stat-total-deliveries').innerText = data.metrics.total_deliveries;

    // Current Active Job (Step 5)
    renderDriverCurrentJob(data.current_job);

    // Available Jobs Feed
    renderDriverAvailableJobs(data.available_jobs, data.is_verified, data.is_online);

    // Driver Earnings History
    loadDriverEarningsHistory();
}

async function toggleDriverOnlineStatus() {
    const res = await apiFetch('/driver/toggle-online', { method: 'POST' });
    if (res.ok) loadDriverDashboard();
}

function renderDriverCurrentJob(job) {
    const container = document.getElementById('driver-current-job-container');
    if (!job) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = `
        <div class="card" style="border: 2px solid var(--accent); background: #fffbeb;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 14px;">
                <h3 style="color: #b45309;"><i class="fa-solid fa-truck-ramp-box"></i> Active Route Job #${job.id}: ${job.crop_name} (${job.total_weight_kg} kg)</h3>
                <span class="status-badge ${job.status}" style="font-size: 13px;">${job.status.replace('_', ' ')}</span>
            </div>

            <!-- Multi-stop Pickup Plan (Step 5.3) -->
            <h4 style="font-size: 13px; text-transform: uppercase; color: #92400e; margin-bottom: 8px;">Optimized Stops Timeline</h4>
            <div class="stops-timeline">
                <div class="stop-item">
                    <strong>Stop 1: Farm Pickup - ${job.pickup_village}</strong>
                    <div style="font-size: 13px; color: #475569;">${job.pickup_address}</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Farmer: <strong>${job.farmer_name}</strong> | <a href="tel:${job.farmer_phone}" style="color:var(--primary); font-weight:bold;"><i class="fa-solid fa-phone"></i> Call Farmer</a></div>
                    
                    ${job.status === 'accepted' ? `
                        <div style="background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-top: 10px;">
                            <label>Enter Pickup Code Shown by Farmer (Step 5.5) *</label>
                            <div style="display: flex; gap: 8px;">
                                <input type="text" id="verify-farm-pickup-code" placeholder="6-digit code" maxlength="6" style="margin: 0; font-size: 16px; letter-spacing: 2px;">
                                <button class="btn-primary" onclick="submitFarmPickupVerification(${job.id})"><i class="fa-solid fa-check"></i> Mark Picked Up</button>
                            </div>
                        </div>
                    ` : `
                        <div style="font-size: 12px; color: green; margin-top: 4px;"><i class="fa-solid fa-check-circle"></i> Produce picked up successfully.</div>
                    `}
                </div>

                <div class="stop-item">
                    <strong>Stop 2: Buyer Destination - ${job.drop_city}</strong>
                    <div style="font-size: 13px; color: #475569;">${job.drop_address}</div>
                    <div style="font-size: 12px; color: var(--text-muted);">Buyer: <strong>${job.buyer_name}</strong> | <a href="tel:${job.buyer_phone}" style="color:var(--primary); font-weight:bold;"><i class="fa-solid fa-phone"></i> Call Buyer</a></div>
                    
                    ${job.status === 'picked_up' ? `
                        <div style="background: white; border: 1px solid #cbd5e1; border-radius: 8px; padding: 12px; margin-top: 10px;">
                            <label>Enter Delivery Code from Buyer (Step 5.8) *</label>
                            <div style="display: flex; gap: 8px; margin-bottom: 8px;">
                                <input type="text" id="verify-buyer-delivery-code" placeholder="6-digit code" maxlength="6" style="margin: 0; font-size: 16px; letter-spacing: 2px;">
                                <button class="btn-primary" onclick="submitBuyerDropVerification(${job.id}, '${job.payment_method}', ${job.total_amount})"><i class="fa-solid fa-circle-check"></i> Mark Delivered</button>
                            </div>
                            ${job.payment_method === 'COD' ? `
                                <div style="font-size: 12px; color: #b45309; font-weight: bold;">
                                    💵 Collect Cash on Delivery: ₹${job.total_amount}
                                </div>
                            ` : ''}
                        </div>
                    ` : ''}
                </div>
            </div>

            <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 14px; border-top: 1px solid #fde68a; padding-top: 10px;">
                <span style="font-size: 13px;">Driver Pay for this trip: <strong style="color: var(--primary); font-size: 16px;">₹${job.driver_pay}</strong></span>
                <button class="btn-danger" style="padding: 6px 12px;" onclick="driverReportIssuePrompt(${job.id})"><i class="fa-solid fa-triangle-exclamation"></i> Report Issue</button>
            </div>
        </div>
    `;
}

async function submitFarmPickupVerification(jobId) {
    const code = document.getElementById('verify-farm-pickup-code').value.trim();
    if (!code) {
        alert("Please enter the 6-digit pickup code provided by the farmer.");
        return;
    }
    const res = await apiFetch(`/driver/jobs/${jobId}/verify-pickup`, {
        method: 'POST',
        body: JSON.stringify({ pickup_code: code })
    });
    if (res.ok) {
        alert(res.data.message);
        loadDriverDashboard();
    } else {
        alert(res.data.message);
    }
}

async function submitBuyerDropVerification(jobId, payMethod, totalAmount) {
    const code = document.getElementById('verify-buyer-delivery-code').value.trim();
    if (!code) {
        alert("Please enter the 6-digit delivery code provided by the buyer.");
        return;
    }

    let cashCollected = 0;
    if (payMethod === 'COD') {
        const cashStr = prompt(`COD Order: Confirm cash amount collected from buyer (Total ₹${totalAmount}):`, totalAmount);
        if (cashStr === null) return;
        cashCollected = parseFloat(cashStr || 0);
    }

    const res = await apiFetch(`/driver/jobs/${jobId}/verify-delivery`, {
        method: 'POST',
        body: JSON.stringify({ delivery_code: code, cash_collected: cashCollected })
    });
    if (res.ok) {
        alert(res.data.message);
        loadDriverDashboard();
    } else {
        alert(res.data.message);
    }
}

async function driverReportIssuePrompt(jobId) {
    const reason = prompt("Describe issue (farmer not available, buyer refused, goods damaged, road blocked):");
    if (!reason) return;
    const res = await apiFetch(`/driver/jobs/${jobId}/report-issue`, {
        method: 'POST',
        body: JSON.stringify({ reason })
    });
    if (res.ok) {
        alert(res.data.message);
        loadDriverDashboard();
    }
}

function renderDriverAvailableJobs(jobs, isVerified, isOnline) {
    const container = document.getElementById('driver-available-jobs-container');
    if (!isVerified) {
        container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">Jobs locked: Driver licence and vehicle verification required.</div>`;
        return;
    }
    if (!isOnline) {
        container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">You are currently Offline. Tap 'Go Online' above to view nearby jobs.</div>`;
        return;
    }
    if (!jobs || jobs.length === 0) {
        container.innerHTML = `<div style="text-align: center; color: var(--text-muted); padding: 20px;">No available jobs in your service area right now. Refreshing regularly.</div>`;
        return;
    }

    container.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 16px;">
            ${jobs.map(j => `
                <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 16px; display: flex; flex-direction: column;">
                    <div style="display: flex; justify-content: space-between; align-items: flex-start;">
                        <strong>${j.crop_name} (${j.total_weight_kg} kg)</strong>
                        <span style="font-size: 18px; font-weight: 800; color: var(--primary);">₹${j.driver_pay}</span>
                    </div>
                    <div style="font-size: 12px; color: var(--text-muted); margin: 8px 0;">
                        <div><i class="fa-solid fa-location-arrow" style="color:var(--primary);"></i> Pickup: <strong>${j.pickup_village}</strong></div>
                        <div><i class="fa-solid fa-location-dot" style="color:var(--accent);"></i> Drop: <strong>${j.drop_city}</strong></div>
                        <div><i class="fa-solid fa-road"></i> Distance: ~${j.distance_km || 15} km</div>
                    </div>
                    <button class="btn-primary" style="margin-top: auto; padding: 8px;" onclick="acceptDriverJob(${j.id})">
                        <i class="fa-solid fa-circle-check"></i> Accept Delivery Job
                    </button>
                </div>
            `).join('')}
        </div>
    `;
}

async function acceptDriverJob(jobId) {
    const res = await apiFetch(`/driver/jobs/${jobId}/accept`, { method: 'POST' });
    if (res.ok) {
        alert("Job accepted! Proceeding to pickup location.");
        loadDriverDashboard();
    } else {
        alert(res.data.message);
    }
}

async function loadDriverEarningsHistory() {
    const res = await apiFetch('/driver/earnings');
    if (!res.ok) return;

    const data = res.data.data;
    const container = document.getElementById('driver-earnings-table-container');

    if (!data.jobs || data.jobs.length === 0) {
        container.innerHTML = `<div style="text-align:center; color:var(--text-muted); padding:20px;">No completed delivery payouts recorded yet.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="table-responsive">
            <table>
                <thead>
                    <tr>
                        <th>Job ID</th>
                        <th>Route</th>
                        <th>Weight</th>
                        <th>Driver Pay</th>
                        <th>Status</th>
                        <th>Payout Status</th>
                    </tr>
                </thead>
                <tbody>
                    ${data.jobs.map(j => `
                        <tr>
                            <td>#${j.id}</td>
                            <td>${j.pickup_village} ➔ ${j.drop_city}</td>
                            <td>${j.total_weight_kg} kg</td>
                            <td><strong style="color: var(--primary);">₹${j.driver_pay}</strong></td>
                            <td><span class="status-badge ${j.status}">${j.status}</span></td>
                            <td><span class="status-badge ${j.payment_status === 'paid' ? 'verified' : 'pending'}">${j.payment_status || 'pending'}</span></td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// ==================== INTERFACE 4: ADMIN CONTROL CENTER ====================
let adminActiveTab = 'verifications';

async function loadAdminDashboard() {
    const res = await apiFetch('/admin/dashboard');
    if (!res.ok) return;

    const d = res.data.data;

    // Metrics
    document.getElementById('admin-stat-users').innerText = d.metrics.users_by_type.total;
    document.getElementById('admin-stat-users-breakdown').innerText = `${d.metrics.users_by_type.farmers} Farmers, ${d.metrics.users_by_type.fpos} FPOs, ${d.metrics.users_by_type.retail_buyers} Retail, ${d.metrics.users_by_type.bulk_buyers} Bulk, ${d.metrics.users_by_type.drivers} Drivers`;
    document.getElementById('admin-stat-listings').innerText = d.metrics.active_listings;
    document.getElementById('admin-stat-orders-today').innerText = d.metrics.orders_today;
    document.getElementById('admin-stat-orders-delivered').innerText = `${d.metrics.orders_delivered} Delivered`;
    document.getElementById('admin-stat-pending').innerText = d.metrics.pending_verifications;
    document.getElementById('admin-stat-issues').innerText = d.metrics.open_issues;
    document.getElementById('admin-stat-savings').innerText = `₹${d.metrics.total_buyer_savings}`;

    // Stuck Orders Monitor
    const stuckContainer = document.getElementById('admin-stuck-orders-container');
    if (d.stuck_orders && d.stuck_orders.length > 0) {
        stuckContainer.innerHTML = `
            <div class="card" style="background: #fef2f2; border: 1px solid #fecaca; margin-bottom: 20px;">
                <h4 style="color: #991b1b;"><i class="fa-solid fa-triangle-exclamation"></i> Orders Stuck For Too Long (> 24 hours):</h4>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-top: 8px;">
                    ${d.stuck_orders.map(o => `
                        <div style="background: white; border: 1px solid #f87171; border-radius: 6px; padding: 6px 12px; font-size: 12px;">
                            Order #${o.id} (${o.crop_name}, ${o.quantity} ${o.unit}) - Stuck in '${o.status}' since ${o.created_at}
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    } else {
        stuckContainer.innerHTML = '';
    }

    loadAdminVerifications();
    loadAdminUsers();
    loadAdminListings();
    loadAdminIssues();
    renderAdminAnalytics(d.charts);
}

function switchAdminTab(tab) {
    adminActiveTab = tab;
    ['verifications', 'users', 'listings', 'issues', 'analytics'].forEach(t => {
        const el = document.getElementById(`admin-tab-${t}`);
        if (el) el.style.display = t === tab ? 'block' : 'none';
    });
    document.querySelectorAll('#view-admin-portal .tab-button').forEach(btn => {
        btn.classList.toggle('active', btn.innerText.toLowerCase().includes(tab.split('_')[0]));
    });
}

// Verification Queue (Step 4)
async function loadAdminVerifications(type = 'all') {
    const res = await apiFetch(`/admin/verifications?type=${type}`);
    if (!res.ok) return;

    const queue = res.data.data;
    const container = document.getElementById('admin-verifications-container');

    if (queue.length === 0) {
        container.innerHTML = `<div class="card" style="text-align:center; color:var(--text-muted); padding:30px;">Verification queue is empty! All users approved.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="card" style="padding: 0; overflow: hidden;">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Applicant</th>
                            <th>Role & Type</th>
                            <th>Submitted Details & Documents</th>
                            <th>Date Applied</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${queue.map(u => `
                            <tr>
                                <td>
                                    <strong>${u.details ? (u.details.full_name || u.details.fpo_name || u.details.business_name || u.phone) : u.phone}</strong>
                                    <div style="font-size: 11px; color: var(--text-muted);">${u.phone} | ${u.email || ''}</div>
                                </td>
                                <td><span class="status-badge" style="background:#e0f2fe; color:#0369a1;">${u.subtype.replace('_', ' ')}</span></td>
                                <td>
                                    <div style="font-size: 12px; color: #475569;">
                                        ${u.subtype === 'farmer' ? `
                                            Village: ${u.details ? u.details.village : '-'}, Crops: ${u.details ? u.details.crops_grown : '-'}, UPI: ${u.details ? u.details.upi_id : '-'}
                                        ` : u.subtype === 'fpo' ? `
                                            Reg No: ${u.details ? u.details.registration_number : '-'}, Members: ${u.details ? u.details.member_count : '-'}, Cert: <a href="${u.details ? u.details.cert_file_url : '#'}" target="_blank" style="color:var(--primary); font-weight:bold;">View Cert</a>
                                        ` : u.subtype === 'bulk_buyer' ? `
                                            Biz: ${u.details ? u.details.business_name : '-'} (${u.details ? u.details.business_type : '-'}), GSTIN: ${u.details ? u.details.gstin : '-'}, Monthly: ${u.details ? u.details.approx_monthly_qty : '-'}
                                        ` : u.subtype === 'driver' ? `
                                            Vehicle: ${u.details ? u.details.vehicle_number : '-'} (${u.details ? u.details.vehicle_type : '-'}), Licence: <a href="${u.details ? u.details.licence_photo_url : '#'}" target="_blank" style="color:var(--primary); font-weight:bold;">View Licence</a>
                                        ` : ''}
                                    </div>
                                </td>
                                <td>${u.created_at}</td>
                                <td>
                                    <div style="display: flex; gap: 8px;">
                                        <button class="btn-primary" style="padding: 4px 10px; font-size: 12px;" onclick="actionVerification(${u.id}, 'approve')">Approve</button>
                                        <button class="btn-danger" style="padding: 4px 10px; font-size: 12px;" onclick="actionVerification(${u.id}, 'reject')">Reject</button>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

function filterVerificationQueue(type, btn) {
    btn.parentElement.querySelectorAll('.chip').forEach(c => c.classList.remove('active'));
    btn.classList.add('active');
    loadAdminVerifications(type);
}

async function actionVerification(userId, action) {
    let reason = '';
    if (action === 'reject') {
        reason = prompt("Rejection Reason (Required - user will be notified):");
        if (!reason) return;
    }

    const res = await apiFetch(`/admin/verifications/${userId}/action`, {
        method: 'POST',
        body: JSON.stringify({ action, reason })
    });

    if (res.ok) {
        alert(res.data.message);
        loadAdminDashboard();
    } else {
        alert(res.data.message);
    }
}

// User Management (Step 5)
async function loadAdminUsers() {
    const res = await apiFetch('/admin/users');
    if (!res.ok) return;

    const users = res.data.data;
    const container = document.getElementById('admin-tab-users');

    container.innerHTML = `
        <div class="card" style="padding: 0; overflow: hidden;">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>User ID</th>
                            <th>Phone / Identifier</th>
                            <th>Role & Subtype</th>
                            <th>Approval Status</th>
                            <th>Joined Date</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${users.map(u => `
                            <tr>
                                <td>#${u.id}</td>
                                <td><strong>${u.phone}</strong> ${u.email ? `(${u.email})` : ''}</td>
                                <td>${u.subtype.replace('_', ' ')}</td>
                                <td><span class="status-badge ${u.approval_status}">${u.approval_status}</span></td>
                                <td>${u.created_at}</td>
                                <td>
                                    <button class="${u.is_blocked || u.approval_status === 'blocked' ? 'btn-primary' : 'btn-danger'}" style="padding: 4px 10px; font-size: 12px;" onclick="toggleUserBlock(${u.id})">
                                        ${u.is_blocked || u.approval_status === 'blocked' ? 'Unblock' : 'Block User'}
                                    </button>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

async function toggleUserBlock(userId) {
    const res = await apiFetch(`/admin/users/${userId}/block-toggle`, { method: 'POST' });
    if (res.ok) {
        alert(res.data.message);
        loadAdminUsers();
        loadAdminDashboard();
    }
}

// Listing Moderation (Step 6)
async function loadAdminListings() {
    const res = await apiFetch('/admin/listings');
    if (!res.ok) return;

    const listings = res.data.data;
    const container = document.getElementById('admin-tab-listings');

    container.innerHTML = `
        <div class="card" style="padding: 0; overflow: hidden;">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Listing</th>
                            <th>Farmer</th>
                            <th>Quantity Left</th>
                            <th>Price</th>
                            <th>Status</th>
                            <th>Moderation Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${listings.map(l => `
                            <tr>
                                <td>
                                    <strong>${l.crop_name}</strong> ${l.variety ? `(${l.variety})` : ''}
                                    <div style="font-size: 11px; color: var(--text-muted);">${l.pickup_location}</div>
                                </td>
                                <td>${l.farmer_name || l.farmer_phone}</td>
                                <td>${l.quantity_left} / ${l.quantity} ${l.unit}</td>
                                <td>₹${l.asking_price_per_kg}</td>
                                <td><span class="status-badge ${l.status}">${l.status}</span></td>
                                <td>
                                    <div style="display: flex; gap: 6px;">
                                        ${l.status === 'active' ? `
                                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="moderateListingAction(${l.id}, 'pause')">Pause</button>
                                        ` : `
                                            <button class="btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="moderateListingAction(${l.id}, 'restore')">Restore</button>
                                        `}
                                        <button class="btn-danger" style="padding: 4px 8px; font-size: 11px;" onclick="moderateListingAction(${l.id}, 'remove')">Remove</button>
                                    </div>
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

async function moderateListingAction(listingId, action) {
    const reason = prompt(`Reason for ${action}ing listing (e.g. fake photo, incorrect pricing):`);
    if (!reason) return;
    const res = await apiFetch(`/admin/listings/${listingId}/moderate`, {
        method: 'POST',
        body: JSON.stringify({ action, reason })
    });
    if (res.ok) {
        alert(res.data.message);
        loadAdminListings();
    }
}

// Issues Moderation
async function loadAdminIssues() {
    const res = await apiFetch('/admin/issues');
    if (!res.ok) return;

    const issues = res.data.data;
    const container = document.getElementById('admin-tab-issues');

    if (issues.length === 0) {
        container.innerHTML = `<div class="card" style="text-align:center; color:var(--text-muted); padding:30px;">No open dispute issues.</div>`;
        return;
    }

    container.innerHTML = `
        <div class="card" style="padding: 0; overflow: hidden;">
            <div class="table-responsive">
                <table>
                    <thead>
                        <tr>
                            <th>Issue ID</th>
                            <th>Order #</th>
                            <th>Reported By</th>
                            <th>Issue Type & Details</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${issues.map(i => `
                            <tr>
                                <td>#${i.id}</td>
                                <td>Order #${i.order_id}</td>
                                <td>${i.reporter_role.toUpperCase()} (${i.reporter_phone})</td>
                                <td>
                                    <strong>${i.issue_type}</strong>
                                    <div style="font-size: 12px; color: #475569;">"${i.reason}"</div>
                                </td>
                                <td><span class="status-badge ${i.status}">${i.status}</span></td>
                                <td>
                                    ${i.status === 'open' ? `
                                        <button class="btn-primary" style="padding: 4px 10px; font-size: 12px;" onclick="resolveAdminIssue(${i.id})">Mark Resolved</button>
                                    ` : 'Resolved'}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
}

async function resolveAdminIssue(issueId) {
    const notes = prompt("Enter resolution notes:");
    const res = await apiFetch(`/admin/issues/${issueId}/resolve`, {
        method: 'POST',
        body: JSON.stringify({ admin_notes: notes, resolution: 'resolved' })
    });
    if (res.ok) loadAdminIssues();
}

function renderAdminAnalytics(charts) {
    const container = document.getElementById('admin-tab-analytics');
    container.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 20px;">
            <div class="card">
                <h3><i class="fa-solid fa-chart-column"></i> Daily Order Volume & Revenue</h3>
                <div style="margin-top: 14px;">
                    ${charts.orders_per_day.map(o => `
                        <div style="margin-bottom: 12px;">
                            <div style="display: flex; justify-content: space-between; font-size: 12px; font-weight: 600;">
                                <span>${o.order_date}</span>
                                <span>${o.order_count} Orders (₹${o.revenue})</span>
                            </div>
                            <div style="background: #e2e8f0; height: 10px; border-radius: 5px; overflow: hidden; margin-top: 4px;">
                                <div style="background: var(--primary); height: 100%; width: ${Math.min(100, o.order_count * 20)}%;"></div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <div class="card">
                <h3><i class="fa-solid fa-chart-line"></i> Farmer Asking Price vs Prevailing Mandi Rate</h3>
                <div style="margin-top: 14px;">
                    ${charts.farmer_vs_mandi.map(m => `
                        <div style="background: #f8fafc; border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                            <strong>${m.crop_name}</strong>
                            <div style="display: flex; justify-content: space-between; font-size: 13px; margin-top: 4px;">
                                <span>Avg Farmer Realization: <strong style="color:var(--primary);">₹${Number(m.avg_farmer_price).toFixed(2)}/kg</strong></span>
                                <span>Mandi Benchmark: <strong>₹${Number(m.avg_mandi_price).toFixed(2)}/kg</strong></span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
}

// Admin Invites
function openAdminInviteModal() {
    document.getElementById('modal-admin-invite').classList.add('active');
}

function closeAdminInviteModal() {
    document.getElementById('modal-admin-invite').classList.remove('active');
}

async function handleAdminInviteSubmit(e) {
    e.preventDefault();
    const email = document.getElementById('inv-email').value.trim();
    const admin_level = document.getElementById('inv-level').value;

    const res = await apiFetch('/admin/invites', {
        method: 'POST',
        body: JSON.stringify({ email, admin_level })
    });

    if (res.ok) {
        document.getElementById('invite-code-output').innerHTML = `
            <div class="alert-notice alert-success">
                Invite Code Generated: <strong style="letter-spacing: 2px;">${res.data.invite_code}</strong>
                <br>Email invite dispatched to ${email}.
            </div>
        `;
    } else {
        alert(res.data.message);
    }
}

// ==================== COMMON UTILITIES ====================
async function fetchUnreadNotificationCount() {
    const res = await apiFetch('/utils/notifications');
    if (res.ok) {
        const unread = res.data.data.filter(n => !n.is_read).length;
        document.getElementById('notif-badge').innerText = unread;
    }
}

async function openNotificationsModal() {
    const res = await apiFetch('/utils/notifications');
    if (!res.ok) return;

    const notifs = res.data.data;
    const container = document.getElementById('notifications-list-container');

    if (notifs.length === 0) {
        container.innerHTML = `<div style="text-align:center; color:var(--text-muted); padding:20px;">No notifications yet.</div>`;
    } else {
        container.innerHTML = notifs.map(n => `
            <div style="background: ${n.is_read ? '#ffffff' : '#f0fdf4'}; border: 1px solid var(--border); border-radius: 8px; padding: 12px; margin-bottom: 10px;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <strong>${n.title}</strong>
                    <span style="font-size: 11px; color: var(--text-muted);">${n.created_at}</span>
                </div>
                <p style="font-size: 13px; color: #475569; margin: 6px 0;">${n.message}</p>
                ${!n.is_read ? `<button class="btn-secondary" style="padding: 2px 8px; font-size: 11px;" onclick="markNotificationRead(${n.id})">Mark as Read</button>` : ''}
            </div>
        `).join('');
    }

    document.getElementById('modal-notifications').classList.add('active');
}

function closeNotificationsModal() {
    document.getElementById('modal-notifications').classList.remove('active');
}

async function markNotificationRead(id) {
    await apiFetch(`/utils/notifications/${id}/read`, { method: 'POST' });
    openNotificationsModal();
    fetchUnreadNotificationCount();
}

function openFeedbackModal() {
    document.getElementById('modal-feedback').classList.add('active');
}

function closeFeedbackModal() {
    document.getElementById('modal-feedback').classList.remove('active');
}

async function handleFeedbackSubmit(e) {
    e.preventDefault();
    const payload = {
        category: document.getElementById('fb-category').value,
        subject: document.getElementById('fb-subject').value,
        message: document.getElementById('fb-message').value
    };

    const res = await apiFetch('/utils/feedback', {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        alert(res.data.message);
        closeFeedbackModal();
    } else {
        alert(res.data.message);
    }
}

function openForgotPasswordModal() {
    document.getElementById('modal-forgot-pwd').classList.add('active');
}

function closeForgotPasswordModal() {
    document.getElementById('modal-forgot-pwd').classList.remove('active');
}

async function sendForgotPwdOtp() {
    const phone = document.getElementById('fp-mobile').value.trim();
    if (!phone) {
        alert("Enter registered mobile number.");
        return;
    }
    const res = await apiFetch('/auth/send-otp', {
        method: 'POST',
        body: JSON.stringify({ phone })
    });
    if (res.ok) {
        alert(res.data.message);
        document.getElementById('fp-otp').value = res.data.otp_code || '123456';
    } else {
        alert(res.data.message);
    }
}

async function handleForgotPasswordSubmit(e) {
    e.preventDefault();
    const payload = {
        phone: document.getElementById('fp-mobile').value.trim(),
        otp_code: document.getElementById('fp-otp').value.trim(),
        new_password: document.getElementById('fp-new-pwd').value
    };

    const res = await apiFetch('/auth/forgot-password', {
        method: 'POST',
        body: JSON.stringify(payload)
    });

    if (res.ok) {
        alert(res.data.message);
        closeForgotPasswordModal();
    } else {
        alert(res.data.message);
    }
}
