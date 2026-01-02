"""
Main Routes Blueprint
Handles main application routes
"""
from flask import Blueprint, render_template, redirect, url_for
from app.utils.database import init_default_data, get_all_venues
from app.models import Venue, Competition
from datetime import datetime, timedelta

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Home page"""
    # Initialize default data if needed
    init_default_data()
    
    # Get venues and competitions
    venues = get_all_venues()
    recent_competitions = Competition.query.order_by(Competition.created_at.desc()).limit(10).all()
    
    # Get today's date
    today = datetime.now().strftime('%d/%m/%Y')
    
    # Get statistics
    stats = {
        'total_venues': Venue.query.count(),
        'total_competitions': Competition.query.count(),
        'venues': venues,
        'recent_competitions': recent_competitions
    }
    
    return render_template('index.html', stats=stats, today=today)

@main_bp.route('/about')
def about():
    """About page"""
    return render_template('about.html')

@main_bp.route('/analysis')
def analysis():
    """Analysis page (placeholder)"""
    return render_template('analysis.html', message='Módulo de análisis en desarrollo')

@main_bp.route('/models')
def models():
    """Models page (placeholder)"""
    return render_template('models.html', message='Módulo de modelos predictivos en desarrollo')
