/**
 * SMART CLASSROOM - JavaScript Principal
 * Fonctions communes à toutes les pages
 */

// ================================
// VARIABLES GLOBALES
// ================================

let systemStatus = {
    camera: false,
    recognition: false,
    capture: false
};

// ================================
// SYSTÈME DE NOTIFICATIONS
// ================================

class NotificationManager {
    constructor() {
        this.container = document.getElementById('notification');
        this.queue = [];
        this.isShowing = false;
    }

    show(message, type = 'success', duration = 3000) {
        const notification = {
            message,
            type,
            duration,
            id: Date.now()
        };

        this.queue.push(notification);
        this.processQueue();
    }

    processQueue() {
        if (this.isShowing || this.queue.length === 0) return;

        const notification = this.queue.shift();
        this.displayNotification(notification);
    }

    displayNotification(notification) {
        if (!this.container) return;

        this.isShowing = true;
        this.container.textContent = notification.message;
        this.container.className = `notification show ${notification.type}`;

        // Auto-hide
        setTimeout(() => {
            this.hide();
        }, notification.duration);
    }

    hide() {
        if (!this.container) return;

        this.container.classList.remove('show');
        this.isShowing = false;

        // Process next notification
        setTimeout(() => {
            this.processQueue();
        }, 300);
    }

    success(message, duration = 3000) {
        this.show(message, 'success', duration);
    }

    error(message, duration = 5000) {
        this.show(message, 'error', duration);
    }

    warning(message, duration = 4000) {
        this.show(message, 'warning', duration);
    }

    info(message, duration = 3000) {
        this.show(message, 'info', duration);
    }
}

// Instance globale
const notifications = new NotificationManager();

// ================================
// GESTION DES REQUÊTES API
// ================================

class ApiClient {
    constructor(baseUrl = '') {
        this.baseUrl = baseUrl;
    }

