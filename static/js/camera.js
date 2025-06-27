/**
 * SMART CLASSROOM - JavaScript pour la Caméra
 * Gestion du flux vidéo et des contrôles caméra
 */

// ================================
// VARIABLES GLOBALES CAMÉRA
// ================================

let cameraActive = false;
let videoElement = null;
let videoPlaceholder = null;
let reconnectAttempts = 0;
let maxReconnectAttempts = 5;
let videoRefreshInterval = null;

// ================================
// INITIALISATION CAMÉRA
// ================================

function setupVideoStream() {
    videoElement = document.getElementById('videoStream');
    videoPlaceholder = document.getElementById('videoPlaceholder');
    
    if (!videoElement) {
        console.log('Élément vidéo non trouvé');
        return;
    }
    
    // Vérifier le statut initial
    checkCameraStatus();
    
    // Auto-refresh périodique
    startVideoRefreshMonitoring();
}

async function checkCameraStatus() {
    try {
        const response = await api.get('/api/camera/status');
        if (response.success) {
            cameraActive = response.active;
            updateCameraUI(response.active);
            
            if (response.active) {
                setTimeout(startVideoStream, 1000);
            }
        }
    } catch (error) {
        console.log('Status caméra non disponible:', error);
        updateCameraUI(false);
    }
}

// ================================
// CONTRÔLE DU FLUX VIDÉO
// ================================

function startVideoStream() {
    if (!videoElement) return;
    
    const timestamp = new Date().getTime();
    videoElement.src = `/api/camera/stream?t=${timestamp}`;
    
    // Optimisations navigateur
    videoElement.style.imageRendering = 'auto';
    videoElement.loading = 'eager';
    
    console.log('🎥 Stream vidéo démarré');
    reconnectAttempts = 0;
}

function stopVideoStream() {
    if (!videoElement) return;
    
    videoElement.src = '';
    videoElement.style.display = 'none';
    
    if (videoPlaceholder) {
        videoPlaceholder.style.display = 'flex';
        videoPlaceholder.innerHTML = '🎥 Caméra Arrêtée<br><small>Cliquez sur "Démarrer Caméra"</small>';
    }
}

function handleVideoLoad(img) {
    console.log('✅ Flux vidéo chargé avec succès');
    img.style.display = 'block';
    
    if (videoPlaceholder) {
        videoPlaceholder.style.display = 'none';
    }
    
    // Réinitialiser les tentatives de reconnexion
    reconnectAttempts = 0;
}

function handleVideoError(img) {
    console.log('⚠️ Erreur flux vidéo - tentative de reconnexion...');
    
    if (reconnectAttempts < maxReconnectAttempts && cameraActive) {
        reconnectAttempts++;
        
        // Reconnexion avec délai progressif
        setTimeout(() => {
            if (cameraActive) {
                startVideoStream();
            }
        }, 1000 * reconnectAttempts);
    } else {
        console.log('❌ Trop de tentatives de reconnexion');
        img.style.display = 'none';
        showVideoPlaceholder('Connexion échouée - Actualisez la page');
    }
}

function showVideoPlaceholder(message) {
    if (videoPlaceholder) {
        videoPlaceholder.style.display = 'flex';
        videoPlaceholder.innerHTML = `📷 ${message}`;
    }
}

// ================================
// CONTRÔLES CAMÉRA
// ================================

async function toggleCamera() {
    try {
        // Vérifier le statut actuel
        const status = await api.get('/api/camera/status');
        const isActive = status.success && status.active;
        
        // Choisir l'endpoint approprié
        const endpoint = isActive ? '/api/camera/stop' : '/api/camera/start';
        
        // Envoyer la commande
        const response = await api.post(endpoint);
        
        if (response.success) {
            cameraActive = !isActive;
            updateCameraUI(cameraActive);
            notifications.success(response.message);
            
            if (cameraActive) {
                setTimeout(startVideoStream, 1000);
            } else {
                stopVideoStream();
            }
        } else {
            notifications.error(response.message);
        }
    } catch (error) {
        console.error('Erreur toggle caméra:', error);
        notifications.error('Erreur de connexion au système');
    }
}

