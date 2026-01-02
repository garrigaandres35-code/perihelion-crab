import json
import hashlib
import os
from datetime import datetime
from app import db
from app.models import Venue, RaceMeeting, Race, Horse, Jockey, Trainer, Owner, RacePerformance, ProcessedFile

class DataLoader:
    """
    Intelligent loader for JSON data into the SQLite database.
    Tracks processed files to avoid duplicates.
    """
    
    @staticmethod
    def get_file_hash(filepath):
        """Calculate SHA256 hash of a file"""
        hasher = hashlib.sha256()
        with open(filepath, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    @classmethod
    def is_file_processed(cls, filename, file_hash):
        """Check if file has already been processed with same hash"""
        processed = ProcessedFile.query.filter_by(filename=filename, file_hash=file_hash).first()
        return processed is not None

    @classmethod
    def mark_file_processed(cls, filename, file_hash, source_type):
        """Register a file as processed"""
        processed = ProcessedFile(
            filename=filename,
            file_hash=file_hash,
            source_type=source_type
        )
        db.session.add(processed)
        db.session.commit()

    @classmethod
    def load_web_program(cls, filepath):
        """Load a web scraping program JSON file"""
        filename = os.path.basename(filepath)
        file_hash = cls.get_file_hash(filepath)
        
        if cls.is_file_processed(filename, file_hash):
            return False, "File already processed"
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 1. Update Venue
            venue_data = {
                'abbreviation': data.get('abreviatura_hipodromo'),
                'name': data.get('nombre_hipodromo'),
                'country': data.get('pais_hipodromo'),
                'city': data.get('ciudad_hipodromo')
            }
            venue = Venue.update_or_create(venue_data)
            db.session.flush() # Ensure venue has ID if new
            
            # 2. Update Meeting
            meeting = RaceMeeting.update_or_create(data, venue.id)
            db.session.flush()
            
            # 3. Update Races
            for race_data in data.get('carreras', []):
                Race.update_or_create(race_data, meeting.id)
            
            db.session.commit()
            cls.mark_file_processed(filename, file_hash, 'web_program')
            return True, f"Successfully loaded {len(data.get('carreras', []))} races"
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def load_web_result(cls, filepath):
        """Load a web scraping result JSON file (updates Race entries with results)"""
        filename = os.path.basename(filepath)
        file_hash = cls.get_file_hash(filepath)
        
        if cls.is_file_processed(filename, file_hash):
            return False, "File already processed"
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Results usually have the same structure for meeting/races
            # but contain the 'primeros' list (top results)
            meeting_id = data.get('id_reunion')
            
            for race_data in data.get('carreras', []):
                race_id = race_data.get('id_carrera')
                
                # Update/Create entries for the winners/placed horses
                for perf_data in race_data.get('primeros', []):
                    # In results, 'id_ejemplar' is available
                    # We might need to handle Horse creation if it doesn't exist
                    # although usually it should be in the program already.
                    Horse.update_or_create(perf_data)
                    db.session.flush()
                    
                    RacePerformance.update_or_create(perf_data, race_id)
            
            db.session.commit()
            cls.mark_file_processed(filename, file_hash, 'web_result')
            return True, "Successfully loaded results"
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def load_pdf_volante(cls, filepath):
        """Load a PDF scraping volant JSON file (updates Race with predictions)"""
        filename = os.path.basename(filepath)
        file_hash = cls.get_file_hash(filepath)
        
        if cls.is_file_processed(filename, file_hash):
            return False, "File already processed"
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            fecha = data.get('fecha')
            recinto = data.get('recinto')
            
            # Find the corresponding meeting
            meeting = RaceMeeting.query.join(Venue).filter(
                RaceMeeting.date == datetime.strptime(fecha, '%Y-%m-%d').date(),
                Venue.abbreviation == recinto
            ).first()
            
            if not meeting:
                return False, f"No meeting found for {recinto} on {fecha}"
            
            for race_pdf in data.get('carreras', []):
                # Match by correlativo
                race = Race.query.filter_by(meeting_id=meeting.id, correlativo=race_pdf['numero']).first()
                if race:
                    race.prediction_options = race_pdf.get('opcion')
                    race.competitors_count_pdf = race_pdf.get('numero_competidores')
            
            db.session.commit()
            cls.mark_file_processed(filename, file_hash, 'pdf_volante')
            return True, f"Successfully updated {len(data.get('carreras', []))} races with PDF data"
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)

    @classmethod
    def load_web_detail(cls, filepath):
        """Load a web scraping detail JSON file (full horse/performance data)"""
        filename = os.path.basename(filepath)
        file_hash = cls.get_file_hash(filepath)
        
        if cls.is_file_processed(filename, file_hash):
            return False, "File already processed"
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            race_info = data.get('programa', {})
            race_id = race_info.get('id_carrera')
            
            if not race_id:
                return False, "No race ID found in detail file"
            
            # Update/Create race if it doesn't exist (though it should)
            meeting_id = race_info.get('id_reunion')
            race = Race.update_or_create(race_info, meeting_id)
            db.session.flush()
            
            # Process ejemplares
            ejemplares = data.get('detalle', {}).get('ejemplares', [])
            for ej_data in ejemplares:
                Horse.update_or_create(ej_data)
                Jockey.update_or_create(ej_data)
                Trainer.update_or_create(ej_data)
                Owner.update_or_create(ej_data)
                db.session.flush()
                
                RacePerformance.update_or_create(ej_data, race_id)
            
            db.session.commit()
            cls.mark_file_processed(filename, file_hash, 'web_detail')
            return True, f"Successfully loaded {len(ejemplares)} horse performances for race {race_id}"
            
        except Exception as e:
            db.session.rollback()
            return False, str(e)
