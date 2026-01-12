"""
Fase 3: Actualización de Base de Datos
Actualiza pdf_volante_path para competencias con matches encontrados
"""
import sqlite3
import json
from pathlib import Path

def update_missing_pdf_paths():
    print(f"\n{'='*80}")
    print("FASE 3: Actualización de Base de Datos")
    print(f"{'='*80}\n")
    
    # Cargar matches
    try:
        with open('matches_found.json', 'r', encoding='utf-8') as f:
            matches = json.load(f)
        print(f"✓ Matches cargados: {len(matches)}\n")
    except FileNotFoundError:
        print("❌ Error: Ejecuta primero phase2_match_competitions_to_pdfs.py")
        return
    
    if len(matches) == 0:
        print("⚠ No hay matches para actualizar")
        return
    
    # Conectar BD
    conn = sqlite3.connect('data/database.db')
    cursor = conn.cursor()
    
    updated_count = 0
    skipped_count = 0
    
    print("Actualizando competencias...\n")
    
    for match in matches:
        comp_id = match['comp_id']
        comp_name = match['comp_name']
        pdf_path = match['pdf_path']
        
        # Verificar que PDF existe
        if not Path(pdf_path).exists():
            print(f"⚠ ID {comp_id:3} | {comp_name:20} → PDF no existe: {pdf_path}")
            skipped_count += 1
            continue
        
        # Actualizar BD
        cursor.execute(
            "UPDATE competitions SET pdf_volante_path = ? WHERE id = ?",
            (pdf_path, comp_id)
        )
        
        updated_count += 1
        print(f"✓ ID {comp_id:3} | {comp_name:20} → {Path(pdf_path).name}")
    
    # Confirmar
    conn.commit()
    conn.close()
    
    print(f"\n{'='*80}")
    print("Resumen de actualización:")
    print(f"  ✓ Actualizados: {updated_count}")
    print(f"  ⚠ Omitidos (PDF no existe): {skipped_count}")
    print(f"  Total procesados: {len(matches)}")
    print(f"{'='*80}\n")
    
    if updated_count > 0:
        print("✅ Base de datos actualizada exitosamente")
        print("💡 Recarga la página de competencias para ver los iconos de PDF\n")
    
    return updated_count

if __name__ == '__main__':
    update_missing_pdf_paths()