function updateCameraUI(isActive) {
    const button = document.getElementById('cameraBtn');
    
    if (button) {
        if (isActive) {
            button.textContent = 'Arrêter Caméra';
            button.className = 'btn btn-danger';
        } else {
            button.textContent = 'Démarrer Caméra';
            button.className = 'btn btn-success';
        }
    }
    
    // Mettre à jour les indicateurs de statut
    updateCameraStatusIndicators(isActive);
}

function updateCameraStatusIndicators(isActive) {
    // Mettre à jour tous les indicateurs de caméra sur la page
    const indicators = document.querySelectorAll('[id*="camera-status"]');
    indicators.forEach(indicator => {
        if (indicator.classList.contains('status-indicator')) {
            indicator.className = `status-indicator ${isActive ? '' : 'inactive'}`;
        } else if (indicator.classList.contains('status-text') || indicator.tagName === 'SPAN') {
            indicator.textContent = isActive ? 'Actif' : 'Inactif';
        }
    });
}

// ================================
// FONCTIONS UTILITAIRES CAMÉRA
// ================================

async function takeSnapshot() {
    try {
        const response = await api.get('/api/camera/snapshot');
        
        if (response.success) {
            // Créer un lien de téléchargement
            const link = document.createElement('a');
            link.href = response.image;
            
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            link.download = `smart_classroom_snapshot_${timestamp}.jpg`;
            
            // Déclencher le téléchargement
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            notifications.success('Snapshot sauvegardé');
        } else {
            notifications.error(response.message || 'Erreur lors du snapshot');
        }
    } catch (error) {
        console.error('Erreur snapshot:', error);
        notifications.error('Erreur lors du snapshot');
    }
}

function refreshStream() {
    if (cameraActive && videoElement) {
        startVideoStream();
        notifications.info('Flux vidéo actualisé');
    } else {
        notifications.error('Caméra non active');
    }
}

// ================================
// MONITORING ET MAINTENANCE
// ================================

function startVideoRefreshMonitoring() {
    // Vérifier périodiquement si le flux est toujours actif
    videoRefreshInterval = setInterval(() => {
        if (cameraActive && videoElement && videoElement.style.display === 'none') {
            console.log('🔄 Auto-refresh du stream vidéo');
            startVideoStream();
        }
    }, 15000); // Toutes les 15 secondes
}

function stopVideoRefreshMonitoring() {
    if (videoRefreshInterval) {
        clearInterval(videoRefreshInterval);
        videoRefreshInterval = null;
    }
}

// ================================
// GESTION DES ERREURS
// ================================

function handleCameraError(error, context = 'générique') {
    console.error(`Erreur caméra (${context}):`, error);
    
    // Gérer différents types d'erreurs
    if (error.message && error.message.includes('404')) {
        notifications.error('Service caméra non disponible');
    } else if (error.message && error.message.includes('timeout')) {
        notifications.warning('Timeout caméra - Vérifiez la connexion');
    } else {
        notifications.error(`Erreur caméra: ${error.message || 'Erreur inconnue'}`);
    }
    
    // Réinitialiser l'état si nécessaire
    cameraActive = false;
    updateCameraUI(false);
}

// ================================
// OPTIMISATIONS PERFORMANCE
// ================================

const CameraOptimizer = {
    // Réduire la qualité du stream pour économiser la bande passante
    setLowQuality() {
        if (videoElement) {
            videoElement.style.imageRendering = 'pixelated';
        }
    },
    
    // Restaurer la qualité normale
    setNormalQuality() {
        if (videoElement) {
            videoElement.style.imageRendering = 'auto';
        }
    },
    
    // Adapter la qualité selon la connexion
    adaptQuality() {
        // Estimer la qualité de connexion (simplifié)
        if (navigator.connection) {
            const connection = navigator.connection;
            if (connection.effectiveType === 'slow-2g' || connection.effectiveType === '2g') {
                this.setLowQuality();
            } else {
                this.setNormalQuality();
            }
        }
    }
};

