from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

class AttentionStatus(Enum):
    CONCENTRE = "concentre"
    DISTRAIT = "distrait"
    COLLECTE = "collecte"
    INSUFFISANT = "insuffisant"

class EmotionType(Enum):
    HAPPY = "happy"
    SAD = "sad"
    ANGRY = "angry"
    FEAR = "fear"
    SURPRISE = "surprise"
    DISGUST = "disgust"
    NEUTRAL = "neutral"

@dataclass
class Student:
    """Modèle étudiant"""
    name: str
    id: Optional[int] = None
    created_at: Optional[datetime] = None
    image_count: int = 0
    last_seen: Optional[datetime] = None

@dataclass
class AttendanceRecord:
    """Enregistrement de présence"""
    student_name: str
    timestamp: datetime
    has_class: bool
    course: Optional[str] = None
    classroom: Optional[str] = None

@dataclass
class AttentionRecord:
    """Enregistrement d'attention"""
    student_name: str
    timestamp: datetime
    status: AttentionStatus
    std_x: float
    std_y: float

@dataclass
class EmotionRecord:
    """Enregistrement d'émotion"""
    student_name: str
    timestamp: datetime
    emotion: EmotionType
    confidence: float

@dataclass
class AccessRecord:
    """Enregistrement d'accès"""
    timestamp: datetime
    student_name: Optional[str]
    action: str  # "granted", "denied", "manual"
    reason: Optional[str] = None