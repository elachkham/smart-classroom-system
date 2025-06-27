import pandas as pd
from datetime import datetime, time
from typing import Optional, Tuple
from config.settings import settings

class ScheduleManager:
    """Gestionnaire d'emploi du temps"""
    
    def __init__(self):
        self.schedule_df = None
        self.load_schedule()
    
    def load_schedule(self):
        """Charger l'emploi du temps depuis le CSV"""
        try:
            if settings.EDT_PATH.exists():
                self.schedule_df = pd.read_csv(settings.EDT_PATH)
        except Exception as e:
            print(f"Erreur chargement EDT: {e}")
            self.schedule_df = None
    
    def check_student_schedule(self, student_name: str) -> Tuple[Optional[str], Optional[str]]:
        """Vérifier si un étudiant a cours maintenant"""
        if self.schedule_df is None:
            return None, None
        
        now = datetime.now()
        current_date = now.strftime("%Y-%m-%d")
        current_time = now.strftime("%H:%M")
        
        try:
            student_courses = self.schedule_df[
                (self.schedule_df['nom'].str.lower() == student_name.lower()) &
                (self.schedule_df['date'] == current_date)
            ]
            
            for _, row in student_courses.iterrows():
                if row['heure_debut'] <= current_time <= row['heure_fin']:
                    return row['cours'], row['salle']
                    
        except Exception as e:
            print(f"Erreur vérification EDT: {e}")
        
        return None, None

class ImageProcessor:
    """Utilitaires de traitement d'image"""
    
    @staticmethod
    def resize_face(face_img, target_size=(224, 224)):
        """Redimensionner un visage"""
        import cv2
        return cv2.resize(face_img, target_size)
    
    @staticmethod
    def enhance_image(image):
        """Améliorer la qualité d'une image"""
        import cv2
        # Égalisation d'histogramme
        if len(image.shape) == 3:
            # Image couleur
            yuv = cv2.cvtColor(image, cv2.COLOR_BGR2YUV)
            yuv[:,:,0] = cv2.equalizeHist(yuv[:,:,0])
            return cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)
        else:
            # Image en niveaux de gris
            return cv2.equalizeHist(image)