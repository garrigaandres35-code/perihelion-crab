"""
Database Models
SQLAlchemy models for the application
"""
from app import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin


# ============================================
# User & Authentication Models
# ============================================

class Profile(db.Model):
    """User profile/role model"""
    __tablename__ = 'profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)  # admin, analyst, viewer
    description = db.Column(db.String(200))
    permissions = db.Column(db.JSON)  # Lista de permisos
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    users = db.relationship('User', backref='profile', lazy='dynamic')
    
    def __repr__(self):
        return f'<Profile {self.name}>'


class User(UserMixin, db.Model):
    """User model with authentication"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False, unique=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    profile_id = db.Column(db.Integer, db.ForeignKey('profiles.id'))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        """Hash and set the password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Check if password matches"""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        """Check if user has admin profile"""
        return self.profile and self.profile.name == 'admin'
    
    def __repr__(self):
        return f'<User {self.email}>'


# ============================================
# Venue & Competition Models
# ============================================

class Venue(db.Model):
    """Venue/Recinto Deportivo model"""
    __tablename__ = 'venues'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500))
    abbreviation = db.Column(db.String(20), unique=True)
    country = db.Column(db.String(100))
    city = db.Column(db.String(100))
    active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    competitions = db.relationship('Competition', backref='venue', lazy='dynamic')
    meetings = db.relationship('RaceMeeting', backref='venue', lazy='dynamic')

    @classmethod
    def update_or_create(cls, data):
        venue = cls.query.filter_by(abbreviation=data.get('abbreviation')).first()
        if not venue:
            venue = cls(abbreviation=data.get('abbreviation'))
            db.session.add(venue)
        
        venue.name = data.get('name', venue.name)
        venue.country = data.get('country', venue.country)
        venue.city = data.get('city', venue.city)
        return venue

    def __repr__(self):
        return f'<Venue {self.abbreviation} - {self.name}>'


class Competition(db.Model):
    """Competition/Competencia model"""
    __tablename__ = 'competitions'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'))
    event_date = db.Column(db.Date, nullable=True)  # Nula por defecto
    active = db.Column(db.Boolean, default=True)
    status = db.Column(db.String(20), default='Activa')  # Activa, Scraper, Parcial, DB
    pdf_volante_path = db.Column(db.String(500), nullable=True)  # Ruta al PDF del volante
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    races = db.relationship('Race', backref='competition', lazy='dynamic')
    
    @classmethod
    def update_or_create(cls, data):
        comp = cls.query.filter_by(name=data.get('name'), venue_id=data.get('venue_id')).first()
        if not comp:
            comp = cls(name=data.get('name'), venue_id=data.get('venue_id'))
            db.session.add(comp)
        
        if data.get('event_date'):
            comp.event_date = data['event_date']
        comp.active = data.get('active', comp.active)
        if data.get('status'):
            comp.status = data.get('status')
        return comp

    def __repr__(self):
        return f'<Competition {self.name}>'


# ============================================
# Scraping & Configuration Models
# ============================================

class ScrapingLog(db.Model):
    """Scraping activity log"""
    __tablename__ = 'scraping_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    source_type = db.Column(db.String(50), nullable=False)  # web, pdf
    source_name = db.Column(db.String(100))
    status = db.Column(db.String(20), nullable=False)  # success, error, pending
    records_processed = db.Column(db.Integer, default=0)
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def __repr__(self):
        return f'<ScrapingLog {self.source_type} - {self.status}>'


class Configuration(db.Model):
    """Application configuration storage"""
    __tablename__ = 'configurations'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<Configuration {self.key}>'


# ============================================
# Horse Racing Entities
# ============================================

class Horse(db.Model):
    """Horse master data"""
    __tablename__ = 'horses'
    
    id = db.Column(db.String(50), primary_key=True)  # id_ejemplar
    name = db.Column(db.String(200), nullable=False)
    birth_date = db.Column(db.Date)
    sex = db.Column(db.String(10))
    color = db.Column(db.String(50))
    
    # Lineage
    sire_id = db.Column(db.String(50), db.ForeignKey('horses.id'))
    dam_id = db.Column(db.String(50), db.ForeignKey('horses.id'))
    abuelo_id = db.Column(db.String(50), db.ForeignKey('horses.id'))
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @classmethod
    def update_or_create(cls, data):
        horse = cls.query.get(data['id_ejemplar'])
        if not horse:
            horse = cls(id=data['id_ejemplar'])
            db.session.add(horse)
        
        horse.name = data.get('nombre', horse.name)
        horse.birth_date = datetime.strptime(data['fecha_nac'], '%Y-%m-%d').date() if data.get('fecha_nac') else None
        horse.sex = data.get('sexo', horse.sex)
        horse.color = data.get('pelo', horse.color)
        
        # Lineage IDs are handles separately to ensure parent existence
        if data.get('id_padrillo'): horse.sire_id = data['id_padrillo']
        # Note: dam and abuelo IDs might need more complex logic during load
        
        return horse

    def __repr__(self):
        return f'<Horse {self.name}>'


class Jockey(db.Model):
    """Jockey master data"""
    __tablename__ = 'jockeys'
    
    id = db.Column(db.String(50), primary_key=True)  # id_jinete
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def update_or_create(cls, data):
        jockey = cls.query.get(data['id_jinete'])
        if not jockey:
            jockey = cls(id=data['id_jinete'])
            db.session.add(jockey)
        jockey.name = data.get('nom_jinete', jockey.name)
        return jockey


class Trainer(db.Model):
    """Trainer master data"""
    __tablename__ = 'trainers'
    
    id = db.Column(db.String(50), primary_key=True)  # id_entrenador
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def update_or_create(cls, data):
        trainer = cls.query.get(data['id_entrenador'])
        if not trainer:
            trainer = cls(id=data['id_entrenador'])
            db.session.add(trainer)
        trainer.name = data.get('entrenador', trainer.name)
        return trainer


class Owner(db.Model):
    """Owner master data"""
    __tablename__ = 'owners'
    
    id = db.Column(db.String(50), primary_key=True)  # id_dueno
    name = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @classmethod
    def update_or_create(cls, data):
        owner = cls.query.get(data['id_dueno'])
        if not owner:
            owner = cls(id=data['id_dueno'])
            db.session.add(owner)
        owner.name = data.get('dueno', owner.name)
        return owner


class RaceMeeting(db.Model):
    """A series of races at a venue on a specific date"""
    __tablename__ = 'race_meetings'
    
    id = db.Column(db.String(50), primary_key=True)  # id_reunion
    venue_id = db.Column(db.Integer, db.ForeignKey('venues.id'))
    date = db.Column(db.Date, nullable=False)
    number = db.Column(db.String(50))
    director = db.Column(db.String(200))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    races = db.relationship('Race', backref='meeting', lazy='dynamic')

    @classmethod
    def update_or_create(cls, data, venue_id):
        meeting = cls.query.get(data['id_reunion'])
        if not meeting:
            meeting = cls(id=data['id_reunion'], venue_id=venue_id)
            db.session.add(meeting)
        
        meeting.date = datetime.strptime(data['fecha_reunion'], '%Y-%m-%d').date() if data.get('fecha_reunion') else None
        meeting.number = data.get('numero_reunion')
        meeting.director = data.get('director_turno')
        return meeting


class Race(db.Model):
    """Individual race details"""
    __tablename__ = 'races'
    
    id = db.Column(db.String(50), primary_key=True)  # id_carrera
    meeting_id = db.Column(db.String(50), db.ForeignKey('race_meetings.id'))
    competition_id = db.Column(db.Integer, db.ForeignKey('competitions.id'), nullable=True)
    correlativo = db.Column(db.Integer)
    time = db.Column(db.String(20))
    prize_name = db.Column(db.String(200))
    prize_1 = db.Column(db.Float)
    is_classic = db.Column(db.Boolean, default=False)
    race_type = db.Column(db.String(100))
    surface = db.Column(db.String(100))
    distance = db.Column(db.String(50))
    condition = db.Column(db.Text)
    index_range = db.Column(db.String(50))
    
    # PDF Scraping Data
    prediction_options = db.Column(db.JSON)
    competitors_count_pdf = db.Column(db.Integer)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    performances = db.relationship('RacePerformance', backref='race', lazy='dynamic')

    @classmethod
    def update_or_create(cls, data, meeting_id):
        race = cls.query.get(data['id_carrera'])
        if not race:
            race = cls(id=data['id_carrera'], meeting_id=meeting_id)
            db.session.add(race)
            
        race.correlativo = int(data.get('correlativo', 0))
        race.time = data.get('hora_carrera')
        race.prize_name = data.get('nombre_premio')
        
        p1 = data.get('premio1', '0').replace('.', '')
        race.prize_1 = float(p1) if p1.isdigit() else 0.0
        
        race.is_classic = bool(data.get('es_clasico'))
        race.race_type = data.get('tipo_carrera')
        race.surface = data.get('superficie')
        race.distance = data.get('distance')
        race.condition = data.get('condicion')
        race.index_range = data.get('indice')
        
        return race


class RacePerformance(db.Model):
    """Horse performance in a specific race"""
    __tablename__ = 'race_performances'
    
    id = db.Column(db.Integer, primary_key=True)
    race_id = db.Column(db.String(50), db.ForeignKey('races.id'))
    horse_id = db.Column(db.String(50), db.ForeignKey('horses.id'))
    jockey_id = db.Column(db.String(50), db.ForeignKey('jockeys.id'))
    trainer_id = db.Column(db.String(50), db.ForeignKey('trainers.id'))
    owner_id = db.Column(db.String(50), db.ForeignKey('owners.id'))
    
    mandil_number = db.Column(db.String(10))
    gate_number = db.Column(db.Integer)
    weight_horse = db.Column(db.Float)
    weight_jockey = db.Column(db.Float)
    
    # Results
    position = db.Column(db.String(20))
    dividend = db.Column(db.Float)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Explicit Relationships
    horse = db.relationship('Horse', foreign_keys=[horse_id], backref='performances_list')
    jockey = db.relationship('Jockey', foreign_keys=[jockey_id], backref='performances_list')
    trainer = db.relationship('Trainer', foreign_keys=[trainer_id], backref='performances_list')
    owner = db.relationship('Owner', foreign_keys=[owner_id], backref='performances_list')

    @classmethod
    def update_or_create(cls, data, race_id):
        # Unique identifier for performance is usually race_id + horse_id
        perf = cls.query.filter_by(race_id=race_id, horse_id=data['id_ejemplar']).first()
        if not perf:
            perf = cls(race_id=race_id, horse_id=data['id_ejemplar'])
            db.session.add(perf)
            
        perf.jockey_id = data.get('id_jinete')
        perf.trainer_id = data.get('id_entrenador')
        perf.owner_id = data.get('id_dueno')
        
        perf.mandil_number = data.get('num_mandil')
        perf.gate_number = int(data['num_partidor']) if data.get('num_partidor') and str(data['num_partidor']).isdigit() else None
        perf.weight_horse = float(data['peso_ejemplar']) if data.get('peso_ejemplar') else None
        perf.weight_jockey = float(data['peso_jinete']) if data.get('peso_jinete') else None
        
        perf.position = str(data.get('lugar'))
        div = str(data.get('dividendo', '0')).replace(',', '.')
        try:
            perf.dividend = float(div)
        except ValueError:
            perf.dividend = 0.0
            
        return perf


class ProcessedFile(db.Model):
    """Tracking of processed JSON files"""
    __tablename__ = 'processed_files'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(300), unique=True, nullable=False)
    file_hash = db.Column(db.String(64))
    source_type = db.Column(db.String(50))  # web_program, web_result, pdf_volante
    processed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ProcessedFile {self.filename}>'
