import serial
import time
from typing import Optional
from config.settings import settings
from data.models import AccessRecord
from datetime import datetime

class DoorController:
    """Contrôleur de porte via Arduino"""
    
    def __init__(self, logger):
        self.logger = logger
        self.serial_connection: Optional[serial.Serial] = None
        self.is_connected = False
    
    def connect(self) -> bool:
        """Se connecter à l'Arduino"""
        try:
            self.serial_connection = serial.Serial(
                settings.SERIAL_PORT, 
                settings.BAUD_RATE,
                timeout=1
            )
            time.sleep(2)  # Attendre la connexion
            self.is_connected = True
            return True
        except Exception as e:
            print(f"Erreur connexion Arduino: {e}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Fermer la connexion"""
        if self.serial_connection:
            self.serial_connection.close()
        self.is_connected = False
    
    def open_door(self, student_name: Optional[str] = None, reason: str = "access_granted") -> bool:
        """Ouvrir la porte"""
        if not self.is_connected:
            return False
        
        try:
            self.serial_connection.write(b"MOVE\n")
            self.serial_connection.write(b"OK\n")
            
            # Enregistrer l'accès
            record = AccessRecord(
                timestamp=datetime.now(),
                student_name=student_name,
                action="granted",
                reason=reason
            )
            self.logger.log_access(record)
            
            return True
        except Exception as e:
            print(f"Erreur ouverture porte: {e}")
            return False
    
    def send_alert(self, alert_type: str) -> bool:
        """Envoyer une alerte"""
        if not self.is_connected:
            return False
        
        try:
            if alert_type == "unknown":
                self.serial_connection.write(b"INCONNU\n")
            elif alert_type == "error":
                self.serial_connection.write(b"ERREUR\n")
            
            # Enregistrer l'alerte
            record = AccessRecord(
                timestamp=datetime.now(),
                student_name=None,
                action="denied",
                reason=alert_type
            )
            self.logger.log_access(record)
            
            return True
        except Exception as e:
            print(f"Erreur envoi alerte: {e}")
            return False
