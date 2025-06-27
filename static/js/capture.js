/**
 * SMART CLASSROOM - JavaScript pour la Capture (VERSION COMPLÈTE)
 * Gestion de la capture d'étudiants et de la liste
 */

// ================================
// VARIABLES GLOBALES
// ================================

let captureInterval = null;
let studentsData = [];
let currentPage = 1;
const studentsPerPage = 10;
let captureActive = false;
let captureData = {
    studentName: '',
    totalImages: 20,
    capturedImages: 0,
    mode: 'manual'
};

// ================================
// GESTION DE LA CAMÉRA POUR CAPTURE
// ================================

async function checkCameraStatusForCapture() {
    try {
        const response = await api.get('/api/camera/status');
        updateCameraUI(response.success && response.active);
        
        if (response.success && response.active) {
            setTimeout(startCaptureVideoStream, 1000);
        }
    } catch (error) {
        console.log('Caméra non disponible pour capture:', error);
        updateCameraUI(false);
    }
}

function updateCameraUI(isActive) {
    const button = document.getElementById('captureCameraBtn');
    const statusText = document.getElementById('cameraStatusText');
    const statusIndicator = document.getElementById('cameraStatusIndicator');
    
    if (button) {
        if (isActive) {
            button.textContent = 'Arrêter Caméra';
            button.className = 'btn btn-danger';
        } else {
            button.textContent = 'Démarrer Caméra';
            button.className = 'btn btn-success';
        }
    }
    
    if (statusText) {
        statusText.textContent = isActive ? 'Actif' : 'Inactif';
    }
    
    if (statusIndicator) {
        statusIndicator.className = `status-indicator ${isActive ? '' : 'inactive'}`;
    }
}

async function toggleCaptureCamera() {
    try {
        const status = await api.get('/api/camera/status');
        const isActive = status.success && status.active;
        const endpoint = isActive ? '/api/camera/stop' : '/api/camera/start';
        
        const response = await api.post(endpoint);
        
        if (response.success) {
            updateCameraUI(!isActive);
            notifications.success(response.message);
            
            if (!isActive) {
                setTimeout(startCaptureVideoStream, 1000);
            } else {
                stopCaptureVideoStream();
            }
        } else {
            notifications.error(response.message);
        }
    } catch (error) {
        notifications.error('Erreur de contrôle caméra');
    }
}

function startCaptureVideoStream() {
    const videoElement = document.getElementById('captureVideoStream');
    const placeholder = document.getElementById('captureVideoPlaceholder');
    
    if (videoElement) {
        const timestamp = new Date().getTime();
        videoElement.src = `/api/camera/stream?t=${timestamp}`;
    }
}

function stopCaptureVideoStream() {
    const videoElement = document.getElementById('captureVideoStream');
    const placeholder = document.getElementById('captureVideoPlaceholder');
    
    if (videoElement) {
        videoElement.src = '';
        videoElement.style.display = 'none';
        if (placeholder) {
            placeholder.style.display = 'flex';
        }
    }
}

function handleCaptureVideoLoad(img) {
    img.style.display = 'block';
    const placeholder = document.getElementById('captureVideoPlaceholder');
    if (placeholder) {
        placeholder.style.display = 'none';
    }
    console.log('✅ Flux vidéo de capture chargé');
}

function handleCaptureVideoError(img) {
    img.style.display = 'none';
    const placeholder = document.getElementById('captureVideoPlaceholder');
    if (placeholder) {
        placeholder.style.display = 'flex';
        placeholder.innerHTML = '📷 Flux Non Disponible<br><small>Vérifiez que la caméra est active</small>';
    }
}

function refreshCaptureStream() {
    startCaptureVideoStream();
    notifications.info('Flux vidéo actualisé');
}

function calibrateCamera() {
    notifications.info('Calibration caméra - Fonction à implémenter');
}

// ================================
// GESTION DE LA CAPTURE WEB
// ================================

