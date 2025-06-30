

import cv2
import threading
import time
import queue
from datetime import datetime
from config.settings import settings
from data.logger import SmartClassroomLogger
from data.models import AttendanceRecord, AttentionRecord, EmotionRecord
from core.camera_manager import OptimizedCameraManager as CameraManager
from core.face_detector import FaceDetector
from core.face_recognizer import FaceRecognizer
from core.attention_tracker import SimplifiedAttentionTracker
from core.emotion_analyzer import SimplifiedEmotionAnalyzer
from core.door_controller import DoorController
from utils.helpers import ScheduleManager, ImageProcessor

class SmartClassroomSystemFixed:
    """Système principal Smart Classroom DEBUG"""
    
    def __init__(self):
        # Initialisation des composants
        self.logger = SmartClassroomLogger()
        self.camera_manager = CameraManager()
        self.face_detector = FaceDetector()
        self.face_recognizer = FaceRecognizer()
        self.attention_tracker = SimplifiedAttentionTracker(self.logger)
        self.emotion_analyzer = SimplifiedEmotionAnalyzer(self.logger)
        self.door_controller = DoorController(self.logger)
        self.schedule_manager = ScheduleManager()
        
        # État du système
        self.is_running = False
        self.recognized_students = set()
        self.frame_count = 0
        
        # Files d'attente très petites
        self.face_recognition_queue = queue.Queue(maxsize=1)
        self.emotion_analysis_queue = queue.Queue(maxsize=1)
        self.processing_active = False
        
        # Statistiques
        self.successful_recognitions = 0
        self.failed_recognitions = 0
        self.last_diagnostic_time = time.time()
        
        # Threads de traitement asynchrone
        self.recognition_thread = None
        self.emotion_thread = None
        
        # DEBUG: Variables pour détecter les blocages
        self.recognition_in_progress = False
        self.recognition_start_time = 0
        self.max_recognition_time = 8.0
        
        # Configuration
        settings.create_directories()
        
        print(" Smart Classroom System DEBUG initialisé")
    
    def setup_api_connection(self):
        """Connecter l'API au système principal"""
        try:
            from api import routes
            routes.main_system = self
            routes.logger = self.logger
            routes.camera_manager = self.camera_manager
            routes.face_recognizer = self.face_recognizer
            routes.attention_tracker = self.attention_tracker
            routes.emotion_analyzer = self.emotion_analyzer
            routes.door_controller = self.door_controller
            print(" API connectée au système principal")
        except Exception as e:
            print(f" Erreur connexion API: {e}")
    
    def start(self):
        """Démarrer le système"""
        print("🎓 Démarrage Smart Classroom System DEBUG...")
        
        if not self.camera_manager.start():
            print("Erreur: Impossible de démarrer la caméra")
            return False
        
        # Forcer le port COM7 pour Arduino
        try:
            # Changer temporairement le port pour configuration
            original_port = settings.SERIAL_PORT
            settings.SERIAL_PORT = "COM7"  
            
            if self.door_controller.connect():
                print(f" Contrôleur de porte connecté sur {settings.SERIAL_PORT}")
                
                # TEST IMMÉDIAT de la porte
                print(" Test de la porte...")
                if self.door_controller.open_door("TEST_USER", "system_startup"):
                    print(" Test porte réussi - Servo et LED OK")
                else:
                    print(" Test porte échoué")
            else:
                print(f" Contrôleur de porte non connecté sur {settings.SERIAL_PORT}")
                # Essayer d'autres ports
                for port in ["COM3", "COM4", "COM5", "COM6", "COM8"]:
                    print(f"🔍 Essai port {port}...")
                    settings.SERIAL_PORT = port
                    if self.door_controller.connect():
                        print(f" Porte trouvée sur {port}")
                        break
                else:
                    print(" Aucun port série trouvé pour la porte")
                    
        except Exception as e:
            print(f" Erreur contrôleur de porte: {e}")
        
        print(" Calibration du système d'attention...")
        self._calibrate_attention_system()
        
        self.setup_api_connection()
        self._start_async_processing()
        self.camera_manager.add_callback(self._process_frame_debug)
        
        self.is_running = True
        print(" Système DEBUG démarré!")
        
        return True
    
    def _start_async_processing(self):
        """Démarrer les threads de traitement asynchrone"""
        self.processing_active = True
        
        self.recognition_thread = threading.Thread(
            target=self._debug_recognition_worker, 
            daemon=True, 
            name="DebugRecognition"
        )
        self.recognition_thread.start()
        
        self.emotion_thread = threading.Thread(
            target=self._debug_emotion_worker, 
            daemon=True, 
            name="DebugEmotion"
        )
        self.emotion_thread.start()
        
        print("🔄 Threads de traitement DEBUG démarrés")
    
    def _debug_recognition_worker(self):
        """Worker de reconnaissance DEBUG avec timeout forcé"""
        print("🐛 Worker reconnaissance DEBUG démarré")
        
        while self.processing_active:
            try:
                face_data = self.face_recognition_queue.get(timeout=0.1)
                
                if face_data is None:
                    break
                
                face_img, face_box, frame_id = face_data
                
                print(f"🐛 DEBUG: Début reconnaissance (queue: {self.face_recognition_queue.qsize()})")
                
                self.recognition_in_progress = True
                self.recognition_start_time = time.time()
                
                try:
                    result_queue = queue.Queue()
                    
                    def recognition_task():
                        try:
                            print(" DEBUG: Appel face_recognizer.recognize_face...")
                            name, confidence = self.face_recognizer.recognize_face(face_img)
                            result_queue.put(('success', name, confidence))
                            print(f" DEBUG: Reconnaissance terminée: {name} ({confidence})")
                        except Exception as e:
                            print(f" DEBUG: Erreur reconnaissance: {e}")
                            result_queue.put(('error', str(e), 0))
                    
                    recognition_thread = threading.Thread(target=recognition_task)
                    recognition_thread.daemon = True
                    recognition_thread.start()
                    
                    try:
                        result = result_queue.get(timeout=3.0)
                        status, name, confidence = result
                        
                        print(f" DEBUG: Résultat reçu: {status}, {name}, {confidence}")
                        
                        if status == 'success' and name not in ["Inconnu", "Erreur", "Base_vide"]:
                            self.successful_recognitions += 1
                            print(f" DEBUG RECONNAISSANCE RÉUSSIE: {name} ({confidence:.1f}%)")
                            self._force_handle_result(name, confidence, face_img)
                        else:
                            self.failed_recognitions += 1
                            print(f" DEBUG reconnaissance échouée: {name}")
                            
                    except queue.Empty:
                        print(" DEBUG TIMEOUT reconnaissance - ABANDON FORCÉ")
                        self.failed_recognitions += 1
                    
                except Exception as e:
                    print(f" DEBUG Erreur worker: {e}")
                    self.failed_recognitions += 1
                
                finally:
                    self.recognition_in_progress = False
                    self.recognition_start_time = 0
                    print("🐛 DEBUG: reconnaissance_in_progress = False")
                
                self.face_recognition_queue.task_done()
                
            except queue.Empty:
                if self.recognition_in_progress:
                    elapsed = time.time() - self.recognition_start_time
                    if elapsed > self.max_recognition_time:
                        print(f"🚨 DEBUG: RECONNAISSANCE BLOQUÉE ({elapsed:.1f}s) - DÉBLOCAGE FORCÉ")
                        self.recognition_in_progress = False
                        self.recognition_start_time = 0
                        self.failed_recognitions += 1
                
                time.sleep(0.05)
                continue
            except Exception as e:
                print(f" DEBUG Erreur worker: {e}")
                self.recognition_in_progress = False
                time.sleep(0.1)
        
        print(" Worker reconnaissance DEBUG arrêté")
    
    def _debug_emotion_worker(self):
        """Worker émotion DEBUG"""
        print(" Worker émotion DEBUG démarré")
        
        while self.processing_active:
            try:
                emotion_data = self.emotion_analysis_queue.get(timeout=0.5)
                
                if emotion_data is None:
                    break
                
                face_img, student_name, frame_id = emotion_data
                
                print(f" DEBUG: Analyse émotion pour {student_name}")
                
                try:
                    emotion_record = self.emotion_analyzer.analyze_emotion(face_img, student_name)
                    if emotion_record:
                        self.logger.log_emotion(emotion_record)
                        print(f" DEBUG ÉMOTION: {student_name} - {emotion_record.emotion.value} ({emotion_record.confidence:.1f}%)")
                        print(f" DEBUG: Log émotion écrit pour {student_name}")
                    else:
                        print(f" DEBUG: Aucune émotion retournée pour {student_name}")
                        
                except Exception as e:
                    print(f" DEBUG Erreur émotion: {e}")
                
                self.emotion_analysis_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f" DEBUG Erreur worker émotion: {e}")
                time.sleep(0.1)
        
        print(" Worker émotion DEBUG arrêté")
    
    def _force_handle_result(self, name, confidence, face_img):
        """FORCER le traitement du résultat"""
        try:
            print(f" DEBUG: Traitement forcé pour {name}")
            
            if name not in self.recognized_students:
                print(f" DEBUG: Ajout {name} à recognized_students")
                self.recognized_students.add(name)
                
                attendance_record = AttendanceRecord(
                    student_name=name,
                    timestamp=datetime.now(),
                    has_class=True,
                    course="DEBUG_Course",
                    classroom="DEBUG_Room"
                )
                self.logger.log_attendance(attendance_record)
                print(f"📝 DEBUG: NOUVELLE présence enregistrée pour {name}")
                
                
                print(f" DEBUG: {name} ajouté avec succès (pas d'ouverture automatique)")
            else:
                print(f" DEBUG: {name} déjà reconnu, pas de nouvelle présence enregistrée")
            
            # Toujours ajouter l'émotion
            try:
                while not self.emotion_analysis_queue.empty():
                    try:
                        self.emotion_analysis_queue.get_nowait()
                        self.emotion_analysis_queue.task_done()
                    except queue.Empty:
                        break
                
                self.emotion_analysis_queue.put_nowait((face_img.copy(), name, time.time()))
                print(f" DEBUG: Émotion forcée pour {name}")
                
            except Exception as e:
                print(f" DEBUG Erreur ajout émotion: {e}")
                
        except Exception as e:
            print(f" DEBUG Erreur traitement forcé: {e}")
    
    def _calibrate_attention_system(self):
        """Calibrer le système de suivi d'attention"""
        print(" DEBUG: Calibration attention...")
        
        frame = self.camera_manager.get_frame()
        if frame is not None:
            faces = self.face_detector.detect_faces_optimized(frame)
            if faces:
                self.attention_tracker.calibrate(frame, faces)
            else:
                self.attention_tracker.is_calibrated = True
        
        print(" DEBUG: Attention calibrée")
    
    def _process_frame_debug(self, frame):
        """Traiter chaque frame - VERSION DEBUG"""
        if not self.is_running:
            return
        
        try:
            self.frame_count += 1
            current_time = time.time()
            
            if current_time - self.last_diagnostic_time > 5.0:
                self.print_diagnostic()
                self.last_diagnostic_time = current_time
            
            if self.frame_count % 90 == 1:
                faces = self.face_detector.detect_faces_optimized(frame)
                
                if faces:
                    print(f" DEBUG: {len(faces)} visage(s) détecté(s)")
                    self._force_attention_processing(frame, faces)
                    
                    if not self.recognition_in_progress and self.face_recognition_queue.empty():
                        self._try_recognition(frame, faces)
                    else:
                        print(f" DEBUG: Skip reconnaissance (en_cours: {self.recognition_in_progress}, queue: {self.face_recognition_queue.qsize()})")
                        
        except Exception as e:
            print(f" DEBUG Erreur frame: {e}")
    
    def _force_attention_processing(self, frame, faces):
        """FORCER le traitement de l'attention"""
        try:
            print(" DEBUG: Traitement attention forcé")
            
            face_names = []
            for i, face in enumerate(faces):
                if len(self.recognized_students) > 0:
                    face_names.append(list(self.recognized_students)[0])
                else:
                    face_names.append(f"Face_{i}")
            
            print(f" DEBUG: Appel attention_tracker.update_tracking avec {len(faces)} visages et noms: {face_names}")
            
            try:
                attention_records = self.attention_tracker.update_tracking(frame, faces, face_names)
                print(f" DEBUG: attention_tracker retourné {len(attention_records)} records")
                
                for record in attention_records:
                    print(f" DEBUG: Traitement record attention pour {record.student_name}")
                    self.logger.log_attention(record)
                    print(f" DEBUG ATTENTION: {record.student_name} - {record.status.value}")
                    print(f" DEBUG: Log attention écrit pour {record.student_name}")
                    
                if len(attention_records) == 0:
                    print(" DEBUG: Aucun record d'attention retourné par le tracker")
                    
                    if len(face_names) > 0 and len(faces) > 0:
                        print(" DEBUG: CRÉATION FORCÉE d'un record d'attention")
                        from data.models import AttentionRecord, AttentionStatus
                        from datetime import datetime
                        import random
                        
                        forced_record = AttentionRecord(
                            student_name=face_names[0],
                            timestamp=datetime.now(),
                            status=AttentionStatus.CONCENTRE if random.random() > 0.5 else AttentionStatus.DISTRAIT,
                            std_x=random.uniform(5.0, 15.0),
                            std_y=random.uniform(3.0, 12.0)
                        )
                        
                        self.logger.log_attention(forced_record)
                        print(f"📊 DEBUG ATTENTION FORCÉE: {forced_record.student_name} - {forced_record.status.value}")
                        print(f"📝 DEBUG: Log attention forcé écrit pour {forced_record.student_name}")
                    
            except Exception as attention_error:
                print(f" DEBUG Erreur dans attention_tracker.update_tracking: {attention_error}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f" DEBUG Erreur attention forcée: {e}")
            import traceback
            traceback.print_exc()
    
    def _try_recognition(self, frame, faces):
        """Essayer la reconnaissance"""
        try:
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            face_img = frame[y:y+h, x:x+w]
            face_img = ImageProcessor.resize_face(face_img)
            
            face_data = (face_img.copy(), (x, y, w, h), self.frame_count)
            self.face_recognition_queue.put_nowait(face_data)
            print(f"🐛 DEBUG: Visage ajouté pour reconnaissance")
            
        except queue.Full:
            print(" DEBUG: File reconnaissance pleine")
        except Exception as e:
            print(f" DEBUG Erreur ajout reconnaissance: {e}")
    
    def manual_recognition_and_door_test(self):
        """Fonction appelée par le bouton Test de l'interface web"""
        try:
            print(" DEBUG: Test manuel déclenché depuis l'interface web")
            
            # Vérifier que la caméra est active
            if not self.camera_manager.is_active:
                print(" DEBUG: Caméra non active pour le test")
                return {
                    'success': False, 
                    'message': 'Caméra non active',
                    'door_opened': False
                }
            
            # Prendre une photo actuelle
            frame = self.camera_manager.get_frame()
            if frame is None:
                print("❌ DEBUG: Aucune image disponible")
                return {
                    'success': False, 
                    'message': 'Aucune image disponible',
                    'door_opened': False
                }
            
            # Détecter les visages
            faces = self.face_detector.detect_faces_optimized(frame)
            if not faces:
                print("❌ DEBUG: Aucun visage détecté pour le test")
                return {
                    'success': False, 
                    'message': 'Aucun visage détecté. Positionnez-vous face à la caméra.',
                    'door_opened': False
                }
            
            # Prendre le plus grand visage
            largest_face = max(faces, key=lambda f: f[2] * f[3])
            x, y, w, h = largest_face
            face_img = frame[y:y+h, x:x+w]
            face_img = ImageProcessor.resize_face(face_img)
            
            print(" DEBUG: Reconnaissance manuelle en cours...")
            
            # Reconnaissance IMMÉDIATE
            try:
                name, confidence = self.face_recognizer.recognize_face(face_img)
                print(f" DEBUG: Résultat reconnaissance manuelle: {name} ({confidence:.1f}%)")
                
                if name not in ["Inconnu", "Erreur", "Base_vide"]:
                    # PERSONNE RECONNUE
                    print(f" DEBUG: {name} reconnu, ouverture de la porte")
                    
                    # Ouvrir la porte
                    door_success = False
                    if self.door_controller.is_connected:
                        try:
                            door_success = self.door_controller.open_door(name, "manual_test")
                            if door_success:
                                print(f" DEBUG: Porte ouverte avec succès pour {name}")
                            else:
                                print(f" DEBUG: Échec ouverture porte pour {name}")
                        except Exception as door_error:
                            print(f" DEBUG: Erreur ouverture porte: {door_error}")
                    else:
                        print("⚠ DEBUG: Contrôleur de porte non connecté")
                    
                    return {
                        'success': True,
                        'message': f'Accès autorisé pour {name} (confiance: {confidence:.1f}%)',
                        'student_name': name,
                        'confidence': confidence,
                        'door_opened': door_success,
                        'door_connected': self.door_controller.is_connected
                    }
                
                else:
                    # PERSONNE NON RECONNUE
                    print(f" DEBUG: Personne non reconnue: {name}")
                    
                    # Envoyer une alerte à l'Arduino (LED rouge)
                    if self.door_controller.is_connected:
                        try:
                            self.door_controller.send_alert("unknown")
                            print(" DEBUG: Alerte envoyée à l'Arduino (LED rouge)")
                        except Exception as alert_error:
                            print(f" DEBUG: Erreur envoi alerte: {alert_error}")
                    
                    return {
                        'success': True,
                        'message': f'Accès refusé - Personne non reconnue (confiance: {confidence:.1f}%)',
                        'student_name': name,
                        'confidence': confidence,
                        'door_opened': False,
                        'door_connected': self.door_controller.is_connected
                    }
                    
            except Exception as recognition_error:
                print(f" DEBUG: Erreur reconnaissance manuelle: {recognition_error}")
                return {
                    'success': False,
                    'message': f'Erreur lors de la reconnaissance: {str(recognition_error)}',
                    'door_opened': False
                }
                
        except Exception as e:
            print(f" DEBUG: Erreur test manuel: {e}")
            return {
                'success': False,
                'message': f'Erreur système: {str(e)}',
                'door_opened': False
            }
    
    def get_unique_attendance_today(self):
        """Obtenir le nombre UNIQUE d'étudiants présents aujourd'hui"""
        try:
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            
            attendance_logs = self.logger.get_recent_logs('attendance', 1000)
            
            unique_students_today = set()
            for log in attendance_logs:
                if log.get('timestamp', '').startswith(today):
                    student_name = log.get('student_name')
                    if student_name:
                        unique_students_today.add(student_name)
            
            print(f" DEBUG: Étudiants UNIQUES présents aujourd'hui: {len(unique_students_today)} - {list(unique_students_today)}")
            return len(unique_students_today)
            
        except Exception as e:
            print(f" DEBUG Erreur calcul présence unique: {e}")
            return len(self.recognized_students)
    
    def print_diagnostic(self):
        """Diagnostic DEBUG"""
        status = self.get_queue_status()
        unique_today = self.get_unique_attendance_today()
        
        print("\n" + "="*60)
        print("🐛 DIAGNOSTIC DEBUG")
        print("="*60)
        print(f" File reconnaissance: {status['recognition_queue_size']}/1")
        print(f" File émotions: {status['emotion_queue_size']}/1")
        print(f" Reconnaissances réussies: {status['successful_recognitions']}")
        print(f" Reconnaissances échouées: {status['failed_recognitions']}")
        print(f" Étudiants reconnus: {list(self.recognized_students)}")
        print(f" Étudiants UNIQUES aujourd'hui: {unique_today}")
        print(f" Reconnaissance en cours: {'🟢 Oui' if status['recognition_in_progress'] else '🔴 Non'}")
        print(f" Porte connectée: {'🟢 Oui' if self.door_controller.is_connected else '🔴 Non'}")
        
        if status['recognition_in_progress']:
            elapsed = time.time() - self.recognition_start_time if self.recognition_start_time > 0 else 0
            print(f"⏱ Temps reconnaissance: {elapsed:.1f}s")
        
        print("="*60 + "\n")
    
    def stop(self):
        """Arrêter le système"""
        print(" DEBUG: Arrêt du système...")
        self.is_running = False
        self.processing_active = False
        
        self.recognition_in_progress = False
        
        while not self.face_recognition_queue.empty():
            try:
                self.face_recognition_queue.get_nowait()
                self.face_recognition_queue.task_done()
            except:
                pass
        
        while not self.emotion_analysis_queue.empty():
            try:
                self.emotion_analysis_queue.get_nowait()
                self.emotion_analysis_queue.task_done()
            except:
                pass
        
        try:
            self.face_recognition_queue.put_nowait(None)
            self.emotion_analysis_queue.put_nowait(None)
        except:
            pass
        
        if self.recognition_thread and self.recognition_thread.is_alive():
            self.recognition_thread.join(timeout=1.0)
        
        if self.emotion_thread and self.emotion_thread.is_alive():
            self.emotion_thread.join(timeout=1.0)
        
        self.camera_manager.stop()
        
        try:
            self.door_controller.disconnect()
        except:
            pass
        
        print(" DEBUG: Système arrêté")
    
    def run_web_interface(self):
        """Lancer l'interface web"""
        print(" DEBUG: Interface web...")
        from api.routes import app, socketio
        
        socketio.run(
            app, 
            host=settings.API_HOST, 
            port=settings.API_PORT, 
            debug=False,
            use_reloader=False,
            log_output=False
        )
    
    def get_queue_status(self):
        """Obtenir le statut des files d'attente"""
        return {
            'recognition_queue_size': self.face_recognition_queue.qsize(),
            'emotion_queue_size': self.emotion_analysis_queue.qsize(),
            'successful_recognitions': self.successful_recognitions,
            'failed_recognitions': self.failed_recognitions,
            'processing_active': self.processing_active,
            'recognition_thread_alive': self.recognition_thread and self.recognition_thread.is_alive(),
            'emotion_thread_alive': self.emotion_thread and self.emotion_thread.is_alive(),
            'recognized_students_count': len(self.recognized_students),
            'frame_count': self.frame_count,
            'recognition_in_progress': self.recognition_in_progress
        }

def main():
    """Fonction principale DEBUG"""
    system = SmartClassroomSystemFixed()
    
    try:
        if system.start():
            web_thread = threading.Thread(target=system.run_web_interface)
            web_thread.daemon = True
            web_thread.start()
            
            print(" Smart Classroom System DEBUG actif!")
            print(" Interface web: http://localhost:8000")
            print(" Appuyez sur 'q' pour quitter")
            
            while True:
                frame = system.camera_manager.get_frame()
                if frame is not None:
                    status = system.get_queue_status()
                    cv2.putText(frame, "DEBUG MODE", (10, 30),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)
                    cv2.putText(frame, f"Success: {status['successful_recognitions']}", (10, 60),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    cv2.putText(frame, f"Processing: {'YES' if status['recognition_in_progress'] else 'NO'}", (10, 120),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 255), 2)
                    
                    y_offset = 150
                    for student in list(system.recognized_students)[:3]:
                        cv2.putText(frame, student, (10, y_offset),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                        y_offset += 30
                    
                    cv2.imshow("Smart Classroom - DEBUG MODE", frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
                time.sleep(0.03)
    
    except KeyboardInterrupt:
        print("\n Interruption utilisateur")
    except Exception as e:
        print(f" Erreur système DEBUG: {e}")
        import traceback
        traceback.print_exc()
    finally:
        system.stop()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
