
from app import create_app, db
from app.models import Competition
from app.modules.scraping.utils import check_scraping_status
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def sync_status():
    app = create_app()
    with app.app_context():
        competitions = Competition.query.all()
        logger.info(f"Found {len(competitions)} competitions to check.")
        
        updated_count = 0
        
        for comp in competitions:
            # 1. Get current physical status (P/R/V flags based on files)
            flags = check_scraping_status(comp)
            
            p = flags.get('P', False)
            r = flags.get('R', False)
            v = flags.get('V', False)
            
            # 2. Determine correct status string
            new_status = 'Pending' # Default
            
            if p and r and v:
                new_status = 'Scraper'
            elif p or r or v:
                new_status = 'Parcial'
            elif p:
                new_status = 'Program'
                
            # 3. Update if different
            if comp.status != new_status:
                logger.info(f"Updating {comp.venue.abbreviation} {comp.event_date}: '{comp.status}' -> '{new_status}' (P={p}, R={r}, V={v})")
                comp.status = new_status
                updated_count += 1
                
        if updated_count > 0:
            db.session.commit()
            logger.info(f"Successfully updated {updated_count} competitions.")
        else:
            logger.info("All competitions are already in sync.")

if __name__ == "__main__":
    sync_status()
