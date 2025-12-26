"""
Admin Routes Blueprint
Handles administration routes including users, venues, and competitions
"""
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, Response
from flask_login import login_required, current_user
from functools import wraps
from app.models import Configuration, ScrapingLog, User, Profile, Venue, Competition, RaceMeeting, Race, RacePerformance
from app.utils.database import get_config_value, set_config_value, get_all_venues
from app import db
from datetime import datetime
import io
import csv

admin_bp = Blueprint('admin', __name__)


def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Por favor inicia sesión', 'warning')
            return redirect(url_for('auth.login'))
        if not current_user.is_admin:
            flash('Acceso denegado. Se requiere rol de administrador.', 'error')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================
# Dashboard
# ============================================

@admin_bp.route('/')
@login_required
def dashboard():
    """Admin dashboard"""
    configs = Configuration.query.all()
    recent_logs = ScrapingLog.query.order_by(ScrapingLog.started_at.desc()).limit(20).all()
    
    # Stats
    stats = {
        'total_users': User.query.count(),
        'total_venues': Venue.query.count(),
        'total_competitions': Competition.query.count(),
    }
    
    return render_template('admin/dashboard.html', configs=configs, logs=recent_logs, stats=stats)


# ============================================
# Users Management
# ============================================

@admin_bp.route('/users')
@admin_required
def users():
    """Users management page"""
    users = User.query.all()
    profiles = Profile.query.all()
    return render_template('admin/users.html', users=users, profiles=profiles)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@admin_required
def toggle_user(user_id):
    """Toggle user active status"""
    user = User.query.get_or_404(user_id)
    
    # Prevent deactivating yourself
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'No puedes desactivarte a ti mismo'}), 400
    
    user.active = not user.active
    db.session.commit()
    
    status = 'activado' if user.active else 'desactivado'
    return jsonify({'success': True, 'message': f'Usuario {status}', 'active': user.active})


@admin_bp.route('/users/<int:user_id>/update', methods=['POST'])
@admin_required
def update_user(user_id):
    """Update user profile"""
    user = User.query.get_or_404(user_id)
    
    profile_id = request.form.get('profile_id')
    if profile_id:
        user.profile_id = int(profile_id)
        db.session.commit()
        flash(f'Perfil de {user.name} actualizado', 'success')
    
    return redirect(url_for('admin.users'))


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    """Delete user"""
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        return jsonify({'success': False, 'message': 'No puedes eliminarte a ti mismo'}), 400
    
    db.session.delete(user)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Usuario eliminado'})


@admin_bp.route('/users/<int:user_id>/update-profile', methods=['POST'])
@admin_required
def update_user_profile(user_id):
    """Update user name and email"""
    user = User.query.get_or_404(user_id)
    
    try:
        data = request.json
        field = data.get('field')
        value = data.get('value', '').strip()
        
        if not value:
            return jsonify({'success': False, 'message': 'El valor no puede estar vacío'}), 400
        
        if field == 'name':
            user.name = value
        elif field == 'email':
            # Check if email already exists for another user
            existing = User.query.filter(User.email == value, User.id != user_id).first()
            if existing:
                return jsonify({'success': False, 'message': 'Este email ya está en uso'}), 400
            user.email = value
        else:
            return jsonify({'success': False, 'message': 'Campo no válido'}), 400
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Usuario actualizado', 'value': value})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/users/<int:user_id>/change-password', methods=['POST'])
@admin_required
def change_user_password(user_id):
    """Change user password"""
    user = User.query.get_or_404(user_id)
    
    try:
        data = request.json
        new_password = data.get('password', '').strip()
        
        if not new_password:
            return jsonify({'success': False, 'message': 'La contraseña no puede estar vacía'}), 400
        
        if len(new_password) < 6:
            return jsonify({'success': False, 'message': 'La contraseña debe tener al menos 6 caracteres'}), 400
        
        from werkzeug.security import generate_password_hash
        user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        
        return jsonify({'success': True, 'message': f'Contraseña de {user.name} actualizada correctamente'})
    
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500



