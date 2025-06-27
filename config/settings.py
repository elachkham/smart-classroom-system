import os
from pathlib import Path

class Settings:
    """Configuration centralisée du système"""
    
    # Chemins
    BASE_DIR = Path(__file__).parent.parent
    DATASET_PATH = BASE_DIR / "dataset"
    LOGS_PATH = BASE_DIR / "logs"
    EDT_PATH = BASE_DIR / "data" / "edt.csv"
    
    # Caméra
    CAMERA_INDEX = 0
    CAMERA_WIDTH = 640
    CAMERA_HEIGHT = 480
    
    # Reconnaissance faciale
    RECOGNITION_MODEL = "VGG-Face"
    RECOGNITION_THRESHOLD = 60
    DETECTION_INTERVAL = 60
    COOLDOWN_SECONDS = 5
    
    # Suivi d'attention
    WINDOW_SIZE = 30
    ATTENTION_THRESHOLD_MULTIPLIER = 1.5
    CALIBRATION_DURATION = 2.0
    
    # Communication série
    SERIAL_PORT = "COM5"
    BAUD_RATE = 9600
    
    # API
    API_HOST = "localhost"
    API_PORT = 8000
    DEBUG = True
    
    @classmethod
    def create_directories(cls):
        """Créer les dossiers nécessaires"""
        for path in [cls.DATASET_PATH, cls.LOGS_PATH]:
            path.mkdir(parents=True, exist_ok=True)

settings = Settings()

class OptimizedSettings:
    # Performance
    FAST_MODE = True
    WEB_STREAM_FPS = 15      # FPS pour le web (au lieu de 30)
    PROCESSING_FPS = 2       # FPS pour analyses lourdes
    DETECTION_INTERVAL = 150 # Frames entre détections (au lieu de 60)
    
    # Qualité vs Performance
    WEB_RESOLUTION = 480     # Largeur max pour web
    JPEG_QUALITY = 70        # Qualité JPEG (70 = bon compromis)
    
    # Seuils optimisés
    MIN_FACE_SIZE = 5000  



# Optimisations caméra
CAMERA_BUFFER_SIZE = 1  # Buffer minimal
CAMERA_FPS = 30
STREAM_QUALITY = 75  # Qualité JPEG (0-100)
STREAM_WIDTH = 640
STREAM_HEIGHT = 480

# Optimisations réseau
STREAM_CHUNK_SIZE = 1024
MAX_FRAME_AGE = 0.1  # 100ms max