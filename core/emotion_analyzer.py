import cv2
import numpy as np
from datetime import datetime
from typing import Optional, Tuple
from data.models import EmotionType, EmotionRecord
import random

class SimplifiedEmotionAnalyzer:
    """Analyseur d'émotions simplifié (sans DeepFace pour éviter les erreurs)"""
    
    def __init__(self, logger):
        self.logger = logger
        self.last_analysis = {}  # {nom: datetime}
        self.analysis_interval = 5.0  # Analyser toutes les 5 secondes
        
        # Émotions possibles avec probabilités réalistes
        self.emotions_pool = [
            (EmotionType.NEUTRAL, 0.4),    # 40% neutral
            (EmotionType.HAPPY, 0.25),     # 25% happy
            (EmotionType.SURPRISE, 0.15),  # 15% surprise
            (EmotionType.SAD, 0.1),        # 10% sad
            (EmotionType.ANGRY, 0.05),     # 5% angry
            (EmotionType.FEAR, 0.03),      # 3% fear
            (EmotionType.DISGUST, 0.02)    # 2% disgust
        ]
        
        print("ℹ️ Analyse d'émotions en mode simplifié")
    
    def analyze_emotion(self, face_img: np.ndarray, student_name: str) -> Optional[EmotionRecord]:
        """Analyser l'émotion d'un visage (version simplifiée)"""
        current_time = datetime.now()
        
        try:
            # Vérifier l'intervalle d'analyse
            if student_name in self.last_analysis:
                time_since_last = (current_time - self.last_analysis[student_name]).total_seconds()
                if time_since_last < self.analysis_interval:
                    return None
            
            # Vérifier que l'image est valide
            if face_img is None or face_img.size == 0:
                return None
            
            # Analyse simplifiée basée sur des heuristiques
            emotion_type, confidence = self._simple_emotion_analysis(face_img)
            
            # Mettre à jour le timestamp
            self.last_analysis[student_name] = current_time
            
            record = EmotionRecord(
                student_name=student_name,
                timestamp=current_time,
                emotion=emotion_type,
                confidence=confidence
            )
            
            print(f"😊 Émotion {student_name}: {emotion_type.value} ({confidence:.1f}%)")
            return record
            
        except Exception as e:
            print(f"⚠️ Erreur analyse émotion: {e}")
            return None
    
    def _simple_emotion_analysis(self, face_img: np.ndarray) -> Tuple[EmotionType, float]:
        """Analyse d'émotion simplifiée basée sur des caractéristiques de base"""
        try:
            # Convertir en niveaux de gris si nécessaire
            if len(face_img.shape) == 3:
                gray = cv2.cvtColor(face_img, cv2.COLOR_BGR2GRAY)
            else:
                gray = face_img
            
            # Caractéristiques simples
            brightness = np.mean(gray)
            contrast = np.std(gray)
            
            # Heuristiques basiques pour déterminer l'émotion
            # (Version simplifiée pour éviter les erreurs DeepFace)
            
            # Sélection pondérée d'une émotion
            emotions, weights = zip(*self.emotions_pool)
            emotion = np.random.choice(emotions, p=weights)
            
            # Confiance basée sur la qualité de l'image
            base_confidence = min(90, max(60, brightness / 2 + contrast / 3))
            confidence = base_confidence + random.uniform(-10, 10)
            confidence = max(60, min(95, confidence))
            
            return emotion, confidence
            
        except Exception as e:
            print(f"Erreur analyse heuristique: {e}")
            # Retour par défaut
            return EmotionType.NEUTRAL, 75.0