"""
Dynamic Menu System Utility
Loads and manages menu configuration
"""
import json
from pathlib import Path
from flask import current_app

def get_menu_items():
    """
    Load menu items from configuration file
    Returns list of menu items sorted by order
    """
    try:
        config_path = Path(current_app.config['CONFIG_DIR']) / 'menu_config.json'
        
        with open(config_path, 'r', encoding='utf-8') as f:
            menu_data = json.load(f)
        
        # Filter enabled items and sort by order
        menu_items = menu_data.get('menu_items', [])
        
        # Filter out disabled items
        enabled_items = [
            item for item in menu_items 
            if item.get('enabled', True)
        ]
        
        # Sort by order
        enabled_items.sort(key=lambda x: x.get('order', 999))
        
        return enabled_items
        
    except Exception as e:
        current_app.logger.error(f"Error loading menu configuration: {e}")
        return []

def get_menu_item_by_id(item_id):
    """
    Get a specific menu item by ID
    """
    menu_items = get_menu_items()
    
    for item in menu_items:
        if item['id'] == item_id:
            return item
        
        # Check submenu items
        if 'submenu' in item:
            for subitem in item['submenu']:
                if subitem['id'] == item_id:
                    return subitem
    
    return None

def update_menu_config(new_config):
    """
    Update menu configuration file
    """
    try:
        config_path = Path(current_app.config['CONFIG_DIR']) / 'menu_config.json'
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(new_config, f, indent=2, ensure_ascii=False)
        
        return True
        
    except Exception as e:
        current_app.logger.error(f"Error updating menu configuration: {e}")
        return False