// ================================
// DETECTION DE VISAGES (OPTIONNEL)
// ================================

const FaceDetectionOverlay = {
    canvas: null,
    context: null,
    
    init() {
        // Créer un canvas overlay pour afficher les détections de visages
        this.canvas = document.createElement('canvas');
        this.canvas.style.position = 'absolute';
        this.canvas.style.top = '0';
        this.canvas.style.left = '0';
        this.canvas.style.pointerEvents = 'none';
        this.canvas.style.zIndex = '10';
        
        this.context = this.canvas.getContext('2d');
        
        // Ajouter le canvas au container vidéo
        const videoContainer = document.querySelector('.video-container');
        if (videoContainer) {
            videoContainer.style.position = 'relative';
            videoContainer.appendChild(this.canvas);
        }
    },
    
    updateSize() {
        if (this.canvas && videoElement) {
            this.canvas.width = videoElement.offsetWidth;
            this.canvas.height = videoElement.offsetHeight;
        }
    },
    
    drawFaceBoxes(faces) {
        if (!this.context) return;
        
        // Effacer le canvas
        this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Dessiner les boîtes de détection
        this.context.strokeStyle = '#00ff00';
        this.context.lineWidth = 2;
        
        faces.forEach(face => {
            this.context.strokeRect(face.x, face.y, face.width, face.height);
        });
    },
    
    clear() {
        if (this.context) {
            this.context.clearRect(0, 0, this.canvas.width, this.canvas.height);
        }
    }
};

// ================================
// GESTION DES ÉVÉNEMENTS
// ================================

// Nettoyage lors de la fermeture de la page
window.addEventListener('beforeunload', () => {
    stopVideoRefreshMonitoring();
});

// Gestion de la perte/reprise de focus
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && cameraActive) {
        // Actualiser le flux quand la page redevient visible
        setTimeout(refreshStream, 1000);
    }
});

// Gestion du redimensionnement pour l'overlay
window.addEventListener('resize', Utils.debounce(() => {
    if (FaceDetectionOverlay.canvas) {
        FaceDetectionOverlay.updateSize();
    }
}, 250));

// ================================
// INITIALISATION AUTOMATIQUE
// ================================

// Auto-initialisation si on est sur une page avec vidéo
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('videoStream')) {
        setupVideoStream();
        CameraOptimizer.adaptQuality();
        
        // Initialiser l'overlay de détection si nécessaire
        if (document.querySelector('.face-guide-overlay')) {
            FaceDetectionOverlay.init();
        }
    }
});

// ================================
// EXPORT DES FONCTIONS GLOBALES
// ================================

// Rendre les fonctions principales disponibles globalement
window.cameraControls = {
    toggle: toggleCamera,
    snapshot: takeSnapshot,
    refresh: refreshStream,
    start: startVideoStream,
    stop: stopVideoStream,
    status: checkCameraStatus
};


/**
 * OPTIMISATIONS FRONTEND POUR RÉDUIRE LA LATENCE VIDÉO
 * Ajoutez ce code à votre camera.js ou utilisez-le pour remplacer les fonctions existantes
 */

// ================================
// GESTION OPTIMISÉE DU FLUX VIDÉO
// ================================

class OptimizedVideoStream {
    constructor(videoElementId, placeholderId) {
        this.videoElement = document.getElementById(videoElementId);
        this.placeholder = document.getElementById(placeholderId);
        this.isActive = false;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.streamUrl = '/api/camera/stream';
        this.fastStreamUrl = '/api/camera/stream/fast';
        this.useOptimizedStream = true;
        
        // Paramètres d'optimisation
        this.refreshInterval = null;
        this.errorTimeout = null;
        this.loadTimeout = null;
        
        this.init();
    }
    
