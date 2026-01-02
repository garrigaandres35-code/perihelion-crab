"""
PDF Data Models (DTOs)
Pydantic models for structured PDF data extraction via LlamaExtract
"""
from typing import List, Dict, Any
from pydantic import BaseModel, Field


class Race(BaseModel):
    """Represents a single race"""
    numero: int
    opcion: List[int] = Field(min_length=4, max_length=4)
    numero_competidores: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class Meeting(BaseModel):
    """Represents a full race meeting"""
    recinto: str
    fecha: str
    reunion: int
    carreras: List[Race]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "nro_reunion": str(self.reunion),
            "fecha": self.fecha,
            "recinto": self.recinto,
            "carreras": [c.to_dict() for c in self.carreras]
        }

# For backward compatibility with existing code that might use nro_reunion instead of reunion
Meeting.model_rebuild()
