from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AuditContext(BaseModel):
    audit_id: str
    target_domain: str
    overall_score: float = Field(default=0.0, ge=0.0, le=100.0)
    risk_level: RiskLevel = RiskLevel.LOW
    timestamp: datetime = Field(default_factory=datetime.utcnow)