"""
Data Sports Lab - Entry Point
Main application runner for development and production
"""
from app import create_app
import os

# Create Flask application instance
app = create_app()

if __name__ == '__main__':
    # Get configuration from environment
    debug_mode = os.getenv('FLASK_DEBUG', 'True') == 'True'
    port = int(os.getenv('FLASK_PORT', 5000))
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    
    print(f"""
    ╔═══════════════════════════════════════════════════════════╗
    ║  Data Sports Lab                                         ║
    ║  Ciencia de datos en competencias deportivas             ║
    ╠═══════════════════════════════════════════════════════════╣
    ║  Server running on: http://{host}:{port}                 ║
    ║  Debug mode: {debug_mode}                                        ║
    ╚═══════════════════════════════════════════════════════════╝
    """)
    
    # Run the application
    app.run(
        host=host,
        port=port,
        debug=debug_mode
    )
# Reload trigger
