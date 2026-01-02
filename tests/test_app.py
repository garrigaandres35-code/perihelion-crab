"""
Unit Tests for Sports Prediction Platform
"""
import pytest
from app import create_app, db
from app.models import Venue, Competition, User, Profile

@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

def test_app_creation(app):
    """Test application creation"""
    assert app is not None
    assert app.config['TESTING'] is True

def test_home_page(client):
    """Test home page loads"""
    response = client.get('/')
    assert response.status_code == 200

def test_login_page(client):
    """Test login page loads"""
    response = client.get('/auth/login')
    assert response.status_code == 200

def test_api_venues(client):
    """Test API venues endpoint"""
    response = client.get('/api/venues')
    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)

def test_api_stats(client):
    """Test API stats endpoint"""
    response = client.get('/api/stats')
    assert response.status_code == 200
    data = response.get_json()
    assert 'total_events' in data or 'total_venues' in data

def test_database_models(app):
    """Test database models creation"""
    with app.app_context():
        # Create venue
        venue = Venue(name='Test Venue', abbreviation='TST', country='Test Country')
        db.session.add(venue)
        db.session.commit()
        
        # Verify venue was created
        assert Venue.query.filter_by(abbreviation='TST').first() is not None
        
        # Create competition
        competition = Competition(name='Test Competition', venue_id=venue.id)
        db.session.add(competition)
        db.session.commit()
        
        # Verify competition was created
        assert Competition.query.filter_by(name='Test Competition').first() is not None

def test_user_model(app):
    """Test user model creation and password hashing"""
    with app.app_context():
        # Create profile first
        profile = Profile(name='test_profile', description='Test profile')
        db.session.add(profile)
        db.session.commit()
        
        # Create user
        user = User(
            email='test@test.com',
            name='Test User',
            profile_id=profile.id
        )
        user.set_password('testpass123')
        db.session.add(user)
        db.session.commit()
        
        # Verify user
        saved_user = User.query.filter_by(email='test@test.com').first()
        assert saved_user is not None
        assert saved_user.check_password('testpass123') is True
        assert saved_user.check_password('wrongpass') is False