async function startWebCapture() {
    const studentName = document.getElementById('studentName').value.trim();
    const imageCount = parseInt(document.getElementById('imageCount').value);
    const mode = document.getElementById('captureMode').value;
    
    // Validation
    if (!studentName) {
        notifications.error('Veuillez entrer un nom d\'étudiant');
        document.getElementById('studentName').focus();
        return;
    }
    
    const validation = Utils.validateStudentName(studentName);
    if (!validation.valid) {
        notifications.error(validation.message);
        document.getElementById('studentName').focus();
        return;
    }
    
    // Vérifier que la caméra est active
    try {
        const cameraStatus = await api.get('/api/camera/status');
        if (!cameraStatus.success || !cameraStatus.active) {
            notifications.error('Veuillez d\'abord démarrer la caméra');
            return;
        }
    } catch (error) {
        notifications.error('Erreur de vérification caméra');
        return;
    }
    
    try {
        // Nettoyer le nom
        const cleanName = Utils.sanitizeStudentName(studentName);
        
        // Démarrer la capture
        const response = await api.post('/api/students/capture/start', {
            name: cleanName,
            num_images: imageCount,
            mode: mode
        });
        
        if (response.success) {
            // Mettre à jour les données de capture
            captureData = {
                studentName: cleanName,
                totalImages: imageCount,
                capturedImages: 0,
                mode: mode
            };
            
            // Basculer vers l'interface de capture
            switchToCaptureInterface();
            
            // Démarrer le monitoring
            startCaptureStatusMonitoring();
            
            notifications.success('Capture démarrée !');
        } else {
            notifications.error(response.message || 'Erreur de démarrage');
        }
    } catch (error) {
        notifications.error('Erreur lors du démarrage de la capture');
        console.error('Erreur capture:', error);
    }
}

function switchToCaptureInterface() {
    // Masquer la configuration
    document.getElementById('captureSetup').style.display = 'none';
    
    // Afficher l'interface de capture
    const captureInterface = document.getElementById('captureInterface');
    captureInterface.style.display = 'block';
    captureInterface.classList.add('fade-in');
    
    // Mettre à jour les informations
    document.getElementById('captureTitle').textContent = `Capture: ${captureData.studentName}`;
    document.getElementById('captureTotal').textContent = captureData.totalImages;
    document.getElementById('captureCount').textContent = '0';
    document.getElementById('captureProgress').style.width = '0%';
    
    captureActive = true;
    
    // Configurer l'interface selon le mode
    updateCaptureInterface();
}

function updateCaptureInterface() {
    const isManual = captureData.mode === 'manual';
    const captureBtn = document.getElementById('captureBtn');
    const tips = document.getElementById('captureTips');
    
    if (captureBtn) {
        captureBtn.style.display = isManual ? 'block' : 'none';
    }
    
    if (tips) {
        if (isManual) {
            tips.innerHTML = `
                <h4>💡 Mode Manuel:</h4>
                <ul>
                    <li>📷 Positionnez-vous face à la caméra</li>
                    <li>🖱️ Cliquez sur "Capturer Image" quand vous êtes prêt</li>
                    <li>😊 Variez légèrement les expressions entre les captures</li>
                    <li>⏱️ Prenez votre temps pour chaque image</li>
                </ul>
            `;
        } else {
            tips.innerHTML = `
                <h4>🤖 Mode Automatique:</h4>
                <ul>
                    <li>📷 Restez face à la caméra</li>
                    <li>⏱️ Une image sera prise toutes les 2 secondes</li>
                    <li>😊 Bougez légèrement entre les captures</li>
                    <li>⏸️ Utilisez "Pause" si nécessaire</li>
                </ul>
            `;
        }
    }
}

