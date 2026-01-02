"""
API Routes Blueprint
RESTful API endpoints
"""
from flask import Blueprint, jsonify, request
from app.models import Venue, Competition
from app import db

api_bp = Blueprint('api', __name__)

@api_bp.route('/venues')
def get_venues():
    """Get all venues"""
    venues = Venue.query.filter_by(active=True).all()
    
    return jsonify([{
        'id': v.id,
        'name': v.name,
        'abbreviation': v.abbreviation,
        'country': v.country,
        'description': v.description
    } for v in venues])

@api_bp.route('/venues/<int:venue_id>')
def get_venue(venue_id):
    """Get venue by ID"""
    venue = Venue.query.get_or_404(venue_id)
    
    return jsonify({
        'id': venue.id,
        'name': venue.name,
        'abbreviation': venue.abbreviation,
        'country': venue.country,
        'description': venue.description,
        'competitions': [{
            'id': c.id,
            'name': c.name,
            'event_date': c.event_date.isoformat() if c.event_date else None
        } for c in venue.competitions]
    })

@api_bp.route('/competitions')
def get_competitions():
    """Get competitions with optional filters"""
    venue_id = request.args.get('venue_id')
    date_str = request.args.get('date')
    
    query = Competition.query.filter_by(active=True)
    
    if venue_id:
        query = query.filter_by(venue_id=int(venue_id))
    
    if date_str:
        from datetime import datetime
        try:
            event_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter_by(event_date=event_date)
        except ValueError:
            pass
    
    competitions = query.order_by(Competition.created_at.desc()).limit(100).all()
    
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'venue': c.venue.abbreviation if c.venue else None,
        'venue_name': c.venue.name if c.venue else None,
        'event_date': c.event_date.isoformat() if c.event_date else None
    } for c in competitions])

@api_bp.route('/competitions/<int:comp_id>')
def get_competition(comp_id):
    """Get competition by ID"""
    competition = Competition.query.get_or_404(comp_id)
    
    return jsonify({
        'id': competition.id,
        'name': competition.name,
        'venue': {
            'id': competition.venue.id,
            'name': competition.venue.name,
            'abbreviation': competition.venue.abbreviation
        } if competition.venue else None,
        'event_date': competition.event_date.isoformat() if competition.event_date else None
    })

@api_bp.route('/stats')
def get_stats():
    """Get general statistics"""
    return jsonify({
        'total_venues': Venue.query.count(),
        'total_competitions': Competition.query.count(),
        'active_venues': Venue.query.filter_by(active=True).count(),
        'active_competitions': Competition.query.filter_by(active=True).count()
    })
