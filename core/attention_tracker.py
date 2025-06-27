import cv2
import numpy as np
import time
from collections import deque
from typing import Dict, List, Optional, Tuple
from data.models import AttentionStatus, AttentionRecord
from datetime import datetime
import random

class SimplifiedAttentionTracker:
    """Système de suivi d'attention simplifié sans trackers OpenCV"""
    
    def __init__(self, logger):
        self.logger = logger
        self.attention_threshold = 15.0
        self.is_calibrated = True  # Toujours calibré
        
        # Historique des visages par nom
        self.face_history = {}  # {nom: {'positions': deque, 'last_status': status}}
        self.window_size = 30
        
        print("ℹ️ Système d'attention en mode simplifié (sans trackers OpenCV)")
    
    def calibrate(self, frame, faces, duration=2.0):
        """Calibration simplifiée"""
        self.is_calibrated = True
        self.attention_threshold = 12.0  # Seuil fixe
        print(f"✅ Calibration attention: seuil = {self.attention_threshold}")
        return True
    
    def update_tracking(self, frame: np.ndarray, new_faces: List[Tuple[int, int, int, int]], 
                       face_names: List[str]) -> List[AttentionRecord]:
        """Mettre à jour le suivi simplifié et retourner les enregistrements"""
        records = []
        current_time = datetime.now()
        
        try:
            for (x, y, w, h), name in zip(new_faces, face_names):
                if name in ["Inconnu", "Erreur", "Base_vide"]:
                    continue
                
                # Initialiser l'historique si nouveau visage
                if name not in self.face_history:
                    self.face_history[name] = {
                        'positions': deque(maxlen=self.window_size),
                        'last_status': AttentionStatus.COLLECTE,
                        'last_update': current_time
                    }
                
                # Ajouter la position actuelle
                center = (x + w//2, y + h//2)
                self.face_history[name]['positions'].append(center)
                
                # Analyser l'attention si assez de données
                if len(self.face_history[name]['positions']) >= 10:
                    status = self._analyze_simple_attention(name)
                    
                    # Générer un log seulement si le statut change ou toutes les 10 secondes
                    time_since_last = (current_time - self.face_history[name]['last_update']).total_seconds()
                    
                    if (status != self.face_history[name]['last_status'] or time_since_last > 10):
                        std_x, std_y = self._calculate_movement_stats(name)
                        
                        record = AttentionRecord(
                            student_name=name,
                            timestamp=current_time,
                            status=status,
                            std_x=std_x,
                            std_y=std_y
                        )
                        records.append(record)
                        
                        self.face_history[name]['last_status'] = status
                        self.face_history[name]['last_update'] = current_time
                        
                        print(f"📊 Attention {name}: {status.value} (std_x:{std_x:.1f}, std_y:{std_y:.1f})")
        
        except Exception as e:
            print(f"⚠️ Erreur suivi attention: {e}")
        
        return records
    
    def _analyze_simple_attention(self, name: str) -> AttentionStatus:
        """Analyser l'attention de manière simplifiée"""
        if name not in self.face_history:
            return AttentionStatus.COLLECTE
        
        positions = list(self.face_history[name]['positions'])
        if len(positions) < 10:
            return AttentionStatus.COLLECTE
        
        # Calculer la variation de mouvement
        recent_positions = positions[-10:]  # 10 dernières positions
        
        if len(recent_positions) < 5:
            return AttentionStatus.INSUFFISANT
        
        # Calculer l'écart-type des mouvements
        x_coords = [pos[0] for pos in recent_positions]
        y_coords = [pos[1] for pos in recent_positions]
        
        std_x = np.std(x_coords) if len(x_coords) > 1 else 0
        std_y = np.std(y_coords) if len(y_coords) > 1 else 0
        
        # Critères d'attention basés sur le mouvement
        movement_score = max(std_x, std_y)
        
        if movement_score > self.attention_threshold:
            return AttentionStatus.DISTRAIT
        else:
            return AttentionStatus.CONCENTRE
    
    def _calculate_movement_stats(self, name: str) -> Tuple[float, float]:
        """Calculer les statistiques de mouvement"""
        if name not in self.face_history or len(self.face_history[name]['positions']) < 2:
            return 0.0, 0.0
        
        positions = list(self.face_history[name]['positions'])
        x_coords = [pos[0] for pos in positions]
        y_coords = [pos[1] for pos in positions]
        
        std_x = float(np.std(x_coords)) if len(x_coords) > 1 else 0.0
        std_y = float(np.std(y_coords)) if len(y_coords) > 1 else 0.0
        
        return std_x, std_y
    
    def get_current_status(self) -> Dict[str, AttentionStatus]:
        """Obtenir le statut actuel de tous les visages suivis"""
        result = {}
        for name, data in self.face_history.items():
            result[name] = data['last_status']
        return result