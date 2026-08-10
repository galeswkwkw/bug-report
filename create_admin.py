import bcrypt
from app.database import SessionLocal
from app.models import User

def create_admin():
    """
    Create Admin user with secure credentials
    """
    db = SessionLocal()
    
    email = "daeaje@gmail.com"
    password = "slwX$PoC"
    full_name = "Admin"
    role_id = 1  # Admin
    
    try:
        # Cek apakah admin sudah ada
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"⚠️ Admin already exists!")
            print(f"   ID: {existing_user.id}")
            print(f"   Email: {existing_user.email}")
            print(f"   Status: {existing_user.status}")
            db.close()
            return
        
        # Hash password
        password_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        hashed_str = hashed.decode('utf-8')
        
        # Buat Admin
        admin = User(
            role_id=role_id,
            researcher_type="Internal",
            full_name=full_name,
            email=email,
            password_hash=hashed_str,
            status="Active"
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("=" * 60)
        print("✅ ADMIN CREATED SUCCESSFULLY!")
        print("=" * 60)
        print(f"   ID:          {admin.id}")
        print(f"   Email:       {email}")
        print(f"   Password:    {password}")
        print(f"   Name:        {full_name}")
        print(f"   Role:        Admin (role_id: {role_id})")
        print(f"   Status:      Active")
        print("=" * 60)
        print()
        print("🔑 LOGIN CREDENTIALS:")
        print(f"   Email:    {email}")
        print(f"   Password: {password}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Failed to create admin: {str(e)}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()