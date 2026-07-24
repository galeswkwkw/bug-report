# create_users.py
import bcrypt
from app.database import SessionLocal
from app.models import User

def create_user(email, password, full_name, role_id, researcher_type=None):
    """
    Create a new user with specified role
    
    Role IDs:
    - 1: Admin
    - 2: Security Team
    - 3: Bug Hunter
    - 4: Super Admin
    """
    db = SessionLocal()
    
    try:
        # Cek apakah user sudah ada
        existing_user = db.query(User).filter(User.email == email).first()
        if existing_user:
            print(f"⚠️ User with email {email} already exists (ID: {existing_user.id})")
            db.close()
            return
        
        # Hash password
        password_bytes = password.encode('utf-8')[:72]
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password_bytes, salt)
        hashed_str = hashed.decode('utf-8')
        
        # Buat user
        user = User(
            role_id=role_id,
            researcher_type=researcher_type,
            full_name=full_name,
            email=email,
            password_hash=hashed_str,
            status="Active"
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Role name
        role_names = {
            1: "Admin",
            2: "Security Team",
            3: "Bug Hunter",
            4: "Super Admin"
        }
        
        print(f"✅ User created successfully!")
        print(f"   ID: {user.id}")
        print(f"   Email: {email}")
        print(f"   Password: {password}")
        print(f"   Name: {full_name}")
        print(f"   Role: {role_names.get(role_id, 'Unknown')} (role_id: {role_id})")
        if researcher_type:
            print(f"   Researcher Type: {researcher_type}")
        print(f"   Status: Active")
        print("-" * 50)
        
    except Exception as e:
        print(f"❌ Failed to create user: {str(e)}")
        db.rollback()
    finally:
        db.close()


def create_bug_hunter():
    """Create Bug Hunter (role_id: 3)"""
    create_user(
        email="robert@company.com",
        password="password123",
        full_name="Robert Bug Hunter",
        role_id=3,
        researcher_type="External"
    )


def create_security_team():
    """Create Security Team (role_id: 2)"""
    create_user(
        email="security@company.com",
        password="password123",
        full_name="Security Team",
        role_id=2
    )


if __name__ == "__main__":
    print("=" * 60)
    print("🚀 CREATING USERS FOR BUG BOUNTY SYSTEM")
    print("=" * 60)
    print()
    
    # Buat Bug Hunter
    create_bug_hunter()
    
    # Buat Security Team
    create_security_team()
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    print("Bug Hunter:   robert@company.com / password123")
    print("Security:     security@company.com / password123")
    print("=" * 60)