    async request(url, options = {}) {
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        try {
            const response = await fetch(this.baseUrl + url, config);
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('application/json')) {
                return await response.json();
            }
            
            return await response.text();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    async get(url) {
        return this.request(url, { method: 'GET' });
    }

    async post(url, data = null) {
        const options = { method: 'POST' };
        if (data) {
            options.body = JSON.stringify(data);
        }
        return this.request(url, options);
    }

    async put(url, data) {
        return this.request(url, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(url) {
        return this.request(url, { method: 'DELETE' });
    }
}

// Instance globale
const api = new ApiClient();

// ================================
// GESTION DU SYSTÈME
// ================================

class SystemManager {
    constructor() {
        this.status = { ...systemStatus };
        this.updateInterval = null;
    }

    async initialize() {
        console.log('🚀 Initialisation du système...');
        
        try {
            await this.updateSystemStatus();
            this.startStatusMonitoring();
            this.setupEventListeners();
            
            notifications.success('Système initialisé avec succès');
            console.log('✅ Système initialisé');
        } catch (error) {
            console.error('❌ Erreur initialisation:', error);
            notifications.error('Erreur lors de l\'initialisation du système');
        }
    }

    async updateSystemStatus() {
        try {
            const response = await api.get('/api/system/status');
            this.status = {
                camera: response.camera_active || false,
                recognition: response.face_recognition_active || false,
                capture: response.capture_active || false,
                door: response.door_controller_connected || false
            };
            
            this.updateStatusIndicators();
        } catch (error) {
            console.error('Erreur mise à jour statut:', error);
        }
    }

    updateStatusIndicators() {
        // Mettre à jour les indicateurs visuels de statut
        this.updateIndicator('camera-status', this.status.camera);
        this.updateIndicator('recognition-status', this.status.recognition);
        this.updateIndicator('capture-status', this.status.capture);
        this.updateIndicator('door-status', this.status.door);
    }

    updateIndicator(elementId, isActive) {
        const element = document.getElementById(elementId);
        if (!element) return;

        const indicator = element.querySelector('.status-indicator');
        if (indicator) {
            indicator.className = `status-indicator ${isActive ? '' : 'inactive'}`;
        }

        const text = element.querySelector('.status-text');
        if (text) {
            text.textContent = isActive ? 'Actif' : 'Inactif';
        }
    }

    startStatusMonitoring() {
        // Mise à jour toutes les 5 secondes
        this.updateInterval = setInterval(() => {
            this.updateSystemStatus();
        }, 5000);
    }

    stopStatusMonitoring() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    setupEventListeners() {
        // Gestion de la fermeture de la page
        window.addEventListener('beforeunload', () => {
            this.stopStatusMonitoring();
        });

        // Gestion de la perte de focus
        document.addEventListener('visibilitychange', () => {
            if (document.visibilityState === 'visible') {
                this.updateSystemStatus();
            }
        });
    }
}

// ================================
// UTILITAIRES
// ================================

const Utils = {
    // Formater une date
    formatDate(date) {
        return new Date(date).toLocaleString('fr-FR', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    },

    // Formater une durée
    formatDuration(seconds) {
        const minutes = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${minutes}:${secs.toString().padStart(2, '0')}`;
    },

    // Débounce une fonction
    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },

    // Throttle une fonction
    throttle(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Valider un nom d'étudiant
    validateStudentName(name) {
        if (!name || name.trim().length === 0) {
            return { valid: false, message: 'Le nom est requis' };
        }
        
        if (name.trim().length < 2) {
            return { valid: false, message: 'Le nom doit contenir au moins 2 caractères' };
        }
        
        if (!/^[a-zA-Z0-9_\-\s]+$/.test(name)) {
            return { valid: false, message: 'Le nom contient des caractères non autorisés' };
        }
        
        return { valid: true };
    },

    // Nettoyer un nom d'étudiant
    sanitizeStudentName(name) {
        return name.trim()
                  .replace(/\s+/g, '_')
                  .replace(/[^a-zA-Z0-9_\-]/g, '')
                  .toLowerCase();
    },

    // Copier du texte dans le presse-papiers
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            notifications.success('Copié dans le presse-papiers');
        } catch (error) {
            console.error('Erreur copie:', error);
            notifications.error('Erreur lors de la copie');
        }
    },

    // Télécharger un fichier
    downloadFile(data, filename, type = 'application/json') {
        const blob = new Blob([data], { type });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};

// ================================
// GESTION DES MODALS
// ================================

class ModalManager {
    constructor() {
        this.activeModal = null;
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Fermer modal en cliquant à l'extérieur
        document.addEventListener('click', (event) => {
            if (event.target.classList.contains('modal') && this.activeModal) {
                this.close(this.activeModal);
            }
        });

        // Fermer modal avec Escape
        document.addEventListener('keydown', (event) => {
            if (event.key === 'Escape' && this.activeModal) {
                this.close(this.activeModal);
            }
        });
    }

    open(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) {
            console.error(`Modal ${modalId} non trouvée`);
            return;
        }

        // Fermer la modal active
        if (this.activeModal) {
            this.close(this.activeModal);
        }

        modal.style.display = 'block';
        modal.classList.add('fade-in');
        this.activeModal = modalId;

        // Focus sur le premier input
        const firstInput = modal.querySelector('input, select, textarea');
        if (firstInput) {
            setTimeout(() => firstInput.focus(), 100);
        }
    }

    close(modalId) {
        const modal = document.getElementById(modalId);
        if (!modal) return;

        modal.style.display = 'none';
        modal.classList.remove('fade-in');
        
        if (this.activeModal === modalId) {
            this.activeModal = null;
        }
    }

    closeAll() {
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.style.display = 'none';
            modal.classList.remove('fade-in');
        });
        this.activeModal = null;
    }
}

// ================================
// INITIALISATION
// ================================

// Instances globales
let systemManager;
let modalManager;

// Initialisation au chargement de la page
document.addEventListener('DOMContentLoaded', async function() {
    console.log('🚀 Chargement de Smart Classroom...');
    
    try {
        // Initialiser les managers
        systemManager = new SystemManager();
        modalManager = new ModalManager();
        
        // Initialiser le système
        await systemManager.initialize();
        
        // Afficher un message de bienvenue
        setTimeout(() => {
            notifications.info('Interface Smart Classroom chargée');
        }, 1000);
        
    } catch (error) {
        console.error('❌ Erreur lors du chargement:', error);
        notifications.error('Erreur lors du chargement de l\'interface');
    }
});

// ================================
// FONCTIONS GLOBALES (compatibilité)
// ================================

// Fonction globale pour afficher les notifications (rétrocompatibilité)
window.showNotification = function(message, type = 'success') {
    notifications.show(message, type);
};

// Fonctions modals (rétrocompatibilité)
window.openModal = function(modalId) {
    modalManager.open(modalId);
};

window.closeModal = function(modalId) {
    modalManager.close(modalId);
};