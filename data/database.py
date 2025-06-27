import os
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime
from config.settings import settings

class FileSystemDatabase:
    """Base de données basée sur le système de fichiers"""
    
    def __init__(self):
        self.dataset_path = settings.DATASET_PATH
        self.dataset_path.mkdir(parents=True, exist_ok=True)
    
    def get_all_students(self) -> List[Dict]:
        """Obtenir tous les étudiants de la base"""
        students = []
        
        try:
            # Parcourir tous les dossiers dans dataset/
            for student_dir in self.dataset_path.iterdir():
                if student_dir.is_dir():
                    student_info = self.get_student_info(student_dir.name)
                    if student_info:
                        students.append(student_info)
        except Exception as e:
            print(f"Erreur lecture base étudiants: {e}")
        
        return students
    
    def get_student_info(self, student_name: str) -> Optional[Dict]:
        """Obtenir les informations d'un étudiant"""
        student_path = self.dataset_path / student_name
        
        if not student_path.exists() or not student_path.is_dir():
            return None
        
        try:
            # Compter les images
            image_files = [f for f in student_path.iterdir() 
                          if f.suffix.lower() in ['.jpg', '.jpeg', '.png']]
            
            # Obtenir la date de création du dossier
            creation_time = datetime.fromtimestamp(student_path.stat().st_ctime)
            
            # Obtenir la dernière modification (dernière image ajoutée)
            last_modified = creation_time
            if image_files:
                last_modified = max(
                    datetime.fromtimestamp(f.stat().st_mtime) 
                    for f in image_files
                )
            
            return {
                'name': student_name,
                'image_count': len(image_files),
                'created_at': creation_time,
                'last_updated': last_modified,
                'folder_path': str(student_path),
                'images': [f.name for f in image_files]
            }
            
        except Exception as e:
            print(f"Erreur lecture info étudiant {student_name}: {e}")
            return None
    
    def student_exists(self, student_name: str) -> bool:
        """Vérifier si un étudiant existe"""
        student_path = self.dataset_path / student_name
        return student_path.exists() and student_path.is_dir()
    
    def add_student(self, student_name: str) -> bool:
        """Créer le dossier pour un nouvel étudiant"""
        try:
            student_path = self.dataset_path / student_name
            student_path.mkdir(parents=True, exist_ok=True)
            return True
        except Exception as e:
            print(f"Erreur création dossier étudiant {student_name}: {e}")
            return False
    
    def delete_student(self, student_name: str) -> bool:
        """Supprimer un étudiant et toutes ses images"""
        try:
            student_path = self.dataset_path / student_name
            if student_path.exists():
                import shutil
                shutil.rmtree(student_path)
                return True
            return False
        except Exception as e:
            print(f"Erreur suppression étudiant {student_name}: {e}")
            return False
    
    def get_student_images(self, student_name: str) -> List[str]:
        """Obtenir la liste des images d'un étudiant"""
        student_path = self.dataset_path / student_name
        
        if not student_path.exists():
            return []
        
        try:
            image_files = [
                f.name for f in student_path.iterdir() 
                if f.suffix.lower() in ['.jpg', '.jpeg', '.png']
            ]
            return sorted(image_files)
        except Exception as e:
            print(f"Erreur lecture images {student_name}: {e}")
            return []
    
    def get_database_stats(self) -> Dict:
        """Obtenir les statistiques de la base"""
        try:
            students = self.get_all_students()
            total_students = len(students)
            total_images = sum(student['image_count'] for student in students)
            
            # Trouver l'étudiant avec le plus d'images
            best_student = max(students, key=lambda x: x['image_count']) if students else None
            
            return {
                'total_students': total_students,
                'total_images': total_images,
                'average_images_per_student': total_images / total_students if total_students > 0 else 0,
                'best_student': best_student['name'] if best_student else None,
                'best_student_images': best_student['image_count'] if best_student else 0,
                'database_size_mb': self._get_folder_size_mb(),
                'last_updated': max((s['last_updated'] for s in students), default=None)
            }
        except Exception as e:
            print(f"Erreur calcul statistiques: {e}")
            return {}
    
    def _get_folder_size_mb(self) -> float:
        """Calculer la taille du dossier dataset en MB"""
        try:
            total_size = 0
            for dirpath, dirnames, filenames in os.walk(self.dataset_path):
                for filename in filenames:
                    filepath = os.path.join(dirpath, filename)
                    total_size += os.path.getsize(filepath)
            return total_size / (1024 * 1024)  # Convertir en MB
        except Exception as e:
            print(f"Erreur calcul taille: {e}")
            return 0.0