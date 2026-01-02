"""
VSC Scraper - Valparaíso Sporting Club
PDF extractor for VSC race programs
"""
import re
from typing import Optional, List

from app.modules.scraping.extractors.hch import HCHScraper
from app.modules.scraping.pdf_models import Meeting, Race, Participant


class VSCScraper(HCHScraper):
    """PDF Scraper for Valparaíso Sporting Club (VSC)"""
    
    R_HIPODROMO = re.compile(r"Valpara[íi]so\s+Sporting", re.IGNORECASE)
    
    # VSC Participant Line: "22 LE PEINTRE (ARG) - Interaction"
    R_PARTICIPANT_START = re.compile(r"^\s*(\d{1,2})\s+(.+?)\s+-\s+(.+)", re.IGNORECASE)

    def extract_meeting(self) -> Meeting:
        meeting = super().extract_meeting()
        meeting.recinto = "VSC"
        return meeting

    def _is_participant_start(self, lines, idx):
        if self.R_PARTICIPANT_START.match(lines[idx]):
            return True
        return False

    def _parse_participant_chunk(self, chunk) -> Optional[Participant]:
        line0 = chunk[0].strip()
        
        # Try splitting by multiple spaces first
        parts = re.split(r"\s{2,}", line0)
        
        if len(parts) >= 4:
            nro = parts[0].strip()
            
            # Name and Sire
            name_sire = parts[1].strip()
            if " - " in name_sire:
                caballo = name_sire.split(" - ")[0].strip()
            elif "-" in name_sire:
                caballo = name_sire.split("-", 1)[0].strip()
            else:
                caballo = name_sire
            
            remaining_text = "   ".join(parts[2:])
            
            jinete = ""
            preparador = ""
            
            jp_match = re.search(r"([A-Z\.]+\s+[A-Z][a-z]+.*)\s+-\s+([A-Z\.]+\s+[A-Z][a-z]+.*)", remaining_text)
            if jp_match:
                jinete = jp_match.group(1).strip()
                preparador_raw = jp_match.group(2).strip()
                preparador = re.split(r"\s{2,}", preparador_raw)[0].strip()
                
                m_lead_digit = re.match(r"^(\d+)\s+(.+)", jinete)
                if m_lead_digit:
                    jinete = m_lead_digit.group(2).strip()
            
            weight_nums = re.findall(r"\b(\d{2,3})\b", remaining_text)
            peso = weight_nums[0] if weight_nums else ""
            
            stud = ""
            for p in reversed(parts):
                if " - " in p and not any(c.isdigit() for c in p[:5]): 
                    stud_split = p.split(" - ", 1)
                    stud_candidate = stud_split[0].strip()
                    if stud_candidate != jinete and stud_candidate != preparador:
                        stud = stud_candidate
                        break
            
            return Participant(
                numero=nro,
                nombre=caballo,
                jinete=jinete,
                peso=peso,
                preparador=preparador,
                stud=stud
            )

        # Fallback to regex match for multi-line
        m = self.R_PARTICIPANT_START.match(line0)
        if not m: return None
        
        nro = m.group(1)
        caballo = m.group(2).strip()
        
        peso = ""
        if len(chunk) > 1:
            nums = re.findall(r"\d+", chunk[1])
            if nums:
                peso = nums[0]
        
        jinete = ""
        preparador = ""
        stud = ""
        
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
            preparador=preparador,
            stud=stud
        )

    def _split_races(self, lines):
        indices = []
        for i, ln in enumerate(lines):
            if self.R_RACE_HEADER.search(ln):
                start_idx = i
                for offset in range(1, 4):
                    if i - offset >= 0:
                        prev_line = lines[i - offset]
                        if self.R_OPCION_LABEL.search(prev_line):
                            start_idx = i - offset
                            break
                indices.append(start_idx)
        
        blocks = []
        if indices and indices[0] > 0:
            blocks.append((0, lines[0:indices[0]]))
            
        for idx, start in enumerate(indices):
            end = indices[idx + 1] if idx + 1 < len(indices) else len(lines)
            blocks.append((start, lines[start:end]))
            
        return blocks
