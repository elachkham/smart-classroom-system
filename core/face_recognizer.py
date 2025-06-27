import cv2
import os
import numpy as np
from deepface import DeepFace
from typing import Tuple, Optional, List
from config.settings import settings
from data.database import FileSystemDatabase

class FaceRecognizer:
    """Système de reconnaissance faciale basé sur filesystem"""
    
    def __init__(self):
        self.model_name = settings.RECOGNITION_MODEL
        self.threshold_score = settings.RECOGNITION_THRESHOLD
        self.db_path = str(settings.DATASET_PATH)
        self.database = FileSystemDatabase()
    
    def recognize_face(self, face_img: np.ndarray) -> Tuple[str, float]:
         """Reconnaître un visage avec gestion améliorée des erreurs"""
         try:
             # Vérifier qu'il y a des étudiants dans la base
             students = self.database.get_all_students()
             if not students:
                 return "Base_vide", 0
             
             # Vérifier que le dossier dataset existe et contient des fichiers
             if not os.path.exists(self.db_path) or not os.listdir(self.db_path):
                 return "Base_vide", 0
             
             # Compter le nombre total d'images
             total_images = sum(len(os.listdir(os.path.join(self.db_path, student_dir))) 
                               for student_dir in os.listdir(self.db_path) 
                               if os.path.isdir(os.path.join(self.db_path, student_dir)))
             
             if total_images == 0:
                 return "Base_vide", 0
             
             results = DeepFace.find(
                 img_path=face_img,
                 db_path=self.db_path,
                 model_name=self.model_name,
                 enforce_detection=False
             )
             
             if results and len(results) > 0:
                 df = results[0]
                 if not df.empty:
                     df = df.sort_values(by="distance", ascending=True).reset_index(drop=True)
                     best = df.iloc[0]
                     identity_path = best["identity"]
                     distance = best["distance"]
                     threshold = best.get("threshold", 0.4)
                     score = (1 - distance / threshold) * 100
                     
                     if score >= self.threshold_score:
                         # Extraire le nom du dossier parent
                         name = os.path.basename(os.path.dirname(identity_path))
                         return name, score
             
             return "Inconnu", 0
             
         except Exception as e:
             # Gestion plus spécifique des erreurs
             error_msg = str(e).lower()
             if "no item found" in error_msg or "empty" in error_msg:
                 return "Base_vide", 0
             else:
                 print(f"Erreur reconnaissance: {e}")
                 return "Erreur", 0
    
    def get_students_list(self) -> List[str]:
        """Obtenir la liste des étudiants"""
        students = self.database.get_all_students()
        return [student['name'] for student in students]
    
    def get_student_details(self, student_name: str) -> Optional[dict]:
        """Obtenir les détails d'un étudiant"""
        return self.database.get_student_info(student_name)
    
    def delete_student(self, student_name: str) -> bool:
        """Supprimer un étudiant"""
        return self.database.delete_student(student_name)
    
    def get_database_stats(self) -> dict:
        """Obtenir les statistiques de la base"""
        return self.database.get_database_stats()