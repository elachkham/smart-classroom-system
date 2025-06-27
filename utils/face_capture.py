import cv2
import os
import threading
from typing import Callable, Optional
from config.settings import settings

class FaceCapture:
    """Système de capture de visages intégré"""
    
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.is_capturing = False
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
    
    def capture_faces(self, person_name: str, num_images: int = 20) -> bool:
        """Capture de visages - Version de votre code original améliorée"""
        # Créer le dossier pour la personne
        person_path = settings.DATASET_PATH / person_name
        person_path.mkdir(parents=True, exist_ok=True)

        cap = cv2.VideoCapture(settings.CAMERA_INDEX)
        if not cap.isOpened():
            print("Erreur : impossible d'ouvrir la webcam.")
            return False

        print(f"🎯 Capture de {num_images} images pour {person_name}")
        print("📸 Appuyez sur ESPACE pour capturer | Q pour quitter")

        count = 0
        self.is_capturing = True
        
        try:
            while count < num_images and self.is_capturing:
                ret, frame = cap.read()
                if not ret:
                    print("Erreur de capture.")
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

                # Dessiner les rectangles et afficher le compteur
                for (x, y, w, h) in faces:
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                
                # Afficher les informations
                cv2.putText(frame, f"Images: {count}/{num_images}", (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                cv2.putText(frame, "ESPACE = Capturer | Q = Quitter", (10, 70),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

                cv2.imshow(f"Webcam - {person_name} - Appuie sur [ESPACE] pour capturer | [Q] pour quitter", frame)
                key = cv2.waitKey(1)

                if key == ord(' '):  # ESPACE
                    if len(faces) == 0:
                        print("⚠️ Aucun visage détecté.")
                        continue

                    for (x, y, w, h) in faces:
                        face_img = frame[y:y+h, x:x+w]
                        face_img = cv2.resize(face_img, (224, 224))  # Taille compatible DeepFace
                        img_path = person_path / f"{person_name}_{count + 1}.jpg"
                        cv2.imwrite(str(img_path), face_img)
                        print(f"✅ Image sauvegardée : {img_path}")
                        count += 1
                        
                        # Callback pour notifier l'interface web
                        if self.callback:
                            self.callback({
                                'type': 'capture_progress',
                                'student': person_name,
                                'count': count,
                                'total': num_images
                            })
                        break  # Une seule capture par pression

                elif key == ord('q') or key == 27:
                    print("🛑 Capture interrompue.")
                    break

        except Exception as e:
            print(f"❌ Erreur durant la capture: {e}")
            return False
            
        finally:
            cap.release()
            cv2.destroyAllWindows()
            self.is_capturing = False

        print("✅ Capture terminée.")
        return count >= num_images
    
    def stop_capture(self):
        """Arrêter la capture en cours"""
        self.is_capturing = False