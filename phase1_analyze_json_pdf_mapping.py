"""
Fase 1: Análisis y Mapeo de JSON → PDF
Crea un mapa de todos los JSONs con su metadata y PDFs asociados
"""
import json
from pathlib import Path

def analyze_json_pdf_mapping():
    json_base = Path('data/pdf_scraping/json')
    pdf_base = Path('data/pdf_scraping/pdfs')
    
    mapping = {}
    stats = {
        'total_jsons': 0,
        'with_pdf': 0,
        'without_pdf': 0,
        'by_venue': {}
    }
    
    print(f"\n{'='*80}")
    print("FASE 1: Análisis y Mapeo JSON → PDF")
    print(f"{'='*80}\n")
    
    for recinto_dir in json_base.iterdir():
        if not recinto_dir.is_dir():
            continue
        
        recinto = recinto_dir.name
        venue_count = 0
        
        for json_file in recinto_dir.glob('*.json'):
            stats['total_jsons'] += 1
            venue_count += 1
            
            try:
                # Leer JSON
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Extraer metadata
                fecha = data.get('fecha')
                recinto_json = data.get('recinto', recinto.upper())
                
                # Construir path del PDF
                pdf_name = json_file.stem  # Nombre sin extensión
                pdf_path = pdf_base / recinto / f"{pdf_name}.pdf"
                
                pdf_exists = pdf_path.exists()
                
                if pdf_exists:
                    stats['with_pdf'] += 1
                else:
                    stats['without_pdf'] += 1
                
                # Guardar en mapa
                mapping[str(json_file.relative_to('.'))] = {
                    'recinto': recinto_json,
                    'fecha': fecha,
                    'pdf_path': str(pdf_path).replace('/', '\\'),
                    'pdf_exists': pdf_exists,
                    'json_name': json_file.name
                }
                
            except Exception as e:
                print(f"⚠ Error procesando {json_file.name}: {e}")
        
        stats['by_venue'][recinto.upper()] = venue_count
        print(f"  {recinto.upper()}: {venue_count} JSONs procesados")
    
    # Guardar mapa
    output_file = 'json_pdf_map.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(mapping, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*80}")
    print("Estadísticas:")
    print(f"  Total JSONs: {stats['total_jsons']}")
    print(f"  Con PDF: {stats['with_pdf']} ({stats['with_pdf']/stats['total_jsons']*100:.1f}%)")
    print(f"  Sin PDF: {stats['without_pdf']} ({stats['without_pdf']/stats['total_jsons']*100:.1f}%)")
    print(f"\n  Por recinto:")
    for venue, count in stats['by_venue'].items():
        print(f"    {venue}: {count}")
    print(f"\n✅ Mapa guardado en: {output_file}")
    print(f"{'='*80}\n")
    
    return mapping, stats

if __name__ == '__main__':
    analyze_json_pdf_mapping()
