"""
Fase 2: Vinculación de Competencias → PDFs
Busca matches entre competencias sin PDF y archivos JSON/PDF
"""
import sqlite3
import json
from pathlib import Path

def match_competitions_to_pdfs():
    print(f"\n{'='*80}")
    print("FASE 2: Vinculación Competencias → PDFs")
    print(f"{'='*80}\n")
    
    # Cargar mapa
    try:
        with open('json_pdf_map.json', 'r', encoding='utf-8') as f:
            json_map = json.load(f)
        print(f"✓ Mapa cargado: {len(json_map)} JSONs")
    except FileNotFoundError:
        print("❌ Error: Ejecuta primero phase1_analyze_json_pdf_mapping.py")
        return
    
    # Conectar BD
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    
    # Obtener competencias sin PDF
    cursor.execute("""
        SELECT c.id, c.name, v.abbreviation, c.event_date
        FROM competitions c
        LEFT JOIN venues v ON c.venue_id = v.id
        WHERE c.status = 'Scraper' AND c.pdf_volante_path IS NULL
        ORDER BY c.event_date DESC
    """)
    
    competitions = cursor.fetchall()
    print(f"✓ Competencias sin PDF: {len(competitions)}\n")
    
    matches_found = []
    matches_multiple = []
    matches_not_found = []
    
    print("Buscando matches...\n")
    
    for comp_id, comp_name, venue, event_date in competitions:
        # Buscar en mapa
        candidates = []
        
        for json_path, metadata in json_map.items():
            if (metadata['recinto'].upper() == venue.upper() and 
                metadata['fecha'] == event_date and
                metadata['pdf_exists']):
                candidates.append({
                    'json_path': json_path,
                    'json_name': metadata['json_name'],
                    'pdf_path': metadata['pdf_path']
                })
        
        if len(candidates) == 1:
            # Match único
            matches_found.append({
                'comp_id': comp_id,
                'comp_name': comp_name,
                'venue': venue,
                'event_date': event_date,
                'pdf_path': candidates[0]['pdf_path'],
                'json_path': candidates[0]['json_path'],
                'json_name': candidates[0]['json_name']
            })
            print(f"✓ ID {comp_id:3} | {comp_name:20} → {Path(candidates[0]['pdf_path']).name}")
            
        elif len(candidates) > 1:
            # Múltiples matches
            matches_multiple.append({
                'comp_id': comp_id,
                'comp_name': comp_name,
                'venue': venue,
                'event_date': event_date,
                'candidates': candidates
            })
            print(f"⚠ ID {comp_id:3} | {comp_name:20} → {len(candidates)} matches (requiere revisión)")
            
        else:
            # No encontrado
            matches_not_found.append({
                'comp_id': comp_id,
                'comp_name': comp_name,
                'venue': venue,
                'event_date': event_date
            })
            print(f"✗ ID {comp_id:3} | {comp_name:20} → No encontrado")
    
    # Guardar resultados
    with open('matches_found.json', 'w', encoding='utf-8') as f:
        json.dump(matches_found, f, indent=2, ensure_ascii=False)
    
    with open('matches_multiple.json', 'w', encoding='utf-8') as f:
        json.dump(matches_multiple, f, indent=2, ensure_ascii=False)
    
    with open('matches_not_found.json', 'w', encoding='utf-8') as f:
        json.dump(matches_not_found, f, indent=2, ensure_ascii=False)
    
    conn.close()
    
    print(f"\n{'='*80}")
    print("Resultados:")
    print(f"  ✓ Matches únicos: {len(matches_found)}")
    print(f"  ⚠ Múltiples matches: {len(matches_multiple)}")
    print(f"  ✗ No encontrados: {len(matches_not_found)}")
    print(f"\nArchivos generados:")
    print(f"  - matches_found.json ({len(matches_found)} registros)")
    print(f"  - matches_multiple.json ({len(matches_multiple)} registros)")
    print(f"  - matches_not_found.json ({len(matches_not_found)} registros)")
    print(f"{'='*80}\n")
    
    return {
        'found': len(matches_found),
        'multiple': len(matches_multiple),
        'not_found': len(matches_not_found)
    }

if __name__ == '__main__':
    match_competitions_to_pdfs()
