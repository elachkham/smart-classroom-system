import os
import cv2
import base64
import threading
import time
from flask import Flask, request, jsonify, render_template
from flask_socketio import SocketIO, emit
import json
from datetime import datetime
from pathlib import Path
from flask import send_from_directory
from flask import Response

# CORRECTION: Chemin absolu vers les templates
BASE_DIR = Path(__file__).parent.parent  # Remonte de api/ vers smart_classroom/
TEMPLATE_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

# Debug - Vérification des chemins
print(f"🔍 BASE_DIR: {BASE_DIR}")
print(f"🔍 TEMPLATE_DIR: {TEMPLATE_DIR}")
print(f"🔍 Index exists: {(TEMPLATE_DIR / 'index.html').exists()}")

# Créer Flask avec les bons chemins
app = Flask(__name__, 
            template_folder=str(TEMPLATE_DIR),
            static_folder=str(STATIC_DIR))

app.config['SECRET_KEY'] = 'smart_classroom_secret_key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Instances globales - Seront initialisées par le système principal
main_system = None
logger = None
camera_manager = None
face_recognizer = None
attention_tracker = None
emotion_analyzer = None
door_controller = None

# Variables globales pour la capture web
current_capture = None
capture_status = {
    'active': False,
    'student_name': '',
    'images_captured': 0,
    'total_images': 0,
    'message': ''
}

# ================================
# CLASSE DE CAPTURE WEB INTÉGRÉE
# ================================

class WebFaceCapture:
    """Capture de visages intégrée pour l'interface web"""
    
    def __init__(self, camera_manager, face_detector, student_name, num_images=20, callback=None):
        self.camera_manager = camera_manager
        self.face_detector = face_detector
        self.student_name = student_name
        self.num_images = num_images
        self.callback = callback
        
        self.images_captured = 0
        self.is_capturing = False
        
        # Créer le dossier étudiant
        from config.settings import settings
        self.student_dir = settings.DATASET_PATH / student_name
        self.student_dir.mkdir(parents=True, exist_ok=True)
        
        # Mode de capture: 'manual' pour plus de contrôle
        self.capture_mode = 'manual'
        
    def start_capture(self):
        """Démarrer la capture"""
        self.is_capturing = True
        self.images_captured = 0
        
        self._update_status({
            'active': True,
            'message': f'Capture démarrée pour {self.student_name}. Appuyez sur "Capturer Image" quand vous êtes prêt.',
            'images_captured': 0
        })
        
        self._manual_capture_mode()
    
    def _manual_capture_mode(self):
        """Mode capture manuel - attend les déclenchements manuels"""
        self._update_status({
            'message': f'Mode manuel actif. Cliquez sur "Capturer Image" pour prendre une photo ({self.images_captured}/{self.num_images})'
        })
        
        # Garder le thread actif mais en attente
        while self.is_capturing and self.images_captured < self.num_images:
            time.sleep(0.1)
        
        if self.images_captured >= self.num_images:
            self._complete_capture()
    
    def trigger_manual_capture(self):
        """Déclencher manuellement une capture"""
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
        """Sauvegarder une image de visage"""
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
                print(f"✅ Image {self.images_captured} sauvegardée: {img_path}")
                return True
            else:
                self._update_status({'message': 'Erreur lors de la sauvegarde de l\'image'})
                return False
                
        except Exception as e:
            self._update_status({'message': f'Erreur sauvegarde: {e}'})
            return False
    
    def _complete_capture(self):
        """Terminer la capture"""
        self.is_capturing = False
        
        self._update_status({
            'active': False,
            'message': f'Capture terminée ! {self.images_captured} images sauvegardées pour {self.student_name}.'
        })
        
        print(f'✅ Capture terminée: {self.images_captured} images pour {self.student_name}')
    
    def stop_capture(self):
        """Arrêter la capture"""
        self.is_capturing = False
        
        self._update_status({
            'active': False,
            'message': f'Capture arrêtée. {self.images_captured} images sauvegardées.'
        })
    
    def _update_status(self, status_update):
        """Mettre à jour le statut via callback"""
        if self.callback:
            self.callback(status_update)

