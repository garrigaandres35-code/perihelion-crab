"""
Script to create initial admin user
Run this once to set up the first admin account
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, Profile

def create_admin():
    """Create default admin user"""
    app = create_app()
    
    with app.app_context():
        # Check if admin user exists
        admin = User.query.filter_by(email='admin@admin.com').first()
        if admin:
            print("Admin user already exists!")
            return
        
        # Get admin profile
        admin_profile = Profile.query.filter_by(name='admin').first()
        if not admin_profile:
            print("Error: Admin profile not found. Please run the app first to create profiles.")
            return
        
        # Create admin user
        admin = User(
            email='admin@admin.com',
            name='Administrador',
            profile_id=admin_profile.id
        )
        admin.set_password('admin123')
        
        db.session.add(admin)
        db.session.commit()
        
        print("=" * 50)
        print("Admin user created successfully!")
        print("=" * 50)
        print(f"Email: admin@admin.com")
        print(f"Password: admin123")
        print("=" * 50)
        print("Please change this password after first login!")
        print("=" * 50)

if __name__ == '__main__':
    create_admin()
