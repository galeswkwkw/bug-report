import bcrypt
from app.database import SessionLocal
from app.models import User

def create_admin():
    db = SessionLocal()
    
    existing_admin = db.query(User).filter(User.email == "security@company.com").first()
    if existing_admin:
        print(f"⚠️ Admin already exists with ID: {existing_admin.id}")
        print(f"   Email: {existing_admin.email}")
        print(f"   Status: {existing_admin.status}")
        db.close()
        return
    
    password = "security123"
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    hashed_str = hashed.decode('utf-8')
    
    print(f"🔑 Password: {password}")
    print(f"🔒 Hash: {hashed_str}")
    
    admin = User(
        role_id=2, 
        researcher_type="Internal",
        full_name="security User",
        email="security@company.com",
        password_hash=hashed_str,
        status="Active"
    )
    
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    print("✅ Admin created successfully!")
    print(f"   ID: {admin.id}")
    print(f"   Email: security@company.com")
    print(f"   Password: security123")
    print(f"   Status: Active")
    db.close()

if __name__ == "__main__":
    create_admin()