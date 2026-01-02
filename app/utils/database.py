"""
Database Utilities
Helper functions for database operations
"""
from app import db
from app.models import Venue, Configuration, Competition
from datetime import datetime

def init_default_data():
    """
    Initialize database with default venue data
    """
    # Check if data already exists
    if Venue.query.first():
        return
    
    # Create default venues (Recintos)
    venues = [
        Venue(name='Hipódromo Chile', abbreviation='HCH', country='Chile', description='Principal recinto hípico de Chile'),
        Venue(name='Club Hípico de Santiago', abbreviation='CHS', country='Chile', description='Tradicional hipódromo de Santiago'),
        Venue(name='Valparaíso Sporting Club', abbreviation='VSC', country='Chile', description='Recinto deportivo de Valparaíso'),
    ]
    
    for venue in venues:
        db.session.add(venue)
    
    # Create default configurations
    configs = [
        Configuration(key='scraping_enabled', value='true', description='Enable/disable scraping'),
        Configuration(key='scraping_interval', value='3600', description='Scraping interval in seconds'),
        Configuration(key='app_version', value='2.0.0', description='Application version'),
    ]
    
    for config in configs:
        db.session.add(config)
    
    db.session.commit()

def get_config_value(key, default=None):
    """
    Get configuration value by key
    """
    config = Configuration.query.filter_by(key=key).first()
    return config.value if config else default

def set_config_value(key, value, description=None):
    """
    Set configuration value
    """
    config = Configuration.query.filter_by(key=key).first()
    
    if config:
        config.value = value
        if description:
            config.description = description
    else:
        config = Configuration(key=key, value=value, description=description)
        db.session.add(config)
    
    db.session.commit()
    return config

def get_all_venues():
    """
    Get all active venues
    """
    return Venue.query.filter_by(active=True).all()

def get_venue_by_abbreviation(abbreviation):
    """
    Get venue by abbreviation
    """
    return Venue.query.filter_by(abbreviation=abbreviation.upper()).first()
