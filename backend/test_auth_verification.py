import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import SessionLocal
from app.models.user import User, UserRole
from app.core import security

def verify_auth():
    print("Testing Auth and RBAC End-to-End...")
    client = TestClient(app)
    
    # Pre-setup users
    db = SessionLocal()
    # admin123 is seeded by default in init_db.py, but we'll create test ones just to be sure
    test_admin_pw = "admin123"
    test_operator_pw = "oper123"
    
    admin = db.query(User).filter(User.username == "test_admin").first()
    if not admin:
        admin = User(username="test_admin", hashed_password=security.get_password_hash(test_admin_pw), role_name=UserRole.ADMIN)
        db.add(admin)
    
    oper = db.query(User).filter(User.username == "test_oper").first()
    if not oper:
        oper = User(username="test_oper", hashed_password=security.get_password_hash(test_operator_pw), role_name=UserRole.OPERATOR)
        db.add(oper)
        
    db.commit()
    db.close()
    
    # 1. Login Authentication
    print("Testing Admin Login...")
    resp = client.post("/api/v1/auth/login", data={"username": "test_admin", "password": test_admin_pw})
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    admin_token = resp.json()["access_token"]
    print(f"Admin Login Success. Token generated.")
    
    print("Testing Operator Login...")
    resp2 = client.post("/api/v1/auth/login", data={"username": "test_oper", "password": test_operator_pw})
    oper_token = resp2.json()["access_token"]
    print(f"Operator Login Success. Token generated.")
    
    print("Testing Wrong Password...")
    resp_wrong = client.post("/api/v1/auth/login", data={"username": "test_admin", "password": "wrongpassword"})
    print(f"Wrong Password (Expected 401/400): {resp_wrong.status_code}")
    
    # 2. RBAC Testing
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    oper_headers = {"Authorization": f"Bearer {oper_token}"}
    
    print("Testing Protected Route access...")
    # example route: /api/v1/users/me -> should work for both
    resp_me = client.get("/api/v1/users/me", headers=oper_headers)
    print(f"Operator accessed /users/me: {resp_me.status_code == 200}")

    # RBAC specific routes
    # For example, create user should be admin only
    # First, test admin
    print("Testing Admin RBAC capabilities...")
    resp_admin_action = client.post("/api/v1/users/", headers=admin_headers, json={"username": "new_user", "password": "abc", "role": "OPERATOR"})
    print(f"Admin create user: {resp_admin_action.status_code}")

    print("Testing Operator RBAC prevention...")
    resp_oper_action = client.post("/api/v1/users/", headers=oper_headers, json={"username": "new_user2", "password": "abc", "role": "OPERATOR"})
    print(f"Operator create user (Expected 403): {resp_oper_action.status_code}")
    
    print("Testing Authentication bypass prevention (missing token)...")
    resp_no_auth = client.get("/api/v1/users/me")
    print(f"Missing token access (Expected 401): {resp_no_auth.status_code}")
    
    print("Testing Invalid token...")
    resp_invalid = client.get("/api/v1/users/me", headers={"Authorization": "Bearer badtoken"})
    print(f"Invalid token access (Expected 401): {resp_invalid.status_code}")

    print("ALL AUTHENTICATION / RBAC TESTS COMPLETED.")

if __name__ == "__main__":
    verify_auth()
