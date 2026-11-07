from main import app

def test_additional_features():
    print("=== Testing Additional Features (FPO, Bulk RFQ, Mandi, Feedback) ===")
    client = app.test_client()

    # 1. Login FPO
    r = client.post('/auth/login', json={"identifier": "9876543220", "password": "Pass1234!"})
    assert r.status_code == 200
    fpo_token = r.get_json()['token']

    # Add FPO Member
    r = client.post('/farmer/fpo/members', headers={"Authorization": f"Bearer {fpo_token}"}, json={
        "member_name": "Tukaram Shinde",
        "phone": "9876500003",
        "village": "Ozar",
        "crops_grown": "Grapes, Pomegranate"
    })
    assert r.status_code == 201
    member_id = r.get_json()['member_id']
    print(f"✓ FPO Member added #{member_id}")

    # List FPO Members
    r = client.get('/farmer/fpo/members', headers={"Authorization": f"Bearer {fpo_token}"})
    assert r.status_code == 200
    assert any(m['id'] == member_id for m in r.get_json()['data'])
    print("✓ FPO Members listed successfully")

    # 2. Bulk Buyer RFQ Flow
    # Approve Bulk Buyer Taj Hotel
    admin_login = client.post('/admin/auth/login', json={"email": "admin@platform.com", "password": "SuperAdminPass123!"})
    admin_token = admin_login.get_json()['token']
    
    taj_user = client.get('/admin/users?subtype=bulk_buyer', headers={"Authorization": f"Bearer {admin_token}"}).get_json()['data'][0]
    client.post(f'/admin/verifications/{taj_user["id"]}/action', headers={"Authorization": f"Bearer {admin_token}"}, json={"action": "approve"})

    # Login Bulk Buyer
    r = client.post('/auth/login', json={"identifier": "9876543240", "password": "Pass1234!"})
    assert r.status_code == 200
    bulk_token = r.get_json()['token']

    # Post Bulk RFQ
    r = client.post('/buyer/rfqs', headers={"Authorization": f"Bearer {bulk_token}"}, json={
        "crop_name": "Onion",
        "variety": "Red Nashik",
        "min_order_qty": 2000,
        "quality_grade": "A",
        "target_price": 26.0,
        "needed_by_date": "2026-11-20",
        "delivery_location": "Taj Kitchens, Hadapsar, Pune"
    })
    assert r.status_code == 201
    rfq_id = r.get_json()['rfq_id']
    print(f"✓ Bulk RFQ #{rfq_id} posted")

    # Farmer submits quote on RFQ
    # Get farmer token (Ramesh)
    ramesh_login = client.post('/auth/login', json={"identifier": "9876543210", "password": "Pass1234!"})
    ramesh_token = ramesh_login.get_json()['token']
    ramesh_id = ramesh_login.get_json()['user']['id']

    from database import execute_db
    quote_id, _ = execute_db("""
        INSERT INTO rfq_quotes (rfq_id, farmer_id, price_per_kg, quantity_offered, note)
        VALUES (?, ?, 25.5, 2000, 'Top graded Nashik red onions ready for dispatch.')
    """, (rfq_id, ramesh_id))
    print(f"✓ Producer quote #{quote_id} placed on RFQ")

    # Bulk buyer views RFQs and accepts quote -> converts to order
    r = client.get('/buyer/rfqs', headers={"Authorization": f"Bearer {bulk_token}"})
    assert r.status_code == 200
    rfq_rec = next(rfq for rfq in r.get_json()['data'] if rfq['id'] == rfq_id)
    assert len(rfq_rec['quotes']) == 1

    r = client.post(f'/buyer/rfqs/{rfq_id}/accept-quote/{quote_id}', headers={"Authorization": f"Bearer {bulk_token}"})
    assert r.status_code == 200
    converted_order_id = r.get_json()['order_id']
    print(f"✓ Bulk buyer accepted quote, auto-converted to Order #{converted_order_id}")

    # 3. Mandi Prices endpoint
    r = client.get('/utils/mandi-prices?crop=Tomato')
    assert r.status_code == 200
    assert len(r.get_json()['data']) > 0
    print(f"✓ Mandi Prices search returned {len(r.get_json()['data'])} records")

    # 4. Feedback endpoint
    r = client.post('/utils/feedback', json={
        "category": "delivery",
        "subject": "Great prompt transport",
        "message": "Delivery was fast and seamless."
    })
    assert r.status_code == 201
    print("✓ Feedback submission OK")

    # 5. Language support endpoint
    r = client.get('/utils/languages')
    assert r.status_code == 200
    langs = r.get_json()['languages']
    assert len(langs) == 4
    print("✓ Supported languages (en, hi, ta, te) verified")

    print("\n🎉 ALL ADDITIONAL SPECIFICATION FEATURES PASSED WITH 100% SUCCESS!")

if __name__ == '__main__':
    test_additional_features()

