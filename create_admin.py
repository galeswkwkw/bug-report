import bcrypt
from app.database import SessionLocal
from app.models import User

def create_superadmin():
    db = SessionLocal()
    
    # Cek apakah Super Admin sudah ada
    existing_admin = db.query(User).filter(User.email == "superadmin@company.com").first()
    if existing_admin:
        print(f"⚠️ Super Admin already exists with ID: {existing_admin.id}")
        print(f"   Email: {existing_admin.email}")
        print(f"   Status: {existing_admin.status}")
        db.close()
        return
    
    # Hash password: superadmin123
    password = "superadmin123"
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    hashed_str = hashed.decode('utf-8')
    
    print(f"🔑 Password: {password}")
    print(f"🔒 Hash: {hashed_str}")
    
    # Buat Super Admin dengan role_id = 4
    admin = User(
        role_id=4,  # Super Admin
        researcher_type="Internal",
        full_name="Super Admin",
        email="superadmin@company.com",
        password_hash=hashed_str,
        status="Active"
    )
    
    db.add(admin)
    db.commit()
    db.refresh(admin)
    
    print("✅ Super Admin created successfully!")
    print(f"   ID: {admin.id}")
    print(f"   Email: superadmin@company.com")
    print(f"   Password: superadmin123")
    print(f"   Role: Super Admin (role_id: 4)")
    print(f"   Status: Active")
    db.close()

if __name__ == "__main__":
    create_superadmin()