# ================================
# FONCTIONS UTILITAIRES
# ================================

def update_capture_status(status_update):
    """Callback pour mettre à jour le statut de capture"""
    global capture_status
    capture_status.update(status_update)
    
    # Envoyer via WebSocket pour mise à jour temps réel
    try:
        socketio.emit('capture_status_update', capture_status)
    except Exception as e:
        print(f"Erreur WebSocket: {e}")

# ================================
# ROUTES PRINCIPALES
# ================================

@app.route('/')
def index():
    """Page d'accueil"""
    try:
        return render_template('index.html')
    except Exception as e:
        print(f"Erreur template: {e}")
        # Fallback en cas d'erreur
        return f"""
        <h1>Smart Classroom Platform</h1>
        <p>Erreur de template: {e}</p>
        <p>Template directory: {app.template_folder}</p>
        <p>Vérifiez que templates/index.html existe</p>
        """


@app.route('/capture')
def capture_page():
    """Page de capture d'étudiants"""
    try:
        return render_template('capture.html')
    except Exception as e:
        print(f"Erreur template capture: {e}")
        return f"""
        <h1>Page de Capture</h1>
        <p>Erreur de template: {e}</p>
        <a href="/">Retour à l'accueil</a>
        """

@app.route('/dashboard')
def dashboard_page():
    """Page de dashboard/monitoring"""
    try:
        return render_template('dashboard.html')
    except Exception as e:
        print(f"Erreur template dashboard: {e}")
        return f"""
        <h1>Dashboard Smart Classroom</h1>
        <p>Erreur de template: {e}</p>
        <a href="/">Retour à l'accueil</a>
        """

# 4. AJOUTER CES ROUTES API SUPPLÉMENTAIRES