    init() {
        if (!this.videoElement || !this.placeholder) {
            console.warn('Éléments vidéo non trouvés');
            return;
        }
        
        // Optimisations de l'élément img pour le streaming
        this.videoElement.style.imageRendering = 'auto';
        this.videoElement.style.objectFit = 'cover';
        this.videoElement.style.maxWidth = '100%';
        this.videoElement.style.height = 'auto';
        
        // Événements optimisés
        this.setupEventListeners();
        
        console.log('🎥 OptimizedVideoStream initialisé');
    }
    
    setupEventListeners() {
        // Événement de chargement réussi
        this.videoElement.onload = () => {
            this.handleSuccessfulLoad();
        };
        
        // Événement d'erreur avec retry intelligent
        this.videoElement.onerror = () => {
            this.handleLoadError();
        };
        
        // Détecter quand l'image s'arrête de se mettre à jour
        this.setupStagnationDetection();
        
        // Optimisation de la gestion de la mémoire
        this.setupMemoryOptimization();
    }
    
    setupStagnationDetection() {
        // Détecter si le stream se fige
        let lastImageData = null;
        let stagnationCount = 0;
        
        setInterval(() => {
            if (!this.isActive || !this.videoElement.complete) return;
            
            try {
                // Créer un canvas temporaire pour comparer les images
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                canvas.width = 50; // Petite taille pour performance
                canvas.height = 50;
                
                ctx.drawImage(this.videoElement, 0, 0, 50, 50);
                const currentImageData = ctx.getImageData(0, 0, 50, 50).data;
                
                if (lastImageData) {
                    // Comparer avec l'image précédente
                    let diff = 0;
                    for (let i = 0; i < currentImageData.length; i += 4) {
                        diff += Math.abs(currentImageData[i] - lastImageData[i]);
                    }
                    
                    if (diff < 100) { // Image identique
                        stagnationCount++;
                        if (stagnationCount > 5) { // 5 secondes sans changement
                            console.log('🔄 Stream figé détecté, redémarrage...');
                            this.refresh();
                            stagnationCount = 0;
                        }
                    } else {
                        stagnationCount = 0;
                    }
                }
                
                lastImageData = currentImageData;
                
            } catch (error) {
                // Ignorer les erreurs de comparaison
            }
        }, 1000); // Vérifier chaque seconde
    }
    
    setupMemoryOptimization() {
        // Nettoyer la mémoire périodiquement
        setInterval(() => {
            if (this.isActive && this.videoElement.src) {
                // Forcer le garbage collection du navigateur
                if (window.gc) {
                    window.gc();
                }
            }
        }, 30000); // Toutes les 30 secondes
    }
    
    start() {
        if (this.isActive) {
            console.log('Stream déjà actif');
            return;
        }
        
        this.isActive = true;
        this.reconnectAttempts = 0;
        
        console.log('🎥 Démarrage du stream optimisé');
        this.startStream();
        
        // Auto-refresh périodique pour maintenir la fraîcheur
        this.refreshInterval = setInterval(() => {
            this.refreshStream();
        }, 30000); // Refresh toutes les 30 secondes
    }
    
    startStream() {
        if (!this.isActive) return;
        
        // Choisir l'URL optimisée selon les performances
        const streamUrl = this.useOptimizedStream ? this.fastStreamUrl : this.streamUrl;
        const timestamp = Date.now();
        
        // Timeout pour le chargement
        this.loadTimeout = setTimeout(() => {
            if (this.videoElement.style.display === 'none') {
                console.log('⏱️ Timeout de chargement, retry...');
                this.handleLoadError();
            }
        }, 5000);
        
        this.videoElement.src = `${streamUrl}?t=${timestamp}&cache=${Math.random()}`;
        
        console.log(`🔗 Stream démarré: ${streamUrl}`);
    }
    
