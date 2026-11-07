import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from database import init_db
from auth_routes import auth_bp
from farmer_portal_routes import farmer_bp
from buyer_portal_routes import buyer_bp
from driver_portal_routes import driver_bp
from admin_portal_routes import admin_bp
from utils_routes import utils_bp

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = Flask(__name__, static_folder=BASE_DIR, static_url_path='')
CORS(app)

app.config["JWT_SECRET_KEY"] = "farm2you-super-secure-production-jwt-token-key-2026"
jwt = JWTManager(app)

# Register Blueprints for all 4 Interfaces and Common modules
app.register_blueprint(auth_bp)
app.register_blueprint(farmer_bp)
app.register_blueprint(buyer_bp)
app.register_blueprint(driver_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(utils_bp)

# Auto-initialize database schema and seeds on startup
with app.app_context():
    init_db()

@app.route('/')
def serve_index():
    return send_from_directory(BASE_DIR, 'index.html')

@app.route('/api-status', methods=['GET'])
def api_status():
    return jsonify({
        "status": "success",
        "app": "Farm2you Direct Agricultural Marketplace",
        "version": "2.0.0",
        "supported_interfaces": [
            "Interface 1: Farmers & FPOs",
            "Interface 2: Consumer & Bulk Buyer",
            "Interface 3: Pickup and Delivery",
            "Interface 4: Administration"
        ],
        "account_statuses": ["pending", "verified", "rejected", "blocked"],
        "languages": ["English", "Hindi", "Tamil", "Telugu"]
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
