"""
CHS Scraper - Club Hípico de Santiago
PDF extractor for CHS race programs
"""
import re
from typing import Optional, List

from app.modules.scraping.extractors.hch import HCHScraper
from app.modules.scraping.pdf_models import Meeting, Race, Participant


class CHSScraper(HCHScraper):
    """PDF Scraper for Club Hípico de Santiago (CHS)"""
    
    # CHS Date format: "VIERNES 21 NOVIEMBRE 2025" (No "de")
    R_DATE = re.compile(rf"{HCHScraper.WEEKDAYS}\s+\d{{1,2}}\s+\w+\s+\d{{4}}", re.IGNORECASE)
    R_REUNION = re.compile(r"RN\s*(\d+)", re.IGNORECASE)

    # CHS Header: "12:30 APROX."
    R_RACE_HEADER = re.compile(r"(?P<hora>\d{1,2}:\d{2})\s*APROX\.", re.IGNORECASE)
    
    # CHS Line 2: "1 1200VARIANTEMTS. PISTA 2 ARENA"
    R_RACE_DETAILS = re.compile(r"^\s*(?P<nro>\d+)\s+(?P<dist>\d+)(?P<resto>.+)", re.IGNORECASE)
    
    # CHS Participant Line: "3 SASSI - Constitution 57"
    R_PARTICIPANT_START = re.compile(r"^\s*(\d{1,2})\s+(.+?)\s+-\s+(.+?)\s+(\d{2,3})", re.IGNORECASE)

    def extract_meeting(self) -> Meeting:
        meeting = super().extract_meeting()
        meeting.recinto = "CHS"
        return meeting

    def _is_participant_start(self, lines, idx):
        if self.R_PARTICIPANT_START.match(lines[idx]):
            return True
        return False

    def _parse_participant_chunk(self, chunk) -> Optional[Participant]:
        line0 = chunk[0].strip()
        m = self.R_PARTICIPANT_START.match(line0)
        if not m: return None
        
        nro = m.group(1)
        caballo = m.group(2).strip()
        peso = m.group(4)
        
        jinete = ""
        preparador = ""
        
        # Search for Jinete - Preparador line
        for line in chunk[1:]:
            if " - " in line and not line[0].isdigit():
                parts = line.split(" - ", 1)
                if len(parts) == 2:
                    jinete = parts[0].strip()
                    preparador = parts[1].strip()
                    break
        
        return Participant(
            numero=nro,
            nombre=caballo,
            jinete=jinete,
            peso=peso,
            preparador=preparador
        )

    def _parse_fecha_to_iso(self, fecha_text):
        if not fecha_text: return None
        meses = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 
                 'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
        
        # Try HCH format first (with "de")
        iso = super()._parse_fecha_to_iso(fecha_text)
        if iso: return iso
        
        # Try CHS format (without "de"): "VIERNES 21 NOVIEMBRE 2025"
        match = re.search(r'(\d{1,2})\s+(\w+)\s+(\d{4})', fecha_text, re.IGNORECASE)
        if match:
            dia, mes_txt, ano = int(match.group(1)), match.group(2).lower(), int(match.group(3))
            mes = meses.get(mes_txt)
            if mes: return f"{ano:04d}-{mes:02d}-{dia:02d}"
        return None

    def _parse_race_block(self, block_lines) -> Optional[Race]:
        if not block_lines: return None
        
        header_line = block_lines[0]
        m_header = self.R_RACE_HEADER.search(header_line)
        if not m_header: return None
        
        race_dict = {
            "hora": m_header.group("hora"),
            "apuestas": [],
            "premios": {},
            "participantes": []
        }
        
        # Extract Opción from header line if present
        m_opc = re.search(r"OPC:\s*([\d\-\s]+)", header_line)
        if m_opc:
            opc_str = m_opc.group(1).strip()
            race_dict["opcion"] = [int(x.strip()) for x in opc_str.split("-") if x.strip().isdigit()]
        else:
            race_dict["opcion"] = []

        # Parse Line 2 for Number and Distance
        if len(block_lines) > 1:
            line2 = block_lines[1]
            m_details = self.R_RACE_DETAILS.search(line2)
            if m_details:
                race_dict["nro_carrera"] = m_details.group("nro")
                race_dict["distancia_m"] = m_details.group("dist")
                race_dict["condicion"] = m_details.group("resto").strip()

        # Code - find numbers in parentheses
        matches_code = re.findall(r"\(([\d\.,]+)\)", header_line)
        if matches_code:
            race_dict["codigo"] = matches_code[-1].replace(".", "")
        
        # Type
        if "HANDICAP" in header_line.upper():
            race_dict["tipo"] = "HANDICAP"
        elif "CONDICIONAL" in header_line.upper():
            race_dict["tipo"] = "CONDICIONAL"
        elif "CLASICO" in header_line.upper():
            race_dict["tipo"] = "CLASICO"
            
        # Extract Premio Name
        m_premio = re.search(r"Pr\.\s+(.+?)\s*\(", header_line, re.IGNORECASE)
        if m_premio:
            race_dict["premio_nombre"] = m_premio.group(1).strip()
        else:
            race_dict["premio_nombre"] = ""

        # Default missing fields
        race_dict["serie"] = ""
        race_dict["peso_categoria_kg"] = ""
        if "codigo" not in race_dict: race_dict["codigo"] = ""
        if "tipo" not in race_dict: race_dict["tipo"] = ""
        if "indice" not in race_dict: race_dict["indice"] = ""
        if "condicion" not in race_dict: race_dict["condicion"] = ""
        if "nro_carrera" not in race_dict: race_dict["nro_carrera"] = ""
        if "distancia_m" not in race_dict: race_dict["distancia_m"] = ""

        # Participants
        idx = 2
        while idx < len(block_lines):
            if self._is_participant_start(block_lines, idx): break
            idx += 1
            
        participants_section = block_lines[idx:]
        
        participant_chunks = self._gather_participant_chunks(participants_section)
        participants = []
        for chunk in participant_chunks:
            p = self._parse_participant_chunk(chunk)
            if p: participants.append(p)
            
        race_dict["participantes"] = participants
        
        return Race(**race_dict)