# ============================================
# Venues Management (Recintos)
# ============================================

@admin_bp.route('/venues')
@login_required
def venues():
    """Venues management page"""
    venues = Venue.query.all()
    return render_template('admin/venues.html', venues=venues)


@admin_bp.route('/venues/create', methods=['POST'])
@admin_required
def create_venue():
    """Create new venue"""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    abbreviation = request.form.get('abbreviation', '').strip().upper()
    country = request.form.get('country', '').strip()
    
    if not name or not abbreviation:
        flash('Nombre y abreviación son requeridos', 'error')
        return redirect(url_for('admin.venues'))
    
    # Check if abbreviation exists
    if Venue.query.filter_by(abbreviation=abbreviation).first():
        flash('La abreviación ya existe', 'error')
        return redirect(url_for('admin.venues'))
    
    venue = Venue(
        name=name,
        description=description,
        abbreviation=abbreviation,
        country=country
    )
    db.session.add(venue)
    db.session.commit()
    
    flash(f'Recinto "{name}" creado exitosamente', 'success')
    return redirect(url_for('admin.venues'))


@admin_bp.route('/venues/<int:venue_id>/update', methods=['POST'])
@admin_required
def update_venue(venue_id):
    """Update venue"""
    venue = Venue.query.get_or_404(venue_id)
    
    venue.name = request.form.get('name', venue.name).strip()
    venue.description = request.form.get('description', venue.description).strip()
    venue.abbreviation = request.form.get('abbreviation', venue.abbreviation).strip().upper()
    venue.country = request.form.get('country', venue.country).strip()
    
    db.session.commit()
    flash(f'Recinto "{venue.name}" actualizado', 'success')
    return redirect(url_for('admin.venues'))


@admin_bp.route('/venues/<int:venue_id>/delete', methods=['POST'])
@admin_required
def delete_venue(venue_id):
    """Delete venue"""
    venue = Venue.query.get_or_404(venue_id)
    
    # Check if venue has competitions
    if venue.competitions.count() > 0:
        return jsonify({'success': False, 'message': 'No se puede eliminar, tiene competencias asociadas'}), 400
    
    db.session.delete(venue)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Recinto eliminado'})


# ============================================
# Competitions Management
# ============================================

@admin_bp.route('/competitions')
@login_required
def competitions():
    """Competitions management page"""
    competitions = Competition.query.order_by(Competition.event_date.desc()).all()
    venues = Venue.query.filter_by(active=True).all()
    return render_template('admin/competitions.html', competitions=competitions, venues=venues)


@admin_bp.route('/competitions/create', methods=['POST'])
@admin_required
def create_competition():
    """Create new competition"""
    name = request.form.get('name', '').strip()
    venue_id = request.form.get('venue_id')
    event_date_str = request.form.get('event_date')
    
    # Convert date string to Python date object
    event_date = None
    if event_date_str:
        try:
            event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    if not name:
        flash('El nombre es requerido', 'error')
        return redirect(url_for('admin.competitions'))
    
    competition = Competition(
        name=name,
        venue_id=int(venue_id) if venue_id else None,
        event_date=event_date
    )
    db.session.add(competition)
    db.session.commit()
    
    flash(f'Competencia "{name}" creada exitosamente', 'success')
    return redirect(url_for('admin.competitions'))


@admin_bp.route('/competitions/<int:comp_id>/update', methods=['POST'])
@admin_required
def update_competition(comp_id):
    """Update competition"""
    competition = Competition.query.get_or_404(comp_id)
    
    competition.name = request.form.get('name', competition.name).strip()
    venue_id = request.form.get('venue_id')
    competition.venue_id = int(venue_id) if venue_id else None
    
    # Convert date string to Python date object
    event_date_str = request.form.get('event_date')
    if event_date_str:
        try:
            competition.event_date = datetime.strptime(event_date_str, '%Y-%m-%d').date()
        except ValueError:
            competition.event_date = None
    else:
        competition.event_date = None
    
    db.session.commit()
    flash(f'Competencia "{competition.name}" actualizada', 'success')
    return redirect(url_for('admin.competitions'))


