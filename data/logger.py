import csv
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from config.settings import settings
from data.models import AttendanceRecord, AttentionRecord, EmotionRecord, AccessRecord

class SmartClassroomLogger:
    """Système de logs centralisé"""
    
    def __init__(self):
        self.logs_dir = settings.LOGS_PATH
        self.logs_dir.mkdir(exist_ok=True)
        
        # Configuration du logging système
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(self.logs_dir / 'system.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger('SmartClassroom')
        
        # Fichiers CSV pour les différents types de données
        self._init_csv_files()
    
    def _init_csv_files(self):
        """Initialiser les fichiers CSV"""
        csv_configs = {
            'attendance.csv': ['timestamp', 'student_name', 'has_class', 'course', 'classroom'],
            'attention.csv': ['timestamp', 'student_name', 'status', 'std_x', 'std_y'],
            'emotions.csv': ['timestamp', 'student_name', 'emotion', 'confidence'],
            'access.csv': ['timestamp', 'student_name', 'action', 'reason']
        }
        
        for filename, fieldnames in csv_configs.items():
            file_path = self.logs_dir / filename
            if not file_path.exists():
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
    
    def log_attendance(self, record: AttendanceRecord):
        """Enregistrer une présence"""
        self._write_csv('attendance.csv', {
            'timestamp': record.timestamp.isoformat(),
            'student_name': record.student_name,
            'has_class': record.has_class,
            'course': record.course,
            'classroom': record.classroom
        })
        self.logger.info(f"Présence: {record.student_name} - {record.course}")
    
    def log_attention(self, record: AttentionRecord):
        """Enregistrer une mesure d'attention - VERSION CORRIGÉE"""
        try:
            self._write_csv('attention.csv', {
                'timestamp': record.timestamp.isoformat(),
                'student_name': record.student_name,
                'status': record.status.value,
                'std_x': f"{record.std_x:.2f}",
                'std_y': f"{record.std_y:.2f}"
            })
            print(f"📝 Log attention écrit: {record.student_name} - {record.status.value}")
        except Exception as e:
            print(f"❌ Erreur écriture log attention: {e}")
    
    def log_emotion(self, record: EmotionRecord):
        """Enregistrer une émotion - VERSION CORRIGÉE"""
        try:
            self._write_csv('emotions.csv', {
                'timestamp': record.timestamp.isoformat(),
                'student_name': record.student_name,
                'emotion': record.emotion.value,
                'confidence': f"{record.confidence:.2f}"
            })
            print(f"📝 Log émotion écrit: {record.student_name} - {record.emotion.value}")
        except Exception as e:
            print(f"❌ Erreur écriture log émotion: {e}")
    
    def log_access(self, record: AccessRecord):
        """Enregistrer un accès"""
        self._write_csv('access.csv', {
            'timestamp': record.timestamp.isoformat(),
            'student_name': record.student_name,
            'action': record.action,
            'reason': record.reason
        })
        self.logger.info(f"Accès: {record.action} - {record.student_name}")
    
    def _write_csv(self, filename: str, data: Dict[str, Any]):
        """Écrire dans un fichier CSV"""
        file_path = self.logs_dir / filename
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            fieldnames = list(data.keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(data)
    
    def get_recent_logs(self, log_type: str, limit: int = 50) -> List[Dict]:
        """Récupérer les logs récents"""
        filename = f"{log_type}.csv"
        file_path = self.logs_dir / filename
        
        if not file_path.exists():
            return []
        
        logs = []
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            logs = list(reader)
        
        return logs[-limit:] if logs else []