@app.route('/api/dashboard/metrics', methods=['GET'])
def get_dashboard_metrics():
    """Obtenir les métriques pour le dashboard"""
    try:
        # Calculer les métriques depuis les logs
        metrics = {
            'attendance_today': 0,
            'average_attention': 75,
            'positive_emotions': 80,
            'system_uptime': '12h',
            'attendance_trend': '+5%',
            'attention_trend': '+2%',
            'emotion_trend': '+3%',
            'system_trend': '99%'
        }
        
        # Obtenir les données réelles si disponible
        if logger:
            attendance_logs = logger.get_recent_logs('attendance', 100)
            metrics['attendance_today'] = len([
                log for log in attendance_logs 
                if log.get('timestamp', '').startswith(datetime.now().strftime('%Y-%m-%d'))
            ])
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/charts/attention', methods=['GET'])
def get_attention_chart_data():
    """Données pour le graphique d'attention"""
    try:
        period = request.args.get('period', '6h')
        
        # Simuler des données d'attention (remplacer par de vraies données)
        import random
        from datetime import timedelta
        
        now = datetime.now()
        data_points = []
        
        # Générer des points selon la période
        if period == '1h':
            intervals = 12  # 5 min intervals
            delta = timedelta(minutes=5)
        elif period == '6h':
            intervals = 36  # 10 min intervals
            delta = timedelta(minutes=10)
        else:  # 24h
            intervals = 48  # 30 min intervals
            delta = timedelta(minutes=30)
        
        for i in range(intervals):
            timestamp = now - (delta * (intervals - i))
            attention_level = random.randint(60, 95)
            data_points.append({
                'timestamp': timestamp.isoformat(),
                'attention': attention_level
            })
        
        return jsonify({
            'success': True,
            'data': data_points,
            'period': period
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/charts/emotions', methods=['GET'])
def get_emotion_chart_data():
    """Données pour le graphique d'émotions"""
    try:
        # Obtenir les données d'émotions récentes
        emotion_data = {
            'happy': 45,
            'neutral': 30,
            'surprise': 15,
            'sad': 5,
            'angry': 3,
            'fear': 1,
            'disgust': 1
        }
        
        # Si on a de vraies données
        if logger:
            emotion_logs = logger.get_recent_logs('emotions', 100)
            if emotion_logs:
                emotion_counts = {}
                for log in emotion_logs:
                    emotion = log.get('emotion', 'neutral')
                    emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
                
                total = sum(emotion_counts.values())
                if total > 0:
                    emotion_data = {
                        emotion: round((count / total) * 100, 1)
                        for emotion, count in emotion_counts.items()
                    }
        
        return jsonify({
            'success': True,
            'data': emotion_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/dashboard/performance', methods=['GET'])
def get_performance_metrics():
    """Métriques de performance du système"""
    try:
        import psutil
        import random
        
        # Métriques système réelles si possible
        try:
            cpu_percent = psutil.cpu_percent()
            memory_info = psutil.virtual_memory()
            memory_mb = round(memory_info.used / 1024 / 1024)
        except:
            # Valeurs simulées si psutil n'est pas disponible
            cpu_percent = random.randint(10, 30)
            memory_mb = random.randint(100, 500)
        
        metrics = {
            'camera_fps': 30 if (camera_manager and camera_manager.is_active) else 0,
            'detections_per_min': random.randint(5, 15),
            'cpu_usage': f"{cpu_percent}%",
            'memory_usage': f"{memory_mb} MB",
            'errors_per_hour': random.randint(0, 2)
        }
        
        return jsonify({
            'success': True,
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'metrics': {
                'camera_fps': 0,
                'detections_per_min': 0,
                'cpu_usage': '0%',
                'memory_usage': '0 MB',
                'errors_per_hour': 0
            },
            'error': str(e)
        })

@app.route('/api/dashboard/alerts', methods=['GET'])
def get_system_alerts():
    """Obtenir les alertes système"""
    try:
        alerts = [
            {
                'id': 1,
                'type': 'info',
                'icon': 'ℹ️',
                'message': 'Système initialisé avec succès',
                'timestamp': datetime.now().isoformat(),
                'time_ago': 'Il y a 2 min'
            }
        ]
        
        # Ajouter des alertes basées sur l'état du système
        if not (camera_manager and camera_manager.is_active):
            alerts.append({
                'id': 2,
                'type': 'warning',
                'icon': '⚠️',
                'message': 'Caméra non active',
                'timestamp': datetime.now().isoformat(),
                'time_ago': 'Maintenant'
            })
        
        return jsonify({
            'success': True,
            'alerts': alerts
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/export/dashboard', methods=['GET'])
def export_dashboard_data():
    """Exporter les données du dashboard"""
    try:
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'system_status': {},
            'recent_logs': {},
            'metrics': {}
        }
        
        # Ajouter les données si disponibles
        if logger:
            export_data['recent_logs'] = {
                'attendance': logger.get_recent_logs('attendance', 50),
                'attention': logger.get_recent_logs('attention', 50),
                'emotions': logger.get_recent_logs('emotions', 50),
                'access': logger.get_recent_logs('access', 50)
            }
        
        # Ajouter le statut système
        if main_system:
            export_data['system_status'] = {
                'camera_active': camera_manager.is_active if camera_manager else False,
                'components_connected': True
            }
        
        return jsonify({
            'success': True,
            'data': export_data
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# 5. AJOUTER CETTE ROUTE POUR LES ASSETS STATIQUES (si nécessaire)

@app.route('/assets/<path:filename>')
def serve_assets(filename):
    """Servir les fichiers statiques depuis le dossier assets"""
    try:
        return send_from_directory(STATIC_DIR, filename)
    except Exception as e:
        return f"Asset non trouvé: {filename}", 404

# 6. MODIFIER LA GESTION D'ERREURS (ajouter ces handlers)

@app.errorhandler(FileNotFoundError)
def handle_file_not_found(error):
    return jsonify({
        'error': 'Fichier non trouvé',
        'message': str(error)
    }), 404

@app.errorhandler(PermissionError)
def handle_permission_error(error):
    return jsonify({
        'error': 'Erreur de permissions',
        'message': 'Vérifiez les permissions des fichiers'
    }), 403



@app.route('/debug')
def debug_templates():
    """Route de diagnostic"""
    info = {
        "current_dir": os.getcwd(),
        "template_folder": app.template_folder,
        "static_folder": app.static_folder,
        "templates_exists": os.path.exists(app.template_folder),
        "index_exists": os.path.exists(os.path.join(app.template_folder, 'index.html')),
        "files_in_templates": os.listdir(app.template_folder) if os.path.exists(app.template_folder) else [],
        "main_system_connected": main_system is not None,
        "camera_manager_available": camera_manager is not None,
        "capture_status": capture_status
    }
    
    return f"<pre>{json.dumps(info, indent=2, default=str)}</pre>"

@app.route('/health')
def health_check():
    """Vérification de santé de l'API"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'system_connected': main_system is not None,
        'capture_active': capture_status['active'],
        'components': {
            'camera': camera_manager is not None,
            'face_recognizer': face_recognizer is not None,
            'logger': logger is not None,
            'door_controller': door_controller is not None
        }
    })

# ================================
# ROUTES SYSTÈME
# ================================

@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """Obtenir le statut du système"""
    try:
        return jsonify({
            'camera_active': camera_manager.is_active if camera_manager else False,
            'face_recognition_active': face_recognizer is not None,
            'attention_tracking_active': attention_tracker is not None,
            'emotion_analysis_active': emotion_analyzer is not None,
            'door_controller_connected': door_controller.is_connected if door_controller else False,
            'main_system_connected': main_system is not None,
            'capture_active': capture_status['active']
        })
    except Exception as e:
        return jsonify({'error': str(e)})

# ================================
# ROUTES CAMÉRA
# ================================

@app.route('/api/camera/status', methods=['GET'])
def camera_status():
    """Obtenir le statut réel de la caméra"""
    try:
        if main_system and hasattr(main_system, 'camera_manager'):
            is_active = main_system.camera_manager.is_active
            return jsonify({
                'success': True, 
                'active': is_active,
                'message': 'Caméra active' if is_active else 'Caméra arrêtée'
            })
        else:
            return jsonify({'success': False, 'active': False, 'message': 'Système non initialisé'})
    except Exception as e:
        return jsonify({'success': False, 'active': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/camera/start', methods=['POST'])
def start_camera():
    """Démarrer la caméra"""
    try:
        if main_system and hasattr(main_system, 'camera_manager'):
            if main_system.camera_manager.is_active:
                return jsonify({'success': True, 'message': 'Caméra déjà active'})
            elif main_system.camera_manager.start():
                return jsonify({'success': True, 'message': 'Caméra démarrée'})
            else:
                return jsonify({'success': False, 'message': 'Erreur démarrage caméra'})
        else:
            return jsonify({'success': False, 'message': 'Système non initialisé'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/camera/stop', methods=['POST'])
def stop_camera():
    """Arrêter la caméra"""
    try:
        if main_system and hasattr(main_system, 'camera_manager'):
            main_system.camera_manager.stop()
            return jsonify({'success': True, 'message': 'Caméra arrêtée'})
        else:
            return jsonify({'success': False, 'message': 'Système non initialisé'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/camera/stream')
def video_stream_optimized():
    """Stream vidéo optimisé pour réduire la latence"""
    def generate_frames_optimized():
        last_frame_time = 0
        frame_interval = 1.0 / 25  # 25 FPS pour le web (plus fluide que 30)
        jpeg_quality = 75  # Qualité réduite pour moins de latence
        
        while True:
            try:
                current_time = time.time()
                
                # Contrôler le framerate côté serveur
                if current_time - last_frame_time < frame_interval:
                    time.sleep(0.01)  # Petite pause
                    continue
                
                if main_system and main_system.camera_manager and main_system.camera_manager.is_active:
                    # Utiliser la version rapide pour le streaming
                    frame = main_system.camera_manager.get_latest_frame_fast()
                    
                    if frame is not None:
                        # Optimisations d'image pour le streaming
                        # 1. Réduire la taille si nécessaire
                        h, w = frame.shape[:2]
                        if w > 640:
                            frame = cv2.resize(frame, (640, int(h * 640 / w)), 
                                             interpolation=cv2.INTER_AREA)
                        
                        # 2. Compression JPEG optimisée
                        encode_params = [
                            cv2.IMWRITE_JPEG_QUALITY, jpeg_quality,
                            cv2.IMWRITE_JPEG_OPTIMIZE, 1,
                            cv2.IMWRITE_JPEG_PROGRESSIVE, 1
                        ]
                        
                        ret, buffer = cv2.imencode('.jpg', frame, encode_params)
                        
                        if ret:
                            frame_bytes = buffer.tobytes()
                            last_frame_time = current_time
                            
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n'
                                   b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
                                   b'\r\n' + frame_bytes + b'\r\n')
                        else:
                            # Frame d'erreur
                            yield get_error_frame()
                    else:
                        # Pas de frame disponible
                        yield get_placeholder_frame_optimized()
                else:
                    # Caméra inactive
                    yield get_placeholder_frame_optimized()
                
                # Petite pause pour éviter la surcharge CPU
                time.sleep(0.005)  # 5ms
                
            except Exception as e:
                print(f"Erreur streaming optimisé: {e}")
                yield get_error_frame()
                time.sleep(0.1)
    
    return Response(
        generate_frames_optimized(),
        mimetype='multipart/x-mixed-replace; boundary=frame',
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0',
            'Connection': 'close'
        }
    )

def get_placeholder_frame_optimized():
    """Frame placeholder optimisée"""
    import numpy as np
    
    # Créer une image plus petite pour réduire la latence
    placeholder = np.zeros((360, 480, 3), dtype=np.uint8)
    
    # Ajouter du texte
    cv2.putText(placeholder, "Camera Inactive", (120, 160),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    cv2.putText(placeholder, "Click 'Start Camera'", (100, 200),
               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
    
    # Encoder avec compression rapide
    ret, buffer = cv2.imencode('.jpg', placeholder, [cv2.IMWRITE_JPEG_QUALITY, 60])
    frame_bytes = buffer.tobytes() if ret else b''
    
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
            b'\r\n' + frame_bytes + b'\r\n')

def get_error_frame():
    """Frame d'erreur optimisée"""
    import numpy as np
    
    error_frame = np.zeros((360, 480, 3), dtype=np.uint8)
    cv2.putText(error_frame, "Stream Error", (150, 180),
               cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    
    ret, buffer = cv2.imencode('.jpg', error_frame, [cv2.IMWRITE_JPEG_QUALITY, 50])
    frame_bytes = buffer.tobytes() if ret else b''
    
    return (b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n'
            b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
            b'\r\n' + frame_bytes + b'\r\n')

# ================================================================
# ROUTE OPTIMISÉE POUR TESTER LA LATENCE
# ================================================================

@app.route('/api/camera/stream/fast')
def video_stream_ultra_fast():
    """Stream ultra-rapide pour test de latence"""
    def generate_frames_ultra_fast():
        while True:
            try:
                if main_system and main_system.camera_manager and main_system.camera_manager.is_active:
                    frame = main_system.camera_manager.get_latest_frame_fast()
                    
                    if frame is not None:
                        # Compression maximale pour vitesse
                        ret, buffer = cv2.imencode('.jpg', frame, [
                            cv2.IMWRITE_JPEG_QUALITY, 50,
                            cv2.IMWRITE_JPEG_OPTIMIZE, 0
                        ])
                        
                        if ret:
                            yield (b'--frame\r\n'
                                   b'Content-Type: image/jpeg\r\n\r\n' + 
                                   buffer.tobytes() + b'\r\n')
                
                time.sleep(0.033)  # ~30 FPS
                
            except Exception as e:
                break
    
    return Response(
        generate_frames_ultra_fast(),
        mimetype='multipart/x-mixed-replace; boundary=frame'
    )

@app.route('/api/camera/snapshot')
def camera_snapshot():
    """Prendre un snapshot de la caméra"""
    try:
        if main_system and main_system.camera_manager and main_system.camera_manager.is_active:
            frame = main_system.camera_manager.get_frame()
            if frame is not None:
                # Encoder en base64 pour JSON
                ret, buffer = cv2.imencode('.jpg', frame)
                if ret:
                    img_base64 = base64.b64encode(buffer).decode('utf-8')
                    return jsonify({
                        'success': True,
                        'image': f'data:image/jpeg;base64,{img_base64}',
                        'timestamp': datetime.now().isoformat()
                    })
        
        return jsonify({'success': False, 'message': 'Caméra inactive ou indisponible'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

# ================================
# ROUTES RECONNAISSANCE
# ================================

@app.route('/api/recognition/start', methods=['POST'])
def start_face_recognition():
    """Démarrer la reconnaissance faciale"""
    try:
        if main_system:
            return jsonify({'success': True, 'message': 'Reconnaissance faciale active'})
        else:
            return jsonify({'success': False, 'message': 'Système non initialisé'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/recognition/stop', methods=['POST'])
def stop_face_recognition():
    """Arrêter la reconnaissance faciale"""
    return jsonify({'success': True, 'message': 'Reconnaissance faciale désactivée'})

# ================================
# ROUTES ÉTUDIANTS
# ================================

@app.route('/api/students', methods=['GET'])
def get_students():
    """Obtenir la liste des étudiants"""
    try:
        if face_recognizer:
            students = face_recognizer.database.get_all_students()
            return jsonify({'students': students, 'count': len(students)})
        else:
            return jsonify({'students': [], 'count': 0, 'message': 'Système non initialisé'})
    except Exception as e:
        return jsonify({'students': [], 'count': 0, 'error': str(e)})

@app.route('/api/students/stats', methods=['GET'])
def get_students_stats():
    """Obtenir les statistiques de la base étudiants"""
    try:
        if face_recognizer:
            stats = face_recognizer.get_database_stats()
            return jsonify({'success': True, 'stats': stats})
        else:
            return jsonify({'success': False, 'message': 'Système non initialisé'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/students/<student_name>', methods=['GET'])
def get_student_details(student_name):
    """Obtenir les détails d'un étudiant"""
    try:
        if face_recognizer:
            details = face_recognizer.get_student_details(student_name)
            if details:
                return jsonify({'success': True, 'student': details})
            return jsonify({'success': False, 'message': 'Étudiant non trouvé'})
        else:
            return jsonify({'success': False, 'message': 'Système non initialisé'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/students/<student_name>', methods=['DELETE'])
def delete_student(student_name):
    """Supprimer un étudiant"""
    try:
        if face_recognizer:
            success = face_recognizer.delete_student(student_name)
            message = f'Étudiant {student_name} supprimé' if success else 'Erreur suppression'
            return jsonify({'success': success, 'message': message})
        else:
            return jsonify({'success': False, 'message': 'Système non initialisé'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

# ================================
# ROUTES CAPTURE WEB
# ================================

@app.route('/api/students/capture/start', methods=['POST'])
def start_web_capture():
    """Démarrer la capture depuis l'interface web"""
    global current_capture, capture_status
    
    try:
        data = request.json
        student_name = data.get('name', '').strip()
        num_images = data.get('num_images', 20)
        
        if not student_name:
            return jsonify({'success': False, 'message': 'Nom d\'étudiant requis'})
        
        # Nettoyer le nom (remplacer espaces par underscores)
        student_name = student_name.replace(' ', '_')
        
        if capture_status['active']:
            return jsonify({'success': False, 'message': 'Une capture est déjà en cours'})
        
        # Vérifier que la caméra est active
        if not (main_system and main_system.camera_manager and main_system.camera_manager.is_active):
            return jsonify({'success': False, 'message': 'Caméra non active. Démarrez la caméra d\'abord.'})
        
        # Vérifier que le détecteur de visages est disponible
        if not (main_system and main_system.face_detector):
            return jsonify({'success': False, 'message': 'Détecteur de visages non disponible'})
        
        # Initialiser le statut de capture
        capture_status.update({
            'active': True,
            'student_name': student_name,
            'images_captured': 0,
            'total_images': num_images,
            'message': 'Préparation de la capture...'
        })
        
        # Créer l'instance de capture web
        current_capture = WebFaceCapture(
            camera_manager=main_system.camera_manager,
            face_detector=main_system.face_detector,
            student_name=student_name,
            num_images=num_images,
            callback=update_capture_status
        )
        
        # Démarrer la capture dans un thread
        capture_thread = threading.Thread(target=current_capture.start_capture, daemon=True)
        capture_thread.start()
        
        return jsonify({
            'success': True, 
            'message': f'Capture démarrée pour {student_name}',
            'status': capture_status
        })
        
    except Exception as e:
        capture_status['active'] = False
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/students/capture/status', methods=['GET'])
def get_capture_status():
    """Obtenir le statut de la capture en cours"""
    return jsonify({
        'success': True,
        'status': capture_status
    })

@app.route('/api/students/capture/stop', methods=['POST'])
def stop_web_capture():
    """Arrêter la capture en cours"""
    global current_capture, capture_status
    
    try:
        if current_capture:
            current_capture.stop_capture()
        
        capture_status.update({
            'active': False,
            'message': 'Capture arrêtée par l\'utilisateur'
        })
        
        return jsonify({'success': True, 'message': 'Capture arrêtée'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/students/capture/trigger', methods=['POST'])
def trigger_capture():
    """Déclencher manuellement une capture d'image"""
    global current_capture
    
    try:
        if not capture_status['active'] or not current_capture:
            return jsonify({'success': False, 'message': 'Aucune capture active'})
        
        success = current_capture.trigger_manual_capture()
        
        if success:
            return jsonify({
                'success': True, 
                'message': 'Image capturée !',
                'images_captured': capture_status['images_captured']
            })
        else:
            return jsonify({'success': False, 'message': 'Aucun visage détecté ou erreur de capture'})
            
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

# ================================
# ROUTES LOGS
# ================================

@app.route('/api/logs/<log_type>', methods=['GET'])
def get_logs(log_type):
    """Obtenir les logs par type"""
    try:
        if logger:
            limit = request.args.get('limit', 50, type=int)
            logs = logger.get_recent_logs(log_type, limit)
            return jsonify({'logs': logs, 'count': len(logs)})
        else:
            return jsonify({'logs': [], 'count': 0, 'message': 'Logger non initialisé'})
    except Exception as e:
        return jsonify({'logs': [], 'count': 0, 'error': str(e)})

# ================================
# ROUTES PORTE
# ================================

@app.route('/api/door/open', methods=['POST'])
def open_door():
    """Ouvrir la porte"""
    try:
        if door_controller and door_controller.is_connected:
            success = door_controller.open_door(reason="manual")
            return jsonify({'success': success, 'message': 'Porte ouverte' if success else 'Erreur ouverture'})
        else:
            return jsonify({'success': False, 'message': 'Contrôleur de porte non connecté'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

@app.route('/api/door/test', methods=['POST'])
def test_door():
    """Test de la porte avec reconnaissance automatique"""
    try:
        if main_system:
            print("🚪 API: Test de porte déclenché depuis l'interface")
            
            # Appeler la nouvelle fonction de test manuel
            result = main_system.manual_recognition_and_door_test()
            
            if result['success']:
                return jsonify({
                    'success': True,
                    'message': result['message'],
                    'student_name': result.get('student_name', ''),
                    'confidence': result.get('confidence', 0),
                    'door_opened': result.get('door_opened', False),
                    'door_connected': result.get('door_connected', False)
                })
            else:
                return jsonify({
                    'success': False,
                    'message': result['message'],
                    'door_opened': False,
                    'door_connected': door_controller.is_connected if door_controller else False
                })
        else:
            return jsonify({
                'success': False, 
                'message': 'Système non initialisé',
                'door_opened': False,
                'door_connected': False
            })
    except Exception as e:
        print(f"❌ API: Erreur test porte: {e}")
        return jsonify({
            'success': False, 
            'message': f'Erreur: {str(e)}',
            'door_opened': False,
            'door_connected': False
        })
# ================================
# ROUTES PARAMÈTRES
# ================================

@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Obtenir les paramètres"""
    try:
        from config.settings import settings as sys_settings
        return jsonify({
            'recognition_threshold': sys_settings.RECOGNITION_THRESHOLD,
            'serial_port': sys_settings.SERIAL_PORT,
            'detection_interval': sys_settings.DETECTION_INTERVAL,
            'window_size': sys_settings.WINDOW_SIZE,
            'model_name': sys_settings.RECOGNITION_MODEL,
            'camera_index': sys_settings.CAMERA_INDEX
        })
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/api/settings', methods=['POST'])
def save_settings():
    """Sauvegarder les paramètres"""
    try:
        data = request.json
        from config.settings import settings as sys_settings
        
        # Mettre à jour les paramètres
        if 'recognition_threshold' in data:
            sys_settings.RECOGNITION_THRESHOLD = data['recognition_threshold']
        if 'serial_port' in data:
            sys_settings.SERIAL_PORT = data['serial_port']
        
        return jsonify({'success': True, 'message': 'Paramètres sauvegardés'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Erreur: {str(e)}'})

# ================================
# WEBSOCKET EVENTS
# ================================

@socketio.on('connect')
def handle_connect():
    """Nouvelle connexion WebSocket"""
    emit('status', {'message': 'Connecté au système Smart Classroom'})
    print("📡 Nouvelle connexion WebSocket")

@socketio.on('disconnect')
def handle_disconnect():
    """Déconnexion WebSocket"""
    print('📡 Client WebSocket déconnecté')

@socketio.on('request_stats')
def handle_stats_request():
    """Demande de statistiques en temps réel"""
    try:
        if face_recognizer:
            stats = face_recognizer.get_database_stats()
            emit('stats_update', stats)
    except Exception as e:
        emit('error', {'message': str(e)})

@socketio.on('request_capture_status')
def handle_capture_status_request():
    """Demande du statut de capture"""
    emit('capture_status_update', capture_status)

# ================================
# ROUTES LÉGACY (COMPATIBILITÉ)
# ================================

@app.route('/api/students/capture', methods=['POST'])
def legacy_capture_route():
    """Route de compatibilité - redirige vers la nouvelle capture web"""
    return start_web_capture()

# ================================
# GESTION D'ERREURS
# ================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Route non trouvée'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Erreur interne du serveur'}), 500

# ================================
# POINT D'ENTRÉE (NE PAS UTILISER DIRECTEMENT)
# ================================

if __name__ == '__main__':
    print("⚠️ Ce fichier doit être importé par main.py, pas exécuté directement")
    app.run(debug=True, port=8000)