    handleSuccessfulLoad() {
        console.log('✅ Stream chargé avec succès');
        
        // Afficher la vidéo
        this.videoElement.style.display = 'block';
        this.placeholder.style.display = 'none';
        
        // Réinitialiser les compteurs d'erreur
        this.reconnectAttempts = 0;
        
        // Annuler le timeout de chargement
        if (this.loadTimeout) {
            clearTimeout(this.loadTimeout);
            this.loadTimeout = null;
        }
        
        // Optimisation: Précharger la prochaine frame
        this.preloadNextFrame();
    }
    
    preloadNextFrame() {
        // Technique pour réduire la latence en préchargeant
        if (!this.isActive) return;
        
        setTimeout(() => {
            if (this.isActive && this.videoElement.complete) {
                const preloadImg = new Image();
                preloadImg.src = this.videoElement.src + '&preload=' + Date.now();
            }
        }, 100);
    }
    
    handleLoadError() {
        console.log('⚠️ Erreur de chargement du stream');
        
        // Masquer la vidéo, afficher le placeholder
        this.videoElement.style.display = 'none';
        this.placeholder.style.display = 'flex';
        this.placeholder.innerHTML = '📷 Reconnexion...<br><small>Tentative ' + (this.reconnectAttempts + 1) + '</small>';
        
        // Annuler les timeouts en cours
        if (this.loadTimeout) {
            clearTimeout(this.loadTimeout);
            this.loadTimeout = null;
        }
        
        if (this.errorTimeout) {
            clearTimeout(this.errorTimeout);
        }
        
        // Retry avec délai progressif
        if (this.reconnectAttempts < this.maxReconnectAttempts && this.isActive) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * this.reconnectAttempts, 5000); // Max 5 secondes
            
            this.errorTimeout = setTimeout(() => {
                if (this.isActive) {
                    console.log(`🔄 Tentative de reconnexion ${this.reconnectAttempts}`);
                    this.startStream();
                }
            }, delay);
        } else {
            console.log('❌ Trop de tentatives de reconnexion');
            this.placeholder.innerHTML = '📷 Erreur de connexion<br><small>Cliquez sur "Actualiser" pour réessayer</small>';
        }
    }
    
    refresh() {
        console.log('🔄 Actualisation du stream');
        this.reconnectAttempts = 0;
        
        if (this.isActive) {
            this.startStream();
        }
    }
    
    refreshStream() {
        // Refresh périodique moins agressif
        if (this.isActive && this.videoElement.style.display !== 'none') {
            this.refresh();
        }
    }
    
    stop() {
        console.log('🛑 Arrêt du stream optimisé');
        
        this.isActive = false;
        
        // Nettoyer les timeouts
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
        
        if (this.errorTimeout) {
            clearTimeout(this.errorTimeout);
            this.errorTimeout = null;
        }
        
        if (this.loadTimeout) {
            clearTimeout(this.loadTimeout);
            this.loadTimeout = null;
        }
        
        // Arrêter le stream
        this.videoElement.src = '';
        this.videoElement.style.display = 'none';
        this.placeholder.style.display = 'flex';
        this.placeholder.innerHTML = '🎥 Stream arrêté<br><small>Cliquez sur "Démarrer Caméra"</small>';
    }
    
    toggleOptimization() {
        this.useOptimizedStream = !this.useOptimizedStream;
        console.log(`🔧 Stream ${this.useOptimizedStream ? 'optimisé' : 'normal'} activé`);
        
        if (this.isActive) {
            this.refresh();
        }
    }
}

// ================================
// INTÉGRATION AVEC LE CODE EXISTANT
// ================================

// Instance globale
let optimizedVideoStream = null;

// Fonction pour remplacer setupVideoStream()
function setupOptimizedVideoStream() {
    optimizedVideoStream = new OptimizedVideoStream('videoStream', 'videoPlaceholder');
    
    // Vérifier le statut initial
    checkCameraStatus().then(isActive => {
        if (isActive) {
            setTimeout(() => {
                optimizedVideoStream.start();
            }, 1000);
        }
    });
}

// Fonctions optimisées pour remplacer les existantes
function startVideoStreamOptimized() {
    if (optimizedVideoStream) {
        optimizedVideoStream.start();
    } else {
        setupOptimizedVideoStream();
    }
}

