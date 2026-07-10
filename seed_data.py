import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import SessionLocal
from app.models import Role, DocumentType, PointRule

def seed_data():
    db = SessionLocal()
    
    print("🌱 Seeding data...")
    
    roles = [
        {"name": "Admin"},
        {"name": "Researcher"},
        {"name": "Reviewer"}
    ]
    
    for role_data in roles:
        existing = db.query(Role).filter(Role.name == role_data["name"]).first()
        if not existing:
            role = Role(name=role_data["name"])
            db.add(role)
            print(f"  ✅ Added role: {role_data['name']}")
        else:
            print(f"  ⏭️  Role already exists: {role_data['name']}")
    
    doc_types = [
        {"name": "KTP", "required": True},
        {"name": "NDA", "required": True},
        {"name": "CV", "required": False},
        {"name": "PORTFOLIO", "required": False}
    ]
    
    for doc_data in doc_types:
        existing = db.query(DocumentType).filter(DocumentType.name == doc_data["name"]).first()
        if not existing:
            doc = DocumentType(name=doc_data["name"], required=doc_data["required"])
            db.add(doc)
            print(f"  ✅ Added document type: {doc_data['name']}")
        else:
            print(f"  ⏭️  Document type already exists: {doc_data['name']}")
    
    point_rules = [
        {"severity": "Critical", "point": 100},
        {"severity": "High", "point": 70},
        {"severity": "Medium", "point": 50},
        {"severity": "Low", "point": 20},
        {"severity": "Informational", "point": 10}
    ]
    
    for rule_data in point_rules:
        existing = db.query(PointRule).filter(PointRule.severity == rule_data["severity"]).first()
        if not existing:
            rule = PointRule(severity=rule_data["severity"], point=rule_data["point"])
            db.add(rule)
            print(f"  ✅ Added point rule: {rule_data['severity']} = {rule_data['point']} points")
        else:
            print(f"  ⏭️  Point rule already exists: {rule_data['severity']}")
    
    db.commit()
    print("✅ Seed data inserted successfully!")
    db.close()

if __name__ == "__main__":
    seed_data()
