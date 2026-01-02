from app import create_app, db
from app.models import Competition
from app.modules.scraping.utils import check_scraping_status

def sync_all_statuses():
    app = create_app()
    with app.app_context():
        competitions = Competition.query.all()
        print(f"Syncing {len(competitions)} competitions...")
        
        updated_count = 0
        for comp in competitions:
            # Check file status
            status_flags = check_scraping_status(comp)
            
            # Determine new status
            new_status = 'Activa'
            if status_flags['P'] and status_flags['R'] and status_flags['V']:
                new_status = 'Scraper' # All complete
            elif status_flags['P'] or status_flags['R'] or status_flags['V']:
                new_status = 'Parcial' # Partially complete
            
            # Update if changed
            if comp.status != new_status:
                print(f"Updating ID {comp.id} ({comp.venue.abbreviation} {comp.event_date}): {comp.status} -> {new_status}")
                comp.status = new_status
                updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"Successfully updated {updated_count} competitions.")
        else:
            print("All competitions are already in sync.")

if __name__ == "__main__":
    sync_all_statuses()
