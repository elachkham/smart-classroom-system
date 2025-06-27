import cv2
import numpy as np
from typing import List, Tuple

class FaceDetector:
    """Détecteur de visages optimisé"""
    
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
    
    def detect_faces(self, frame: np.ndarray, scale_factor: float = 1.3, 
                    min_neighbors: int = 5) -> List[Tuple[int, int, int, int]]:
        """Détecter les visages dans une frame"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(
            gray, 
            scaleFactor=scale_factor, 
            minNeighbors=min_neighbors
        )
        return faces.tolist() if len(faces) > 0 else []
    
    def detect_faces_optimized(self, frame: np.ndarray, 
                             target_width: int = 320) -> List[Tuple[int, int, int, int]]:
        """Détection optimisée avec redimensionnement"""
        h, w = frame.shape[:2]
        scale = w / target_width
        small_h = int(h * target_width / w)
        
        # Redimensionner pour la détection
        small_frame = cv2.resize(frame, (target_width, small_h))
        faces_small = self.detect_faces(small_frame)
        
        # Remettre à l'échelle
        faces_full = []
        for (x, y, w, h) in faces_small:
            faces_full.append((
                int(x * scale),
                int(y * scale),
                int(w * scale),
                int(h * scale)
            ))
        
        return faces_full