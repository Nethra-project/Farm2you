import json
from main import app

def run_tests():
    print("=== Testing Farm2you In-Process via Flask Test Client ===")
    client = app.test_client()

    # 1. API Status
    r = client.get('/api-status')
    assert r.status_code == 200, f"Status failed: {r.data}"
    res = r.get_json()
    print("✓ API Status OK:", res['app'])

    # 2. Test OTP Flow
    r = client.post('/auth/send-otp', json={"phone": "9988776655"})
    assert r.status_code == 200, f"Send OTP failed: {r.data}"
    otp_code = r.get_json().get('otp_code', '123456')
    print("✓ Send OTP OK, code:", otp_code)

    r = client.post('/auth/verify-otp', json={"phone": "9988776655", "otp_code": otp_code})
    assert r.status_code == 200, f"Verify OTP failed: {r.data}"
    print("✓ Verify OTP OK")

    # 3. Test Farmer Registration (should be pending approval)
    r = client.post('/auth/register', json={
        "phone": "9988776655",
        "password": "FarmPassword123!",
        "role": "producer",
        "subtype": "farmer",
        "full_name": "Balram Singh",
        "village": "Shampur",
        "district": "Pune",
        "state": "Maharashtra",
        "pincode": "412206",
        "crops_grown": "Tomato, Potato",
        "upi_id": "balram@upi"
    })
    assert r.status_code == 201 or r.status_code == 409
    
    # 4. Test Super Admin Login & Verification Queue (Step 4)
    r = client.post('/admin/auth/login', json={
        "email": "admin@platform.com",
        "password": "SuperAdminPass123!"
    })
    assert r.status_code == 200, f"Admin login failed: {r.data}"
    admin_token = r.get_json()['token']
    print("✓ Admin Login OK")

    # Check Verification Queue
    r = client.get('/admin/verifications', headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    queue = r.get_json()['data']
    print(f"✓ Verification Queue retrieved ({len(queue)} pending applicants)")

    # Approve Farmer Balram Singh if pending
    balram = next((u for u in queue if u['phone'] == '9988776655'), None)
    if balram:
        r = client.post(f'/admin/verifications/{balram["id"]}/action', headers={"Authorization": f"Bearer {admin_token}"}, json={
            "action": "approve"
        })
        assert r.status_code == 200
        print("✓ Balram approved by Admin (Status -> verified)")

    # 5. Login Balram and Add Listing
    r = client.post('/auth/login', json={"identifier": "9988776655", "password": "FarmPassword123!"})
    assert r.status_code == 200
    farmer_token = r.get_json()['token']
    assert r.get_json()['user']['approval_status'] == 'verified'

    r = client.post('/farmer/listings', headers={"Authorization": f"Bearer {farmer_token}"}, json={
        "crop_name": "Tomato",
        "variety": "Hybrid Red",
        "category": "vegetables",
        "quantity": 500,
        "unit": "kg",
        "quality_grade": "A",
        "asking_price_per_kg": 24.0,
        "mandi_price_hint": 24.5,
        "min_order_qty": 10,
        "max_order_qty": 300,
        "pickup_location": "Shampur Farm Gate",
        "description": "Crisp red tomatoes"
    })
    assert r.status_code == 201, f"Farmer add listing failed: {r.data}"
    new_listing_id = r.get_json()['listing_id']
    print(f"✓ Verified Farmer added listing #{new_listing_id} successfully!")

    # 6. Test Consumer Login & Order Placement (Step 7)
    r = client.post('/auth/login', json={"identifier": "9876543230", "password": "Pass1234!"})
    assert r.status_code == 200
    consumer_token = r.get_json()['token']

    # Place order for 25 kg
    r = client.post('/buyer/orders', headers={"Authorization": f"Bearer {consumer_token}"}, json={
        "listing_id": new_listing_id,
        "quantity": 25,
        "delivery_address": "Flat 402, Green Meadows, Pune",
        "payment_method": "COD"
    })
    assert r.status_code == 201, f"Place order failed: {r.data}"
    order_data = r.get_json()['data']
    order_id = order_data['order_id']
    print(f"✓ Consumer placed Order #{order_id} (Status: {order_data['status']}, Total: ₹{order_data['total_amount']})")

    # 7. Check Farmer Order View: Phone hidden on new orders (Step 8)
    r = client.get('/farmer/orders', headers={"Authorization": f"Bearer {farmer_token}"})
    assert r.status_code == 200
    order_in_farmer_view = next((o for o in r.get_json()['data'] if o['id'] == order_id), None)
    assert order_in_farmer_view is not None
    assert "Hidden" in order_in_farmer_view['buyer_phone'], f"Buyer phone should be hidden! Got: {order_in_farmer_view['buyer_phone']}"
    print("✓ Buyer phone is properly hidden on new order!")

    # 8. Farmer Accepts Order -> Quantity left drops automatically & Pickup code generated (Step 8)
    r = client.post(f'/farmer/orders/{order_id}/accept', headers={"Authorization": f"Bearer {farmer_token}"})
    assert r.status_code == 200
    pickup_code = r.get_json()['pickup_code']
    print(f"✓ Farmer accepted order #{order_id}, pickup code generated: {pickup_code}")

    # Check that quantity left dropped from 500 to 475
    r = client.get('/farmer/listings', headers={"Authorization": f"Bearer {farmer_token}"})
    l_updated = next(l for l in r.get_json()['data'] if l['id'] == new_listing_id)
    assert l_updated['quantity_left'] == 475.0, f"Expected 475 left, got {l_updated['quantity_left']}"
    print("✓ Quantity left in listing auto-deducted to 475 kg!")

    # Check that buyer phone is now revealed after acceptance!
    r = client.get('/farmer/orders', headers={"Authorization": f"Bearer {farmer_token}"})
    order_in_farmer_view = next(o for o in r.get_json()['data'] if o['id'] == order_id)
    assert "Hidden" not in order_in_farmer_view['buyer_phone'], "Buyer phone should now be revealed"
    print(f"✓ Buyer phone is now revealed: {order_in_farmer_view['buyer_phone']}")

    # 9. Register a fresh verified Driver to accept this delivery job
    import random
    driver_phone = f"99887{random.randint(10000, 99999)}"
    client.post('/auth/send-otp', json={"phone": driver_phone})
    client.post('/auth/verify-otp', json={"phone": driver_phone, "otp_code": "123456"})
    r = client.post('/auth/register', json={
        "phone": driver_phone,
        "password": "DriverPass123!",
        "role": "driver",
        "subtype": "driver",
        "full_name": "Raju Driver",
        "city": "Pune",
        "district": "Pune",
        "pincodes_served": "411038, 412206",
        "vehicle_type": "tempo",
        "vehicle_number": f"MH-12-XX-{random.randint(1000, 9999)}",
        "load_capacity_kg": 1500,
        "licence_photo_url": "https://example.com/licence.jpg"
    })
    new_driver_id = r.get_json()['user']['id']

    # Approve Raju Driver in Admin Verification Queue
    r = client.post(f'/admin/verifications/{new_driver_id}/action', headers={"Authorization": f"Bearer {admin_token}"}, json={
        "action": "approve"
    })
    assert r.status_code == 200
    print("✓ New Driver Raju registered & approved by admin")

    # Login Raju Driver
    r = client.post('/auth/login', json={"identifier": driver_phone, "password": "DriverPass123!"})
    assert r.status_code == 200
    raju_token = r.get_json()['token']

    # 10. Driver Workflow (Step 5)
    r = client.get('/driver/jobs/available', headers={"Authorization": f"Bearer {raju_token}"})
    assert r.status_code == 200
    jobs = r.get_json()['data']
    job_for_order = next((j for j in jobs if j['order_id'] == order_id), None)
    assert job_for_order is not None, "Delivery job should be available"
    job_id = job_for_order['id']
    print(f"✓ Driver sees Delivery Job #{job_id} (Pay: ₹{job_for_order['driver_pay']})")

    # Driver accepts job
    r = client.post(f'/driver/jobs/{job_id}/accept', headers={"Authorization": f"Bearer {raju_token}"})
    assert r.status_code == 200, f"Accept job failed: {r.data}"
    print(f"✓ Driver accepted Job #{job_id}")

    # Driver Farm Pickup Verification (with pickup code)
    r = client.post(f'/driver/jobs/{job_id}/verify-pickup', headers={"Authorization": f"Bearer {raju_token}"}, json={
        "pickup_code": pickup_code
    })
    assert r.status_code == 200, f"Verify pickup failed: {r.data}"
    print(f"✓ Driver verified Farm Pickup with code {pickup_code} -> status 'picked_up'")

    # Driver Buyer Drop Delivery Verification (with delivery code)
    delivery_code = order_data['delivery_code']
    r = client.post(f'/driver/jobs/{job_id}/verify-delivery', headers={"Authorization": f"Bearer {raju_token}"}, json={
        "delivery_code": delivery_code,
        "cash_collected": order_data['total_amount']
    })
    assert r.status_code == 200, f"Verify delivery failed: {r.data}"
    print(f"✓ Driver verified Buyer Drop with code {delivery_code} -> status 'delivered'")

    # 11. Consumer Rates Farmer (Step 10)
    r = client.post(f'/buyer/orders/{order_id}/rate', headers={"Authorization": f"Bearer {consumer_token}"}, json={
        "rating": 5,
        "review": "Extremely fresh tomatoes, delicious!"
    })
    assert r.status_code == 200
    print("✓ Consumer rated Farmer 5 stars!")

    # 12. Check Admin Dashboard Analytics & Stuck Orders
    r = client.get('/admin/dashboard', headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    metrics = r.get_json()['data']['metrics']
    print(f"✓ Admin Dashboard Metrics: Total Users: {metrics['users_by_type']['total']}, Active Listings: {metrics['active_listings']}, Delivered Orders: {metrics['orders_delivered']}")

    print("\n🎉 ALL 12 INTEGRATION TEST SCENARIOS PASSED WITH 100% SUCCESS!")

if __name__ == '__main__':
    run_tests()