async function triggerCapture() {
    if (!captureActive) return;
    
    const btn = document.getElementById('captureBtn');
    if (!btn) return;
    
    const originalText = btn.textContent;
    
    btn.disabled = true;
    btn.textContent = '📸 Capture...';
    
    try {
        const response = await api.post('/api/students/capture/trigger');
        
        if (response.success) {
            notifications.success('Image capturée !');
            // La mise à jour sera faite via le monitoring
        } else {
            notifications.error(response.message || 'Erreur de capture');
        }
    } catch (error) {
        notifications.error('Erreur lors de la capture');
        console.error('Erreur trigger:', error);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

async function stopWebCapture() {
    try {
        const response = await api.post('/api/students/capture/stop');
        
        notifications.info(response.message || 'Capture arrêtée');
        resetCaptureInterface();
        
        // Recharger la liste des étudiants
        setTimeout(loadStudentsList, 1000);
        
    } catch (error) {
        notifications.error('Erreur lors de l\'arrêt');
    }
}

function pauseCapture() {
    // Fonction pour mettre en pause/reprendre la capture automatique
    if (captureData.mode === 'auto') {
        // Logique de pause pour mode auto
        notifications.info('Pause/Reprise - À implémenter');
    } else {
        notifications.info('La pause n\'est disponible qu\'en mode automatique');
    }
}

function resetCaptureInterface() {
    captureActive = false;
    
    // Arrêter le monitoring
    if (captureInterval) {
        clearInterval(captureInterval);
        captureInterval = null;
    }
    
    // Réafficher la configuration
    const setupElement = document.getElementById('captureSetup');
    const interfaceElement = document.getElementById('captureInterface');
    
    if (setupElement) setupElement.style.display = 'block';
    if (interfaceElement) interfaceElement.style.display = 'none';
    
    // Réinitialiser les champs
    const studentNameInput = document.getElementById('studentName');
    const progressBar = document.getElementById('captureProgress');
    
    if (studentNameInput) studentNameInput.value = '';
    if (progressBar) progressBar.style.width = '0%';
    
    // Réinitialiser les données
    captureData = {
        studentName: '',
        totalImages: 20,
        capturedImages: 0,
        mode: 'manual'
    };
}

function startCaptureStatusMonitoring() {
    // Surveiller le statut de capture toutes les secondes
    captureInterval = setInterval(async () => {
        if (!captureActive) {
            clearInterval(captureInterval);
            return;
        }
        
        try {
            const response = await api.get('/api/students/capture/status');
            
            if (response.success && response.status) {
                updateCaptureUI(response.status);
                
                // Vérifier si la capture est terminée
                if (!response.status.active && captureActive) {
                    setTimeout(() => {
                        resetCaptureInterface();
                        notifications.success('Capture terminée avec succès !');
                    }, 2000);
                }
            }
        } catch (error) {
            console.error('Erreur monitoring capture:', error);
        }
    }, 1000);
}

function updateCaptureUI(status) {
    if (!status) return;
    
    // Mettre à jour les compteurs
    const countElement = document.getElementById('captureCount');
    const messageElement = document.getElementById('captureMessage');
    const progressBar = document.getElementById('captureProgress');
    
    if (countElement) {
        countElement.textContent = status.images_captured || 0;
    }
    
    if (messageElement) {
        messageElement.textContent = status.message || 'Capture en cours...';
    }
    
    // Mettre à jour la barre de progression
    if (progressBar) {
        const progress = ((status.images_captured || 0) / (status.total_images || 1)) * 100;
        progressBar.style.width = progress + '%';
        
        // Changer la couleur selon le progrès
        if (progress >= 100) {
            progressBar.style.background = '#28a745';
        } else if (progress >= 50) {
            progressBar.style.background = '#ffc107';
        } else {
            progressBar.style.background = '#007bff';
        }
    }
    
    // Mettre à jour les données locales
    captureData.capturedImages = status.images_captured || 0;
}

// ================================
// GESTION DES ÉTUDIANTS
// ================================

async function loadStudentsList() {
    try {
        const listElement = document.getElementById('studentsList');
        if (listElement) {
            listElement.innerHTML = '<div class="loading-message">Chargement des étudiants...</div>';
        }
        
        const response = await api.get('/api/students');
        studentsData = response.students || [];
        
        displayStudentsList();
        updatePagination();
        
    } catch (error) {
        console.error('Erreur chargement étudiants:', error);
        const listElement = document.getElementById('studentsList');
        if (listElement) {
            listElement.innerHTML = 
                '<div class="error-message">Erreur de chargement des étudiants</div>';
        }
    }
}

function displayStudentsList() {
    const container = document.getElementById('studentsList');
    if (!container) return;
    
    if (studentsData.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">👥</div>
                <h3>Aucun étudiant enregistré</h3>
                <p>Commencez par capturer votre premier étudiant</p>
            </div>
        `;
        return;
    }
    
    // Pagination
    const startIndex = (currentPage - 1) * studentsPerPage;
    const endIndex = startIndex + studentsPerPage;
    const currentStudents = studentsData.slice(startIndex, endIndex);
    
    const studentsHTML = currentStudents.map(student => `
        <div class="student-card" data-student="${student.name}">
            <div class="student-info">
                <div class="student-name">${student.name}</div>
                <div class="student-details">
                    <span class="detail-item">📸 ${student.image_count} images</span>
                    <span class="detail-item">📅 ${Utils.formatDate(student.created_at)}</span>
                </div>
            </div>
            <div class="student-actions">
                <button class="btn btn-sm" onclick="viewStudentDetails('${student.name}')">
                    👁️ Voir
                </button>
                <button class="btn btn-sm btn-warning" onclick="editStudent('${student.name}')">
                    ✏️ Modifier
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteStudent('${student.name}')">
                    🗑️ Supprimer
                </button>
            </div>
        </div>
    `).join('');
    
    container.innerHTML = studentsHTML;
}

function updatePagination() {
    const totalPages = Math.ceil(studentsData.length / studentsPerPage);
    const pagination = document.getElementById('studentsPagination');
    
    if (!pagination) return;
    
    if (totalPages <= 1) {
        pagination.style.display = 'none';
        return;
    }
    
    pagination.style.display = 'flex';
    
    const currentPageElement = document.getElementById('currentPage');
    const totalPagesElement = document.getElementById('totalPages');
    
    if (currentPageElement) currentPageElement.textContent = currentPage;
    if (totalPagesElement) totalPagesElement.textContent = totalPages;
    
    // Activer/désactiver les boutons
    const prevBtn = pagination.querySelector('button:first-child');
    const nextBtn = pagination.querySelector('button:last-child');
    
    if (prevBtn) prevBtn.disabled = currentPage === 1;
    if (nextBtn) nextBtn.disabled = currentPage === totalPages;
}

function previousPage() {
    if (currentPage > 1) {
        currentPage--;
        displayStudentsList();
        updatePagination();
    }
}

function nextPage() {
    const totalPages = Math.ceil(studentsData.length / studentsPerPage);
    if (currentPage < totalPages) {
        currentPage++;
        displayStudentsList();
        updatePagination();
    }
}

function refreshStudentsList() {
    notifications.info('Actualisation de la liste...');
    currentPage = 1; // Reset à la première page
    loadStudentsList();
}

// ================================
// ACTIONS SUR LES ÉTUDIANTS
// ================================

function viewStudentDetails(studentName) {
    const student = studentsData.find(s => s.name === studentName);
    if (!student) {
        notifications.error('Étudiant non trouvé');
        return;
    }
    
    // Créer un modal avec les détails
    const modalContent = `
        <div class="student-details-modal">
            <h3>👤 ${student.name}</h3>
            <div class="details-grid">
                <div class="detail-row">
                    <span class="label">Images:</span>
                    <span class="value">${student.image_count}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Créé le:</span>
                    <span class="value">${Utils.formatDate(student.created_at)}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Dernière mise à jour:</span>
                    <span class="value">${Utils.formatDate(student.last_updated)}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Dossier:</span>
                    <span class="value">${student.folder_path}</span>
                </div>
            </div>
            <div class="images-preview">
                <h4>Images enregistrées:</h4>
                <div class="images-list">
                    ${student.images.slice(0, 5).map(img => `<span class="image-name">${img}</span>`).join('')}
                    ${student.images.length > 5 ? `<span class="more-images">+${student.images.length - 5} autres...</span>` : ''}
                </div>
            </div>
        </div>
    `;
    
    // Créer et afficher un modal temporaire
    showStudentDetailsModal(student.name, modalContent);
}

function showStudentDetailsModal(title, content) {
    // Créer un modal temporaire
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.innerHTML = `
        <div class="modal-content">
            <span class="close" onclick="this.closest('.modal').remove()">&times;</span>
            ${content}
        </div>
    `;
    
    document.body.appendChild(modal);
    modal.style.display = 'block';
    
    // Fermer en cliquant à l'extérieur
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
}

function editStudent(studentName) {
    notifications.info(`Modification de ${studentName} - Fonctionnalité à implémenter`);
    // TODO: Implémenter l'édition d'étudiant
}

let studentToDelete = null;

function deleteStudent(studentName) {
    studentToDelete = studentName;
    const deleteNameElement = document.getElementById('deleteStudentName');
    if (deleteNameElement) {
        deleteNameElement.textContent = studentName;
    }
    
    // Ouvrir le modal de confirmation
    if (typeof modalManager !== 'undefined') {
        modalManager.open('deleteModal');
    } else if (typeof openModal !== 'undefined') {
        openModal('deleteModal');
    }
}

async function confirmDelete() {
    if (!studentToDelete) return;
    
    try {
        const response = await api.delete(`/api/students/${studentToDelete}`);
        
        if (response.success) {
            notifications.success(`Étudiant ${studentToDelete} supprimé`);
            
            // Fermer le modal
            if (typeof modalManager !== 'undefined') {
                modalManager.close('deleteModal');
            } else if (typeof closeModal !== 'undefined') {
                closeModal('deleteModal');
            }
            
            // Recharger la liste
            loadStudentsList();
        } else {
            notifications.error(response.message || 'Erreur de suppression');
        }
    } catch (error) {
        notifications.error('Erreur lors de la suppression');
    } finally {
        studentToDelete = null;
    }
}

// ================================
// STATISTIQUES ET EXPORT
// ================================

async function showStudentsStats() {
    try {
        const response = await api.get('/api/students/stats');
        
        if (response.success && response.stats) {
            const stats = response.stats;
            const content = `
                <div class="stats-grid">
                    <div class="stat-item">
                        <span class="stat-label">Total étudiants:</span>
                        <span class="stat-value">${stats.total_students || 0}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Total images:</span>
                        <span class="stat-value">${stats.total_images || 0}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Moyenne par étudiant:</span>
                        <span class="stat-value">${(stats.average_images_per_student || 0).toFixed(1)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Meilleur étudiant:</span>
                        <span class="stat-value">${stats.best_student || 'N/A'}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Taille base (MB):</span>
                        <span class="stat-value">${(stats.database_size_mb || 0).toFixed(1)}</span>
                    </div>
                    <div class="stat-item">
                        <span class="stat-label">Dernière mise à jour:</span>
                        <span class="stat-value">${stats.last_updated ? Utils.formatDate(stats.last_updated) : 'N/A'}</span>
                    </div>
                </div>
            `;
            
            const statsContentElement = document.getElementById('statsContent');
            if (statsContentElement) {
                statsContentElement.innerHTML = content;
            }
            
            // Ouvrir le modal
            if (typeof modalManager !== 'undefined') {
                modalManager.open('statsModal');
            } else if (typeof openModal !== 'undefined') {
                openModal('statsModal');
            }
        } else {
            notifications.error('Erreur de chargement des statistiques');
        }
    } catch (error) {
        notifications.error('Erreur lors du chargement des statistiques');
    }
}

function exportStudentsData() {
    if (studentsData.length === 0) {
        notifications.warning('Aucune donnée à exporter');
        return;
    }
    
    // Préparer les données pour l'export
    const exportData = studentsData.map(student => ({
        nom: student.name,
        images: student.image_count,
        cree_le: student.created_at,
        derniere_maj: student.last_updated
    }));
    
    // Exporter en JSON
    const dataStr = JSON.stringify(exportData, null, 2);
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    
    if (typeof Utils !== 'undefined' && Utils.downloadFile) {
        Utils.downloadFile(dataStr, `etudiants_${timestamp}.json`, 'application/json');
        notifications.success('Données exportées');
    } else {
        // Fallback si Utils n'est pas disponible
        const blob = new Blob([dataStr], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `etudiants_${timestamp}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        notifications.success('Données exportées');
    }
}

// ================================
// VALIDATION DES FORMULAIRES
// ================================

function validateStudentInput() {
    const input = document.getElementById('studentName');
    if (!input) return;
    
    const value = input.value.trim();
    
    // Nettoyer automatiquement
    const sanitized = Utils ? Utils.sanitizeStudentName(value) : value.replace(/\s+/g, '_').toLowerCase();
    if (sanitized !== value) {
        input.value = sanitized;
    }
    
    // Valider
    const validation = Utils ? Utils.validateStudentName(sanitized) : { valid: sanitized.length >= 2 };
    
    // Afficher le feedback
    input.classList.toggle('invalid', !validation.valid);
    
    if (!validation.valid && value.length > 0) {
        showInputError(input, validation.message || 'Nom invalide');
    } else {
        clearInputError(input);
    }
}

function validateImageCount() {
    const input = document.getElementById('imageCount');
    if (!input) return;
    
    const value = parseInt(input.value);
    
    if (value < 10) {
        input.value = 10;
        notifications.warning('Minimum 10 images requis');
    } else if (value > 50) {
        input.value = 50;
        notifications.warning('Maximum 50 images autorisé');
    }
}

function setupFormValidation() {
    // Validation en temps réel
    const form = document.querySelector('.capture-setup');
    if (!form) return;
    
    const inputs = form.querySelectorAll('input, select');
    
    inputs.forEach(input => {
        input.addEventListener('blur', validateField);
    });
}

function validateField(event) {
    const field = event.target;
    
    switch(field.id) {
        case 'studentName':
            validateStudentInput();
            break;
        case 'imageCount':
            validateImageCount();
            break;
    }
}

function showInputError(input, message) {
    let errorElement = input.parentNode.querySelector('.error-message');
    if (!errorElement) {
        errorElement = document.createElement('small');
        errorElement.className = 'error-message';
        input.parentNode.appendChild(errorElement);
    }
    errorElement.textContent = message;
    errorElement.style.color = '#dc3545';
}

function clearInputError(input) {
    const errorElement = input.parentNode.querySelector('.error-message');
    if (errorElement) {
        errorElement.remove();
    }
}

// ================================
// INITIALISATION ET ÉVÉNEMENTS
// ================================

function initializeCaptureInterface() {
    // Configuration des événements du formulaire
    const studentNameInput = document.getElementById('studentName');
    const imageCountInput = document.getElementById('imageCount');
    const captureModeSelect = document.getElementById('captureMode');
    
    if (studentNameInput) {
        studentNameInput.addEventListener('input', validateStudentInput);
    }
    
    if (imageCountInput) {
        imageCountInput.addEventListener('change', validateImageCount);
    }
    
    // Écouter les changements de mode
    if (captureModeSelect) {
        captureModeSelect.addEventListener('change', function() {
            captureData.mode = this.value;
            updateCaptureInterface();
        });
    }
}

// Initialisation automatique
document.addEventListener('DOMContentLoaded', function() {
    console.log('📸 Initialisation page de capture');
    
    // Initialiser l'interface de capture
    initializeCaptureInterface();
    
    // Charger la liste des étudiants
    loadStudentsList();
    
    // Vérifier le statut de la caméra
    checkCameraStatusForCapture();
    
    // Configurer les validations de formulaire
    setupFormValidation();
});

// Nettoyage à la fermeture
window.addEventListener('beforeunload', () => {
    if (captureInterval) {
        clearInterval(captureInterval);
    }
});