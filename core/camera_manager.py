

import cv2
import threading
import time
import queue
from typing import Optional, Callable
from config.settings import settings

class OptimizedCameraManager:
    """Gestionnaire de caméra optimisé pour réduire la latence"""
    
    def __init__(self):
        self.cap: Optional[cv2.VideoCapture] = None
        self.is_active = False
        self.frame = None
        self.frame_lock = threading.Lock()
        self.capture_thread = None
        self.callbacks = []
        
        # Buffer circulaire pour éviter l'accumulation
        self.frame_buffer = queue.Queue(maxsize=2)
        
        # Statistiques
        self.frame_count = 0
        self.fps = 0
        self.last_fps_time = time.time()
        self.fps_frame_count = 0
        
        # Configuration optimisée
        self.target_fps = 30
        self.frame_delay = 1.0 / self.target_fps
        self.max_frame_age = 0.1  # 100ms max
        
        # Taille optimisée pour le streaming web
        self.stream_width = 640
        self.stream_height = 480
        
        print("📹 CameraManager optimisé initialisé")
    
    def start(self) -> bool:
        """Démarrer la caméra avec optimisations"""
        if self.is_active:
            print("📹 Caméra déjà active")
            return True
        
        try:
            # Configuration optimisée de la caméra
            self.cap = cv2.VideoCapture(settings.CAMERA_INDEX, cv2.CAP_DSHOW)  # DirectShow sur Windows
            
            if not self.cap.isOpened():
                print(f" Impossible d'ouvrir la caméra à l'index {settings.CAMERA_INDEX}")
                # Essayer d'autres indices
                for i in range(1, 5):
                    print(f" Test caméra index {i}...")
                    self.cap = cv2.VideoCapture(i, cv2.CAP_DSHOW)
                    if self.cap.isOpened():
                        print(f" Caméra trouvée à l'index {i}")
                        settings.CAMERA_INDEX = i
                        break
                    self.cap.release()
                else:
                    print(" Aucune caméra trouvée")
                    return False
            
            # OPTIMISATIONS CRITIQUES
            # Réduire la résolution de capture pour améliorer les performances
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.stream_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.stream_height)
            
            # Optimiser le FPS
            self.cap.set(cv2.CAP_PROP_FPS, self.target_fps)
            
            # TRÈS IMPORTANT : Réduire le buffer au minimum
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Optimisations codec
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'))
            
            # Optimisations pour réduire la latence
            self.cap.set(cv2.CAP_PROP_AUTO_EXPOSURE, 0.25)  # Réduire l'auto-exposition
            
            # Tester la capture
            ret, test_frame = self.cap.read()
            if not ret:
                print(" Impossible de capturer depuis la caméra")
                self.cap.release()
                return False
            
            # Vérifier les paramètres réels
            actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            actual_fps = self.cap.get(cv2.CAP_PROP_FPS)
            
            print(f" Caméra configurée: {actual_width}x{actual_height} @ {actual_fps}fps")
            
            # Démarrer le thread de capture optimisé
            self.is_active = True
            self.capture_thread = threading.Thread(target=self._optimized_capture_loop, daemon=True)
            self.capture_thread.start()
            
            print(" Thread de capture optimisé démarré")
            return True
            
        except Exception as e:
            print(f" Erreur démarrage caméra: {e}")
            if self.cap:
                self.cap.release()
            return False
    
    def _optimized_capture_loop(self):
        """Boucle de capture ultra-optimisée"""
        print(" Démarrage de la boucle de capture optimisée")
        
        # Variables pour le contrôle du timing
        last_frame_time = time.time()
        frame_skip_count = 0
        max_skips = 2  # Skip maximum 2 frames si on est en retard
        
        while self.is_active and self.cap and self.cap.isOpened():
            try:
                current_time = time.time()
                
                # Lecture non-bloquante avec timeout
                ret, frame = self.cap.read()
                
                if ret and frame is not None:
                    # Redimensionner si nécessaire pour optimiser
                    if frame.shape[1] != self.stream_width or frame.shape[0] != self.stream_height:
                        frame = cv2.resize(frame, (self.stream_width, self.stream_height), 
                                         interpolation=cv2.INTER_LINEAR)
                    
                    # Mise à jour thread-safe ultra-rapide
                    with self.frame_lock:
                        self.frame = frame
                    
                    # Vider le buffer si trop plein (évite l'accumulation)
                    while not self.frame_buffer.empty():
                        try:
                            self.frame_buffer.get_nowait()
                        except queue.Empty:
                            break
                    
                    # Ajouter la nouvelle frame
                    try:
                        self.frame_buffer.put_nowait(frame)
                    except queue.Full:
                        pass  # Ignorer si le buffer est plein
                    
                    # Statistiques FPS
                    self.frame_count += 1
                    self.fps_frame_count += 1
                    
                    if current_time - self.last_fps_time >= 1.0:
                        self.fps = self.fps_frame_count / (current_time - self.last_fps_time)
                        self.fps_frame_count = 0
                        self.last_fps_time = current_time
                    
                    # Notifier les callbacks (de manière optimisée)
                    if self.callbacks and self.frame_count % 3 == 0:  # Callback 1 frame sur 3
                        try:
                            for callback in self.callbacks:
                                callback(frame)
                        except Exception as e:
                            # Ne pas laisser les erreurs callback bloquer la capture
                            pass
                    
                    # Contrôle de timing intelligent
                    elapsed = current_time - last_frame_time
                    if elapsed < self.frame_delay:
                        # On est en avance, attendre un peu
                        time.sleep(self.frame_delay - elapsed)
                        frame_skip_count = 0
                    elif elapsed > self.frame_delay * 2 and frame_skip_count < max_skips:
                        # On est en retard, skip la prochaine frame
                        frame_skip_count += 1
                        continue
                    else:
                        frame_skip_count = 0
                    
                    last_frame_time = time.time()
                
                else:
                    print("⚠ Échec de capture, pause...")
                    time.sleep(0.01)  # Pause courte
                    
            except Exception as e:
                print(f" Erreur dans la boucle de capture: {e}")
                time.sleep(0.01)
        
        print(" Boucle de capture optimisée terminée")
    
    def get_frame(self):
        """Obtenir la frame la plus récente"""
        with self.frame_lock:
            return self.frame.copy() if self.frame is not None else None
    
    def get_web_frame(self, max_width=640, quality=85):
        """Obtenir une frame optimisée pour le web avec compression"""
        with self.frame_lock:
            if self.frame is not None:
                frame = self.frame.copy()
                
                # Redimensionner si nécessaire
                h, w = frame.shape[:2]
                if w > max_width:
                    scale = max_width / w
                    new_h = int(h * scale)
                    frame = cv2.resize(frame, (max_width, new_h), 
                                     interpolation=cv2.INTER_AREA)  # INTER_AREA pour downscaling
                
                return frame
            return None
    
    def get_latest_frame_fast(self):
        """Version ultra-rapide pour le streaming"""
        try:
            return self.frame_buffer.get_nowait()
        except queue.Empty:
            return self.get_frame()
    
    def stop(self):
        """Arrêter la caméra"""
        if not self.is_active:
            return
        
        print(" Arrêt de la caméra optimisée...")
        self.is_active = False
        
        # Attendre que le thread se termine
        if self.capture_thread and self.capture_thread.is_alive():
            self.capture_thread.join(timeout=1.0)
        
        # Libérer la caméra
        if self.cap:
            self.cap.release()
            self.cap = None
        
        # Vider le buffer
        while not self.frame_buffer.empty():
            try:
                self.frame_buffer.get_nowait()
            except queue.Empty:
                break
        
        # Réinitialiser les variables
        with self.frame_lock:
            self.frame = None
        
        self.frame_count = 0
        print(" Caméra optimisée arrêtée")
    
    def add_callback(self, callback: Callable):
        """Ajouter un callback pour les nouvelles frames"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)
            print(f" Callback ajouté ({len(self.callbacks)} total)")
    
    def remove_callback(self, callback: Callable):
        """Supprimer un callback"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
            print(f" Callback supprimé ({len(self.callbacks)} restant)")
    
    def get_stats(self) -> dict:
        """Obtenir les statistiques de performance"""
        return {
            'is_active': self.is_active,
            'frame_count': self.frame_count,
            'fps': round(self.fps, 1),
            'target_fps': self.target_fps,
            'resolution': f"{self.stream_width}x{self.stream_height}",
            'callbacks_count': len(self.callbacks),
            'buffer_size': self.frame_buffer.qsize(),
            'has_frame': self.frame is not None
        }
    
    def __del__(self):
        """Destructeur pour s'assurer que la caméra est libérée"""
        self.stop()