function stopVideoStreamOptimized() {
    if (optimizedVideoStream) {
        optimizedVideoStream.stop();
    }
}

function refreshStreamOptimized() {
    if (optimizedVideoStream) {
        optimizedVideoStream.refresh();
    }
}

// ================================
// OPTIMISATIONS SUPPLÉMENTAIRES
// ================================

// Détection de la bande passante pour adapter la qualité
class BandwidthDetector {
    constructor() {
        this.isDetecting = false;
        this.bandwidth = 'unknown';
    }
    
    async detectBandwidth() {
        if (this.isDetecting) return this.bandwidth;
        
        this.isDetecting = true;
        
        try {
            const startTime = Date.now();
            const response = await fetch('/api/camera/snapshot', { 
                cache: 'no-cache',
                method: 'GET'
            });
            
            if (response.ok) {
                const blob = await response.blob();
                const endTime = Date.now();
                const duration = endTime - startTime;
                const sizeKB = blob.size / 1024;
                const speedKBps = sizeKB / (duration / 1000);
                
                if (speedKBps > 500) {
                    this.bandwidth = 'high';
                } else if (speedKBps > 200) {
                    this.bandwidth = 'medium';
                } else {
                    this.bandwidth = 'low';
                }
                
                console.log(`📊 Bande passante détectée: ${this.bandwidth} (${speedKBps.toFixed(1)} KB/s)`);
            }
        } catch (error) {
            console.log('Erreur détection bande passante:', error);
            this.bandwidth = 'medium'; // Valeur par défaut
        }
        
        this.isDetecting = false;
        return this.bandwidth;
    }
    
    getOptimalStreamUrl() {
        switch (this.bandwidth) {
            case 'high':
                return '/api/camera/stream';
            case 'medium':
                return '/api/camera/stream/fast';
            case 'low':
                return '/api/camera/stream/fast';
            default:
                return '/api/camera/stream/fast';
        }
    }
}

// Instance globale du détecteur
const bandwidthDetector = new BandwidthDetector();

// ================================
// OPTIMISATIONS DE PERFORMANCE
// ================================

// Throttle pour éviter trop de requêtes
function throttle(func, limit) {
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
}

// Debounce pour les actions utilisateur
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Optimisation des requêtes réseau
const optimizedFetch = throttle(async (url, options = {}) => {
    try {
        const response = await fetch(url, {
            ...options,
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                ...options.headers
            }
        });
        return response;
    } catch (error) {
        console.error('Erreur requête optimisée:', error);
        throw error;
    }
}, 100); // Maximum 1 requête par 100ms

// ================================
// GESTION INTELLIGENTE DE LA QUALITÉ
// ================================

class QualityManager {
    constructor() {
        this.currentQuality = 'auto';
        this.frameDropCount = 0;
        this.lastFrameTime = 0;
        this.performanceMode = false;
    }
    
    analyzePerformance() {
        const now = Date.now();
        const timeSinceLastFrame = now - this.lastFrameTime;
        
        if (timeSinceLastFrame > 200) { // Plus de 200ms = frame drop
            this.frameDropCount++;
            
            if (this.frameDropCount > 5 && !this.performanceMode) {
                console.log('🐌 Performance dégradée détectée, activation du mode performance');
                this.enablePerformanceMode();
            }
        } else {
            this.frameDropCount = Math.max(0, this.frameDropCount - 1);
            
            if (this.frameDropCount === 0 && this.performanceMode) {
                console.log('🚀 Performance restaurée, désactivation du mode performance');
                this.disablePerformanceMode();
            }
        }
        
        this.lastFrameTime = now;
    }
    
    enablePerformanceMode() {
        this.performanceMode = true;
        
        // Réduire la qualité du stream
        if (optimizedVideoStream) {
            optimizedVideoStream.fastStreamUrl = '/api/camera/stream/fast';
            optimizedVideoStream.useOptimizedStream = true;
            optimizedVideoStream.refresh();
        }
        
        // Réduire la fréquence des mises à jour
        document.body.classList.add('performance-mode');
    }
    
