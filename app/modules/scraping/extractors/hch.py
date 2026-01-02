"""
HCH Scraper - Hipódromo Chile
PDF extractor for HCH race programs
"""
import re
import fitz
from typing import List, Dict, Any, Tuple, Optional

from app.modules.scraping.extractors.base import BaseScraper
from app.modules.scraping.pdf_models import Meeting, Race, Participant


class HCHScraper(BaseScraper):
    """PDF Scraper for Hipódromo Chile (HCH)"""
    
    # Regex Constants
    WEEKDAYS = r"(Lunes|Martes|Miércoles|Miercoles|Jueves|Viernes|Sábado|Sabado|Domingo)"
    R_DATE = re.compile(rf"{WEEKDAYS}\s+\d{{1,2}}\s+de\s+\w+\s+de\s+\d{{4}}", re.IGNORECASE)
    R_REUNION = re.compile(r"REUNION\s*N[ºo]\s*(\d+)", re.IGNORECASE)
    R_HIPODROMO = re.compile(r"Hip[óo]dromo\s+Chile", re.IGNORECASE)
    
    R_RACE_HEADER = re.compile(
        r"(?P<hora>\d{1,2}:\d{2})\s*aprox\.?\s*(?P<dist>[\d\.\s]+)\s*Mts\.?\s*\((?P<codigo>[\d\.,]+)\)\s*(?P<resto>.+)",
        re.IGNORECASE
    )

    R_PESO = re.compile(r"Peso:\s*(\d{2,3})\s*Kilos", re.IGNORECASE)
    R_APUESTAS = re.compile(r"APUESTAS\s+DISP(?:ONIBLES)?\s*[:\-]\s*(.+)", re.IGNORECASE)
    R_PREMIO_NOMBRE = re.compile(r"PREMIO\s*[:\-]\s*(.+)", re.IGNORECASE)
    R_PREMIOS_ANY = re.compile(
        r"PREMIOS\s*[:\-].*?\$([\d\.,]+).*?\$([\d\.,]+).*?\$([\d\.,]+).*?\$([\d\.,]+)",
        re.IGNORECASE | re.DOTALL
    )
    R_OPCION_LABEL = re.compile(r"O[pc]ci[óo]n", re.IGNORECASE)
    R_TIEMPO_LINE = re.compile(r"^\d{1,2}\.\d{2}\.\d{2}$")
    R_DIVIDENDO_LINE = re.compile(r"^\d{1,3}(?:[.,]\d{1,2})$")
    
    APUESTA_NORMALIZATION = {
        "GDOR": "Ganador", "GANADOR": "Ganador",
        "A 2°": "A Segundo", "A 2º": "A Segundo", "A SEGUNDO": "A Segundo",
        "A 3°": "A Tercero", "A 3º": "A Tercero", "A TERCERO": "A Tercero",
        "QLA": "Quinela", "QUINELA": "Quinela",
        "QLA-PLA": "Quinela-Place", "QUINELA-PLACE": "Quinela-Place",
        "EXAC": "Exacta", "EXACTA": "Exacta",
        "TRIF": "Trifecta", "TRIFECTA": "Trifecta",
        "SUP": "Superfecta", "SUPERFECTA": "Superfecta",
    }

    def extract_meeting(self) -> Meeting:
        lines = self._extract_text_lines()
        meeting_markers = self._find_meeting_markers(lines)
        
        start_line, _ = meeting_markers[0]
        end_line = meeting_markers[1][0] if len(meeting_markers) > 1 else len(lines)
        
        header_slice_start = max(0, start_line - 100)
        header_slice_end = min(len(lines), end_line + 50)
        
        header_data = self._parse_header(lines, header_slice_start, header_slice_end)
        
        races_blocks = self._split_races(lines)
        carreras = []
        
        range_start = 0
        range_end = end_line
        
        race_1_participants = []
        
        for block_start, blk in races_blocks:
            if block_start >= range_start and block_start < range_end:
                race_data = self._parse_race_block(blk)
                if race_data:
                    carreras.append(race_data)
                else:
                    chunks = self._gather_participant_chunks(blk)
                    if chunks:
                        parts = []
                        for chunk in chunks:
                            p = self._parse_participant_chunk(chunk)
                            if p: parts.append(p)
                        if parts:
                            race_1_participants = parts
                            
        carreras.sort(key=lambda x: x.hora)
        
        if race_1_participants and carreras:
            carreras[0].participantes = race_1_participants
            
        for idx, race in enumerate(carreras):
            race.nro_carrera = str(idx + 1)
            
        return Meeting(
            nro_reunion=str(header_data.get("nro_reunion", "")),
            fecha=header_data.get("fecha", ""),
            recinto="HCH",
            carreras=carreras
        )

    def _extract_text_lines(self) -> List[str]:
        doc = fitz.open(self.pdf_path)
        lines = []
        for page in doc:
            text = page.get_text("text", sort=True)
            for ln in text.splitlines():
                ln = ln.rstrip()
                if ln: lines.append(ln)
        doc.close()
        return lines

    def _find_meeting_markers(self, lines):
        markers = []
        for idx, ln in enumerate(lines):
            m = self.R_DATE.search(ln)
            if m: markers.append((idx, m.group(0)))
        if not markers: markers.append((0, None))
        return markers

    def _parse_header(self, lines, start_idx, end_idx):
        subset = lines[start_idx:end_idx]
        text = "\n".join(subset)
        fecha_m = self.R_DATE.search(text)
        reunion_m = self.R_REUNION.search(text)
        
        fecha_iso = self._parse_fecha_to_iso(fecha_m.group(0)) if fecha_m else None
        
        return {
            "nro_reunion": self._to_int(reunion_m.group(1)) if reunion_m else None,
            "fecha": fecha_iso
        }

    def _split_races(self, lines):
        indices = []
        for i, ln in enumerate(lines):
            if self.R_RACE_HEADER.search(ln):
                indices.append(i)
        blocks = []
        if indices and indices[0] > 0:
            blocks.append((0, lines[0:indices[0]]))
        for idx, start in enumerate(indices):
            end = indices[idx + 1] if idx + 1 < len(indices) else len(lines)
            blocks.append((start, lines[start:end]))
        return blocks

    def _parse_race_block(self, block_lines) -> Optional[Race]:
        header_idx = -1
        for i in range(min(5, len(block_lines))):
            if self.R_RACE_HEADER.search(block_lines[i]):
                header_idx = i
                break
        
        if header_idx == -1: return None
        
        header_line = block_lines[header_idx]
        m = self.R_RACE_HEADER.search(header_line)
        
        race_dict = {
            "hora": m.group("hora"),
            "distancia_m": str(self._to_int(m.group("dist"))),
            "codigo": m.group("codigo").replace(".", ""),
            "apuestas": [],
            "premios": {},
            "participantes": []
        }
        
        resto = m.group("resto").strip()
        resto_parts = re.split(r"\bPeso:", resto, flags=re.IGNORECASE)
        resto = resto_parts[0].strip()
        
        # Tipo
        tipo_match = re.match(r"^(HANDICAP|CLASICO CONDICIONAL|CLASICO|CONDICIONAL)", resto, re.IGNORECASE)
        race_dict["tipo"] = tipo_match.group(1).upper() if tipo_match else ""
        if race_dict["tipo"]: resto = resto[len(race_dict["tipo"]):].strip()
        
        # Serie
        match_serie_ordinal = re.search(r"\b(\d+)(?:ta|da|ra|to|do|ro|ma|a)\.?\s*Serie", resto, re.IGNORECASE)
        if match_serie_ordinal:
            if race_dict["tipo"] == "HANDICAP":
                race_dict["serie"] = match_serie_ordinal.group(1)
            serie_full_text = match_serie_ordinal.group(0).strip()
            resto = resto.replace(serie_full_text, "").strip()
        else:
            match_serie_plain = re.search(r"\b(Serie\s+Indice.*|Serie\s+[A-Z0-9]+.*)", resto, re.IGNORECASE)
            if match_serie_plain:
                resto = resto[:match_serie_plain.start()].strip()
            else:
                match_serie_code = re.search(r"\b(SERIE[- ]?[A-Z0-9]+)\b", resto, re.IGNORECASE)
                if match_serie_code:
                    resto = resto.replace(match_serie_code.group(1), "").strip(" .")

        # Indice
        if race_dict["tipo"] == "HANDICAP":
            match_indice = re.search(r"Indice:\s*([^\n]+?)(?=\s*$)", resto, re.IGNORECASE)
            if match_indice:
                race_dict["indice"] = match_indice.group(1).strip()
                resto = resto.replace(match_indice.group(0), "").strip()
        
        race_dict["condicion"] = resto if resto else ""
        
        pre_header_lines = block_lines[:header_idx]
        
        meta_lines = []
        idx = header_idx + 1
        while idx < len(block_lines):
            if self._is_participant_start(block_lines, idx): break
            meta_lines.append(block_lines[idx])
            idx += 1
            
        participants_section = block_lines[idx:]
        
        all_meta_lines = pre_header_lines + [header_line] + meta_lines
        meta_text = " ".join(all_meta_lines)
        
        peso_m = self.R_PESO.search(meta_text)
        race_dict["peso_categoria_kg"] = str(self._to_int(peso_m.group(1))) if peso_m else ""
        
        race_dict["apuestas"] = self._extract_apuestas(meta_text)
        
        premio_nom_m = self.R_PREMIO_NOMBRE.search(meta_text)
        if premio_nom_m:
            premio_raw = premio_nom_m.group(1).strip()
            race_dict["premio_nombre"] = re.split(r"\bPREMIOS\b", premio_raw, 1)[0].strip(" -:")
        else:
            race_dict["premio_nombre"] = ""

        premios_m = self.R_PREMIOS_ANY.search(meta_text)
        if premios_m:
            race_dict["premios"] = {
                "1o": str(self._to_int(premios_m.group(1))),
                "2o": str(self._to_int(premios_m.group(2))),
                "3o": str(self._to_int(premios_m.group(3))),
                "4o": str(self._to_int(premios_m.group(4))),
            }
            
        race_dict["opcion"] = self._extract_opcion(all_meta_lines)
        
        participant_chunks = self._gather_participant_chunks(participants_section)
        participants = []
        for chunk in participant_chunks:
            p = self._parse_participant_chunk(chunk)
            if p: participants.append(p)
        
        return Race(
            nro_carrera="",
            hora=race_dict["hora"],
            distancia_m=race_dict["distancia_m"],
            codigo=race_dict["codigo"],
            tipo=race_dict.get("tipo", ""),
            condicion=race_dict.get("condicion", ""),
            serie=race_dict.get("serie", ""),
            indice=race_dict.get("indice", ""),
            peso_categoria_kg=race_dict.get("peso_categoria_kg", ""),
            apuestas=race_dict["apuestas"],
            premio_nombre=race_dict.get("premio_nombre", ""),
            premios=race_dict.get("premios", {}),
            opcion=race_dict["opcion"],
            participantes=participants
        )

    def _is_participant_start(self, lines, idx):
        if idx >= len(lines): return False
        line = lines[idx].strip()
        
        if line.isdigit():
            if int(line) > 30: return False
            if idx + 1 < len(lines) and " - " in lines[idx+1]:
                return True
            return False
            
        if re.match(r"^\d{1,2}\s+.+\s+-\s+", line):
            return True
            
        return False

    def _gather_participant_chunks(self, lines):
        chunks = []
        current_chunk = []
        i = 0
        while i < len(lines):
            if self._is_participant_start(lines, i):
                if current_chunk: chunks.append(current_chunk)
                current_chunk = []
                current_chunk.append(lines[i])
                i += 1
            else:
                if current_chunk is not None: current_chunk.append(lines[i])
                i += 1
        if current_chunk: chunks.append(current_chunk)
        return chunks

    def _parse_participant_chunk(self, chunk) -> Optional[Participant]:
        if not chunk: return None
        
        line0 = chunk[0].strip()
        
        if "   " in line0:
            parts = re.split(r"\s{2,}", line0)
            if len(parts) >= 6 and parts[0].isdigit():
                nro = parts[0]
                nombre = parts[1].split(" - ")[0]
                peso = parts[2]
                
                jinete = preparador = ""
                for p in parts[3:]:
                    if "-" in p and not p[0].isdigit() and len(p) > 5:
                        jp_split = p.split("-", 1)
                        jinete = jp_split[0].strip()
                        preparador = jp_split[1].strip().rstrip(".")
                        break
                
                stud_full = parts[-1]
                stud = stud_full.split(" - ")[0]
                
                return Participant(
                    numero=nro,
                    nombre=nombre,
                    jinete=jinete,
                    peso=peso,
                    preparador=preparador,
                    stud=stud
                )

        nro = ""
        nombre_line = ""
        idx_param = 0
        
        if line0.isdigit():
            if len(chunk) < 2: return None
            nro = line0
            nombre_line = chunk[1].strip()
            idx_param = 2
        else:
            m = re.match(r"^(\d{1,2})\s+(.+)", line0)
            if not m: return None
            nro = m.group(1)
            nombre_line = m.group(2).strip()
            idx_param = 1

        caballo = nombre_line.split(" - ")[0].strip() if " - " in nombre_line else nombre_line
        
        numbers, idx_param = self._extract_numeric_sequence(chunk, idx_param)
        
        peso = str(numbers[0]) if len(numbers) > 0 else ""
        
        jinete = preparador = stud = ""
        if idx_param < len(chunk):
            jp_line = chunk[idx_param].strip()
            if "-" in jp_line:
                parts = jp_line.split("-", 1)
                jinete = parts[0].strip()
                preparador = parts[1].strip().rstrip(".")
            else:
                jinete = jp_line
            
            if idx_param + 1 < len(chunk):
                stud_candidate = chunk[idx_param + 1].strip()
                perf_match = re.match(r"^[\d\-\s\*]+-(.+)", stud_candidate)
                if perf_match:
                    stud = perf_match.group(1).strip()
                else:
                    if not re.match(r"^[\d\s\-\.]+$", stud_candidate):
                        stud = stud_candidate

        return Participant(
            numero=nro,
            nombre=caballo,
            jinete=jinete,
            peso=peso,
            preparador=preparador,
            stud=stud
        )

    def _extract_numeric_sequence(self, lines, start_idx):
        numbers = []
        idx = start_idx
        while idx < len(lines):
            line = lines[idx].replace("\t", " ").strip()
            if not line:
                idx += 1
                continue
            if re.search(r"[A-Za-zÁÉÍÓÚÑ]", line): break
            tokens = re.findall(r"\d+", line)
            if tokens:
                numbers.extend(int(t) for t in tokens)
                idx += 1
                if len(numbers) >= 3: break
                continue
            idx += 1
        return numbers, idx

    def _extract_apuestas(self, meta_text):
        apuestas = []
        apuestas_m = self.R_APUESTAS.search(meta_text)
        if not apuestas_m: return apuestas
        apuestas_text = apuestas_m.group(1)
        apuestas_text = re.split(r"\bPREMIO\b", apuestas_text, 1)[0]
        piezas = re.split(r"[;,]", apuestas_text)
        for pieza in piezas:
            apuesta = self._normalize_apuesta(pieza)
            if apuesta: apuestas.append(apuesta)
        return apuestas

    def _normalize_apuesta(self, token):
        if not token: return None
        cleaned = token.strip().replace("º", "°").upper()
        if cleaned in self.APUESTA_NORMALIZATION: return self.APUESTA_NORMALIZATION[cleaned]
        return cleaned

    def _extract_opcion(self, meta_lines):
        for line in meta_lines:
            m = self.R_OPCION_LABEL.search(line)
            if m:
                after_opcion = line[m.end():]
                return [int(x) for x in re.findall(r"\d+", after_opcion)[:4]]
        return []

    def _parse_fecha_to_iso(self, fecha_text):
        if not fecha_text: return None
        meses = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 
                 'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}
        match = re.search(r'(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})', fecha_text, re.IGNORECASE)
        if match:
            dia, mes_txt, ano = int(match.group(1)), match.group(2).lower(), int(match.group(3))
            mes = meses.get(mes_txt)
            if mes: return f"{ano:04d}-{mes:02d}-{dia:02d}"
        return None

    def _to_int(self, s):
        if s is None: return None
        return int(re.sub(r"[^\d]", "", s)) if re.search(r"\d", s) else None