@admin_bp.route('/competitions/<int:comp_id>/delete', methods=['POST'])
@admin_required
def delete_competition(comp_id):
    """Delete competition"""
    competition = Competition.query.get_or_404(comp_id)
    
    db.session.delete(competition)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Competencia eliminada'})


# ============================================
# Configuration
# ============================================

@admin_bp.route('/config')
@login_required
def config():
    """Configuration page"""
    configs = Configuration.query.all()
    venues = get_all_venues()
    
    return render_template('admin/config.html', configs=configs, venues=venues)


@admin_bp.route('/config/update', methods=['POST'])
@admin_required
def update_config():
    """Update configuration"""
    try:
        key = request.form.get('key')
        value = request.form.get('value')
        description = request.form.get('description')
        
        if not key:
            return jsonify({'success': False, 'message': 'Key is required'}), 400
        
        set_config_value(key, value, description)
        
        flash('Configuración actualizada correctamente', 'success')
        return jsonify({'success': True, 'message': 'Configuration updated'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@admin_bp.route('/scraping')
@login_required
def scraping():
    """Scraping management page"""
    from app.modules.scraping.scraping_config import ScrapingConfig
    
    venues = get_all_venues()
    recent_logs = ScrapingLog.query.order_by(ScrapingLog.started_at.desc()).limit(50).all()
    
    # Pass current configuration to template
    config = {
        'fecha': ScrapingConfig.DIA_REUNION,
        'hipodromo': ScrapingConfig.HIPODROMO,
        'has_credentials': ScrapingConfig.has_credentials()
    }
    
    # Get competitions suitable for scraping (Activa or Parcial)
    # We want to group them or list them so the user can select.
    # The UI requirement: "permitir seleccionar los Recintos o Hipodromos... visualizar en una tabla las Competencias involucradas"
    # Actually, showing all Active/Parcial competitions in a table allows filtering by Venue in the frontend or backend.
    # Let's pass the list of scrapable competitions.
    # Get active/partial competitions
    competitions = Competition.query.filter(
        Competition.status.in_(['Activa', 'Parcial', 'Scraper'])
    ).order_by(Competition.event_date.desc()).all()
    
    # Enrich with P/R/V status
    from app.modules.scraping.utils import check_scraping_status
    
    enriched_competitions = []
    
    for comp in competitions:
        comp_data = {
            'id': comp.id,
            'name': comp.name,
            'event_date': comp.event_date,
            'venue': comp.venue,
            'status': comp.status,
            'progress': check_scraping_status(comp)
        }
        enriched_competitions.append(comp_data)
    
    return render_template(
        'admin/scraping.html', 
        venues=venues, 
        logs=recent_logs, 
        config=config,
        scrapable_competitions=enriched_competitions
    )


@admin_bp.route('/competitions/sync', methods=['POST'])
@admin_required
def sync_competitions_status():
    """Sync competition status with existing files"""
    from app.modules.scraping.utils import check_scraping_status
    
    try:
        competitions = Competition.query.all()
        updated_count = 0
        
        for comp in competitions:
            status = check_scraping_status(comp)
            
            # Logic for status update
            # If all components are present -> Scraper
            # If some are present -> Parcial
            # If none -> Activa (if it was Scraper/Parcial, rollback? Or keep Activa?)
            # Let's assume Activa is default.
            
            new_status = 'Activa'
            if status['P'] and status['R'] and status['V']:
                new_status = 'Scraper'
            elif status['P'] or status['R'] or status['V']:
                new_status = 'Parcial'
            
            # Only update if changed
            if comp.status != new_status:
                # If state is already DB, do we overwrite? 
                # User complaint is about "Activa" persistence.
                # Let's say we only touch Activa/Parcial/Scraper. Leave DB alone.
                if comp.status != 'DB': 
                    comp.status = new_status
                    updated_count += 1
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Sincronizadas {updated_count} competencias'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ============================================
# Data Explorer
# ============================================

@admin_bp.route('/data-explorer')
@login_required
def data_explorer():
    """Data explorer page"""
    venues = Venue.query.filter_by(active=True).all()
    return render_template('admin/data_explorer.html', venues=venues)


@admin_bp.route('/api/data-explorer/meetings')
@login_required
def api_get_meetings():
    """API to get meetings with filters"""
    date_str = request.args.get('date')
    competition_id = request.args.get('competition_id')
    
    query = RaceMeeting.query
    
    if date_str:
        try:
            target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter(RaceMeeting.date == target_date)
        except ValueError:
            pass
            
    if venue_id:
        query = query.filter(RaceMeeting.venue_id == venue_id)
        
    if competition_id:
        query = query.join(Race).filter(Race.competition_id == competition_id)
        
    meetings = query.order_by(RaceMeeting.date.desc()).all()
    
    return jsonify([{
        'id': m.id,
        'date': m.date.isoformat() if m.date else None,
        'venue': m.venue.name if m.venue else 'N/A',
        'venue_abbr': m.venue.abbreviation if m.venue else 'N/A',
        'number': m.number,
        'races_count': m.races.count()
    } for m in meetings])


@admin_bp.route('/api/data-explorer/races/<meeting_id>')
@login_required
def api_get_races(meeting_id):
    """API to get races for a meeting"""
    races = Race.query.filter_by(meeting_id=meeting_id).order_by(Race.correlativo).all()
    
    return jsonify([{
        'id': r.id,
        'correlativo': r.correlativo,
        'time': r.time,
        'prize': r.prize_name,
        'distance': r.distance,
        'type': r.race_type,
        'surface': r.surface,
        'performances_count': r.performances.count()
    } for r in races])


@admin_bp.route('/api/data-explorer/performances/<race_id>')
@login_required
def api_get_performances(race_id):
    """API to get performances for a race"""
    perfs = RacePerformance.query.filter_by(race_id=race_id).all()
    
    # Sort by position (handling alphanumeric and nulls)
    def sort_pos(p):
        try:
            return int(p.position) if p.position and p.position.isdigit() else 999
        except:
            return 999
            
    perfs.sort(key=sort_pos)
    
    return jsonify([{
        'id': p.id,
        'position': p.position,
        'horse': getattr(p, 'horse', None).name if hasattr(p, 'horse') and p.horse else 'N/A',
        'mandil': p.mandil_number,
        'jockey': getattr(p, 'jockey', None).name if hasattr(p, 'jockey') and p.jockey else 'N/A',
        'trainer': getattr(p, 'trainer', None).name if hasattr(p, 'trainer') and p.trainer else 'N/A',
        'weight_horse': p.weight_horse,
        'dividend': p.dividend
    } for p in perfs])


@admin_bp.route('/api/data-explorer/competitions')
@login_required
def api_get_competitions():
    """API to get competitions for filtration"""
    venue_id = request.args.get('venue_id')
    query = Competition.query
    if venue_id:
        query = query.filter_by(venue_id=venue_id)
    
    comps = query.order_by(Competition.name).all()
    return jsonify([{
        'id': c.id,
        'name': c.name,
        'venue_id': c.venue_id
    } for c in comps])


@admin_bp.route('/api/data-explorer/export/performances/<race_id>')
@login_required
def export_performances_csv(race_id):
    """Export race performances to CSV"""
    race = Race.query.get_or_404(race_id)
    perfs = RacePerformance.query.filter_by(race_id=race_id).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Posicion', 'Mandil', 'Caballo', 'Jinete', 'Preparador', 'Peso Caballo', 'Dividendo'])
    
    # Data
    for p in perfs:
        writer.writerow([
            p.position,
            p.mandil_number,
            p.horse.name if p.horse else 'N/A',
            p.jockey.name if p.jockey else 'N/A',
            p.trainer.name if p.trainer else 'N/A',
            p.weight_horse,
            p.dividend
        ])
    
    output.seek(0)
    
    filename = f"resultados_{race.meeting.venue.abbreviation if race.meeting.venue else 'race'}_{race.meeting.date}_{race.correlativo}.csv"
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": f"attachment; filename={filename}"}
    )