    disablePerformanceMode() {
        this.performanceMode = false;
        
        // Restaurer la qualité normale
        if (optimizedVideoStream) {
            optimizedVideoStream.useOptimizedStream = false;
            optimizedVideoStream.refresh();
        }
        
        document.body.classList.remove('performance-mode');
    }
}

// Instance globale du gestionnaire de qualité
const qualityManager = new QualityManager();

// ================================
// INITIALISATION AUTOMATIQUE
// ================================

// Remplacer l'initialisation existante
document.addEventListener('DOMContentLoaded', async () => {
    console.log('🚀 Initialisation des optimisations vidéo');
    
    // Détecter la bande passante
    await bandwidthDetector.detectBandwidth();
    
    // Initialiser le stream optimisé
    if (document.getElementById('videoStream')) {
        setupOptimizedVideoStream();
        
        // Démarrer l'analyse de performance
        setInterval(() => {
            qualityManager.analyzePerformance();
        }, 1000);
    }
    
    // Optimisations CSS pour la performance
    addPerformanceCSS();
});

function addPerformanceCSS() {
    const style = document.createElement('style');
    style.textContent = `
        /* Optimisations CSS pour la performance */
        .video-container img {
            will-change: auto;
            transform: translateZ(0); /* Force hardware acceleration */
            backface-visibility: hidden;
        }
        
        .performance-mode .video-container img {
            image-rendering: pixelated; /* Moins de lissage = plus rapide */
        }
        
        .video-placeholder {
            transition: opacity 0.3s ease;
        }
        
        /* Réduire les animations en mode performance */
        .performance-mode * {
            animation-duration: 0.1s !important;
            transition-duration: 0.1s !important;
        }
    `;
    document.head.appendChild(style);
}

// ================================
// FONCTIONS DE DIAGNOSTIC
// ================================

function diagnoseStreamPerformance() {
    console.log('🔍 Diagnostic de performance du stream:');
    console.log('- Bande passante:', bandwidthDetector.bandwidth);
    console.log('- Mode performance:', qualityManager.performanceMode);
    console.log('- Frame drops:', qualityManager.frameDropCount);
    console.log('- Stream actif:', optimizedVideoStream?.isActive);
    console.log('- Tentatives de reconnexion:', optimizedVideoStream?.reconnectAttempts);
    
    if (optimizedVideoStream?.videoElement) {
        const img = optimizedVideoStream.videoElement;
        console.log('- Image chargée:', img.complete);
        console.log('- Dimensions:', img.naturalWidth, 'x', img.naturalHeight);
        console.log('- URL actuelle:', img.src.substring(0, 100) + '...');
    }
}

// Fonction utilitaire pour tester différentes qualités
function testStreamQuality(quality = 'fast') {
    if (!optimizedVideoStream) return;
    
    console.log(`🧪 Test de qualité: ${quality}`);
    
    switch (quality) {
        case 'fast':
            optimizedVideoStream.streamUrl = '/api/camera/stream/fast';
            optimizedVideoStream.useOptimizedStream = true;
            break;
        case 'normal':
            optimizedVideoStream.streamUrl = '/api/camera/stream';
            optimizedVideoStream.useOptimizedStream = false;
            break;
        case 'auto':
            optimizedVideoStream.streamUrl = bandwidthDetector.getOptimalStreamUrl();
            break;
    }
    
    optimizedVideoStream.refresh();
}

// ================================
// EXPORT DES FONCTIONS GLOBALES
// ================================

// Rendre les fonctions disponibles globalement pour compatibilité
window.videoStreamOptimizations = {
    start: startVideoStreamOptimized,
    stop: stopVideoStreamOptimized,
    refresh: refreshStreamOptimized,
    diagnose: diagnoseStreamPerformance,
    testQuality: testStreamQuality,
    toggleOptimization: () => optimizedVideoStream?.toggleOptimization()
};