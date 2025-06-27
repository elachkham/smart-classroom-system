import cv2
import os
import time
import threading
from pathlib import Path
from config.settings import settings

class WebFaceCapture:
    '''Capture de visages intégrée pour l'interface web'''
    
    def __init__(self, camera_manager, face_detector, student_name, num_images=20, callback=None):
        self.camera_manager = camera_manager
        self.face_detector = face_detector
        self.student_name = student_name
        self.num_images = num_images
        self.callback = callback
        
        self.images_captured = 0
        self.is_capturing = False
        self.student_dir = settings.DATASET_PATH / student_name
        
        # Créer le dossier étudiant
        self.student_dir.mkdir(parents=True, exist_ok=True)
        
        # Mode de capture: 'auto' ou 'manual'
        self.capture_mode = 'manual'  # Par défaut manuel pour plus de contrôle
        
    def start_capture(self):
        '''Démarrer la capture'''
        self.is_capturing = True
        self.images_captured = 0
        
        self._update_status({
            'active': True,
            'message': f'Capture démarrée pour {self.student_name}. Appuyez sur "Capturer Image" quand vous êtes prêt.',
            'images_captured': 0
        })
        
        if self.capture_mode == 'auto':
            self._auto_capture_loop()
        else:
            self._manual_capture_mode()
    
    def _manual_capture_mode(self):
        '''Mode capture manuel - attend les déclenchements manuels'''
        self._update_status({
            'message': f'Mode manuel actif. Cliquez sur "Capturer Image" pour prendre une photo ({self.images_captured}/{self.num_images})'
        })
        
        # Garder le thread actif mais en attente
        while self.is_capturing and self.images_captured < self.num_images:
            time.sleep(0.1)
        
        if self.images_captured >= self.num_images:
            self._complete_capture()
    
    def _auto_capture_loop(self):
        '''Mode capture automatique'''
        last_capture_time = 0
        capture_interval = 2.0  # 2 secondes entre chaque capture
        
        while self.is_capturing and self.images_captured < self.num_images:
            try:
                current_time = time.time()
                
                if current_time - last_capture_time >= capture_interval:
                    frame = self.camera_manager.get_frame()
                    
                    if frame is not None:
                        faces = self.face_detector.detect_faces_optimized(frame)
                        
                        if faces:
                            # Prendre le premier visage détecté
                            x, y, w, h = faces[0]
                            face_img = frame[y:y+h, x:x+w]
                            
                            if self._save_face_image(face_img):
                                last_capture_time = current_time
                
                time.sleep(0.1)
                
            except Exception as e:
                self._update_status({
                    'message': f'Erreur durant la capture: {e}'
                })
                break
        
        if self.images_captured >= self.num_images:
            self._complete_capture()
    
    def trigger_manual_capture(self):
        '''Déclencher manuellement une capture'''
        if not self.is_capturing or self.images_captured >= self.num_images:
            return False
        
        try:
            frame = self.camera_manager.get_frame()
            
            if frame is None:
                self._update_status({'message': 'Aucune image disponible de la caméra'})
                return False
            
            # Détecter les visages
            faces = self.face_detector.detect_faces_optimized(frame)
            
            if not faces:
                self._update_status({'message': 'Aucun visage détecté. Positionnez-vous face à la caméra.'})
                return False
            
            # Prendre le visage le plus grand (le plus proche)
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            face_img = frame[y:y+h, x:x+w]
            
            if self._save_face_image(face_img):
                if self.images_captured >= self.num_images:
                    self._complete_capture()
                return True
            
            return False
            
        except Exception as e:
            self._update_status({'message': f'Erreur capture: {e}'})
            return False
    
    def _save_face_image(self, face_img):
        '''Sauvegarder une image de visage'''
        try:
            # Redimensionner pour DeepFace
            face_resized = cv2.resize(face_img, (224, 224))
            
            # Nom du fichier
            img_path = self.student_dir / f'{self.student_name}_{self.images_captured + 1}.jpg'
            
            # Sauvegarder
            success = cv2.imwrite(str(img_path), face_resized)
            
            if success:
                self.images_captured += 1
                self._update_status({
                    'images_captured': self.images_captured,
                    'message': f'Image {self.images_captured}/{self.num_images} capturée avec succès !'
                })
                return True
            else:
                self._update_status({'message': 'Erreur lors de la sauvegarde de l\'image'})
                return False
                
        except Exception as e:
            self._update_status({'message': f'Erreur sauvegarde: {e}'})
            return False
    
    def _complete_capture(self):
        '''Terminer la capture'''
        self.is_capturing = False
        
        self._update_status({
            'active': False,
            'message': f'Capture terminée ! {self.images_captured} images sauvegardées pour {self.student_name}.'
        })
        
        print(f'✅ Capture terminée: {self.images_captured} images pour {self.student_name}')
    
    def stop_capture(self):
        '''Arrêter la capture'''
        self.is_capturing = False
        
        self._update_status({
            'active': False,
            'message': f'Capture arrêtée. {self.images_captured} images sauvegardées.'
        })
    
    def _update_status(self, status_update):
        '''Mettre à jour le statut via callback'''
        if self.callback:
            self.callback(status_update)