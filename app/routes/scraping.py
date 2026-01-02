"""
Scraping Routes Blueprint
Handles scraping-related routes for Web and PDF scraping
"""
import os
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from werkzeug.utils import secure_filename
from pathlib import Path
from datetime import datetime

from app.models import ScrapingLog, Venue, Competition
from app import db
from app.modules.scraping.scraping_config import ScrapingConfig

scraping_bp = Blueprint('scraping', __name__)

# Allowed extensions for PDF upload
ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ========================================
# Configuration Endpoints
# ========================================

@scraping_bp.route('/config', methods=['GET'])
@login_required
def get_config():
    """Get current scraping configuration"""
    return jsonify({
        'fecha': ScrapingConfig.DIA_REUNION,
        'hipodromo': ScrapingConfig.HIPODROMO,
        'has_credentials': ScrapingConfig.has_credentials(),
        'hipodromos': [
            {'code': code, 'name': info['name']} 
            for code, info in ScrapingConfig.HIPODROMOS.items()
        ]
    })


@scraping_bp.route('/config', methods=['POST'])
@login_required
def update_config():
    """Update scraping configuration"""
    try:
        data = request.json
        fecha = data.get('fecha')
        hipodromo = data.get('hipodromo')
        
        ScrapingConfig.update_config(fecha, hipodromo)
        
        return jsonify({
            'success': True,
            'message': 'Configuration updated',
            'config': {
                'fecha': ScrapingConfig.DIA_REUNION,
                'hipodromo': ScrapingConfig.HIPODROMO
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@scraping_bp.route('/competitions/run', methods=['POST'])
@login_required
def run_competition_scraping():
    """Run full scraping process for a competition"""
    try:
        from app.modules.scraping import ElTurfScraper, PDFScraperManager
        from app.modules.scraping.scraping_config import ScrapingConfig
        from app.modules.scraping.utils import check_scraping_status
        
        data = request.json or {}
        comp_id = data.get('competition_id')
        
        if not comp_id:
            return jsonify({'success': False, 'message': 'Competition ID required'}), 400
            
        competition = Competition.query.get(comp_id)
        if not competition:
            return jsonify({'success': False, 'message': 'Competition not found'}), 404
            
        # Get params from competition
        fecha = competition.event_date.strftime('%Y-%m-%d')
        # Map venue id to code (assuming venue has abbreviation)
        hipodromo = competition.venue.abbreviation
        
        if not hipodromo:
             return jsonify({'success': False, 'message': 'Competition venue has no abbreviation'}), 400

        # Update config temporarily (optional but good for consistency)
        ScrapingConfig.update_config(fecha, hipodromo)
        
        logging_messages = []
        
        # Check existing status
        current_status = check_scraping_status(competition)
        logging_messages.append(f"Pre-check: P={current_status['P']}, R={current_status['R']}, V={current_status['V']}")
        
        scraper = ElTurfScraper(fecha=fecha, hipodromo=hipodromo)
        
        # 1. Web Scraping - Programas
        if not current_status['P']:
            prog_result = scraper.scrape_programas()
            logging_messages.append(f"Programas: {'OK' if prog_result.get('success') else 'Error'}")
        else:
            prog_result = {'success': True, 'skipped': True, 'message': 'Already exists'}
            logging_messages.append("Programas: Skipped (Exists)")
        
        # 2. Web Scraping - Resultados
        if not current_status['R']:
            res_result = scraper.scrape_resultados()
            logging_messages.append(f"Resultados: {'OK' if res_result.get('success') else 'Error'}")
        else:
            res_result = {'success': True, 'skipped': True, 'message': 'Already exists'}
            logging_messages.append("Resultados: Skipped (Exists)")
        
        # 3. PDF Scraping (Batch for track)
        # Note: This processes all PDFs in the track folder. 
        # Ideally we would only process PDFs for this date/competition if we could filter.
        # But PDFScraperManager.process_directory takes 'track'.
        # We'll run it and assume it handles what's there.
        pdf_manager = PDFScraperManager(track=hipodromo)
        # Pass target_date to allow content-based filtering
        pdf_result = pdf_manager.process_directory(track=hipodromo, target_date=fecha) 
        logging_messages.append(f"PDFs: {pdf_result.get('processed', 0)} procesados, {pdf_result.get('failed', 0)} fallidos")
        
        # Determine Status
        # Check P & R
        success_prog = prog_result.get('success', False)
        success_res = res_result.get('success', False)
        
        # Check V (Volantes) logic is now partially handled by check_scraping_status
        # But after running PDF scraping, we should re-check status or trust the process result?
        # Let's rely on standard check_scraping_status logic AGAIN to be sure what we have on disk
        
        final_status_flags = check_scraping_status(competition)
        volante_success = final_status_flags['V']


        new_status = 'Parcial'
        # Log status components for better debugging if needed
        logging_messages.append(f"Status components - P: {success_prog}, R: {success_res}, V: {volante_success}")

        if success_prog and success_res and volante_success:
            new_status = 'Scraper'
        
        # Update Competition Status
        competition.status = new_status
        db.session.commit()
        
        # Log to DB (Summary)
        log = ScrapingLog(
            source_type='full_process',
            source_name=f"{hipodromo} - {fecha}",
            status='success' if new_status == 'Scraper' else 'warning',
            records_processed=prog_result.get('races_saved', 0) + res_result.get('races_count', 0),
            error_message=" | ".join(logging_messages),
            started_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'status': new_status,
            'message': f"Proceso completado. Estado: {new_status}",
            'results': {
                'programas': prog_result,
                'resultados': res_result,
                'pdf': pdf_result
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# Web Scraping Endpoints
# ========================================

@scraping_bp.route('/web/programas', methods=['POST'])
@login_required
def scrape_web_programas():
    """Start web scraping for programs"""
    try:
        from app.modules.scraping import ElTurfScraper
        
        data = request.json or {}
        fecha = data.get('fecha', ScrapingConfig.DIA_REUNION)
        hipodromo = data.get('hipodromo', ScrapingConfig.HIPODROMO)
        
        # Create scraping log
        log = ScrapingLog(
            source_type='web',
            source_name=f"{hipodromo} - Programas",
            status='running',
            started_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        # Run scraper
        scraper = ElTurfScraper(fecha=fecha, hipodromo=hipodromo)
        result = scraper.scrape_programas()
        
        # Update log
        log.status = 'success' if result.get('success') else 'error'
        log.completed_at = datetime.utcnow()
        log.records_processed = result.get('races_saved', 0)
        if not result.get('success'):
            log.error_message = result.get('error')
        db.session.commit()
        
        return jsonify({
            'success': result.get('success'),
            'log_id': log.id,
            **result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@scraping_bp.route('/web/resultados', methods=['POST'])
@login_required
def scrape_web_resultados():
    """Start web scraping for results"""
    try:
        from app.modules.scraping import ElTurfScraper
        
        data = request.json or {}
        fecha = data.get('fecha', ScrapingConfig.DIA_REUNION)
        hipodromo = data.get('hipodromo', ScrapingConfig.HIPODROMO)
        
        # Create scraping log
        log = ScrapingLog(
            source_type='web',
            source_name=f"{hipodromo} - Resultados",
            status='running',
            started_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        # Run scraper
        scraper = ElTurfScraper(fecha=fecha, hipodromo=hipodromo)
        result = scraper.scrape_resultados()
        
        # Update log
        log.status = 'success' if result.get('success') else 'error'
        log.completed_at = datetime.utcnow()
        log.records_processed = result.get('races_count', 0)
        if not result.get('success'):
            log.error_message = result.get('error')
        db.session.commit()
        
        return jsonify({
            'success': result.get('success'),
            'log_id': log.id,
            **result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# PDF Scraping Endpoints
# ========================================

@scraping_bp.route('/pdf/upload', methods=['POST'])
@login_required
def upload_pdf():
    """Upload and process a single PDF"""
    try:
        from app.modules.scraping import PDFScraperManager
        
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file provided'}), 400
        
        file = request.files['file']
        track = request.form.get('track', ScrapingConfig.HIPODROMO).lower()
        
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'message': 'Invalid file type. Only PDF allowed'}), 400
        
        # Save uploaded file
        filename = secure_filename(file.filename)
        pdf_dir = Path(ScrapingConfig.PATH_PDF_SCRAPING) / 'pdfs' / track
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / filename
        file.save(str(pdf_path))
        
        # Create scraping log
        log = ScrapingLog(
            source_type='pdf',
            source_name=f"{track.upper()} - {filename}",
            status='running',
            started_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        # Process PDF
        manager = PDFScraperManager(track=track)
        result = manager.process_pdf(str(pdf_path), track)
        
        # Update log
        log.status = 'success' if result.get('success') else 'error'
        log.completed_at = datetime.utcnow()
        log.records_processed = result.get('races_count', 0)
        if not result.get('success'):
            log.error_message = result.get('error')
        db.session.commit()
        
        return jsonify({
            'success': result.get('success'),
            'log_id': log.id,
            **result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@scraping_bp.route('/pdf/batch', methods=['POST'])
@login_required
def process_pdf_batch():
    """Process all PDFs in a track's directory"""
    try:
        from app.modules.scraping import PDFScraperManager
        
        data = request.json or {}
        track = data.get('track', ScrapingConfig.HIPODROMO).lower()
        
        # Create scraping log
        log = ScrapingLog(
            source_type='pdf',
            source_name=f"{track.upper()} - Batch",
            status='running',
            started_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        # Process batch
        manager = PDFScraperManager(track=track)
        result = manager.process_directory(track=track)
        
        # Update log
        log.status = 'success' if result.get('success') else 'error'
        log.completed_at = datetime.utcnow()
        log.records_processed = result.get('processed', 0)
        if not result.get('success'):
            log.error_message = f"Failed: {result.get('failed', 0)}"
        db.session.commit()
        
        return jsonify({
            'success': result.get('success'),
            'log_id': log.id,
            **result
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@scraping_bp.route('/pdf/list/<track>', methods=['GET'])
@login_required
def list_pdfs(track):
    """List PDFs available for a track"""
    try:
        from app.modules.scraping import PDFScraperManager
        
        manager = PDFScraperManager(track=track)
        pdfs = manager.list_pdfs(track)
        jsons = manager.list_json_files(track)
        
        return jsonify({
            'success': True,
            'track': track,
            'pdfs': pdfs,
            'jsons': jsons
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# ========================================
# Compatibility Endpoints (existing)
# ========================================

@scraping_bp.route('/start', methods=['POST'])
@login_required
def start_scraping():
    """Start scraping process (legacy endpoint)"""
    try:
        source_type = request.json.get('source_type', 'web')
        venue_abbr = request.json.get('venue_code')
        
        # Create scraping log
        log = ScrapingLog(
            source_type=source_type,
            source_name=venue_abbr,
            status='pending',
            started_at=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
        
        # Route to appropriate scraper
        if source_type == 'web':
            from app.modules.scraping import ElTurfScraper
            scraper = ElTurfScraper(hipodromo=venue_abbr)
            result = scraper.scrape_programas()
        else:
            from app.modules.scraping import PDFScraperManager
            manager = PDFScraperManager(track=venue_abbr)
            result = manager.process_directory()
        
        log.status = 'success' if result.get('success') else 'error'
        log.completed_at = datetime.utcnow()
        log.records_processed = result.get('races_count', result.get('processed', 0))
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Scraping completed',
            'log_id': log.id,
            **result
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        }), 500


@scraping_bp.route('/status/<int:log_id>')
@login_required
def scraping_status(log_id):
    """Get scraping status"""
    log = ScrapingLog.query.get_or_404(log_id)
    
    return jsonify({
        'id': log.id,
        'source_type': log.source_type,
        'source_name': log.source_name,
        'status': log.status,
        'records_processed': log.records_processed,
        'error_message': log.error_message,
        'started_at': log.started_at.isoformat() if log.started_at else None,
        'completed_at': log.completed_at.isoformat() if log.completed_at else None
    })


@scraping_bp.route('/logs', methods=['GET'])
@login_required
def get_logs():
    """Get scraping logs"""
    logs = ScrapingLog.query.order_by(ScrapingLog.started_at.desc()).limit(50).all()
    
    return jsonify({
        'success': True,
        'logs': [{
            'id': log.id,
            'source_type': log.source_type,
            'source_name': log.source_name,
            'status': log.status,
            'records_processed': log.records_processed,
            'error_message': log.error_message,
            'started_at': log.started_at.isoformat() if log.started_at else None,
            'completed_at': log.completed_at.isoformat() if log.completed_at else None
        } for log in logs]
    })


@scraping_bp.route('/process-logs', methods=['GET'])
@login_required
def get_process_logs():
    """Get latest logs from the log file"""
    try:
        log_file = os.path.join(os.getcwd(), 'logs', 'app.log')
        if not os.path.exists(log_file):
            return jsonify({'logs': []})
            
        # Read last 50 lines with proper encoding
        try:
            with open(log_file, 'r', encoding='utf-8', errors='replace') as f:
                lines = f.readlines()
                last_lines = lines[-50:] if len(lines) > 50 else lines
        except Exception as read_error:
            # Si falla la lectura, devolvemos un log de error
            return jsonify({'success': True, 'logs': [f"Error leyendo logs: {str(read_error)}"]})
            
        return jsonify({
            'success': True,
            'logs': [line.strip() for line in last_lines]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
