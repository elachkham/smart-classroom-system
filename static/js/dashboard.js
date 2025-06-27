/**
 * SMART CLASSROOM - JavaScript Dashboard COMPLET
 * Gestion du dashboard et des graphiques
 */

// ================================
// VARIABLES GLOBALES
// ================================

let attentionChart = null;
let emotionChart = null;
let logUpdateInterval = null;
let autoRefreshEnabled = true;
let autoRefreshInterval = null;
let currentLogTab = 'attendance';
let logsPaused = false;
let chartInstances = {};

// ================================
// INITIALISATION
// ================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('📊 Initialisation du dashboard');
    
    // Initialiser les composants
    initializeDashboard();
    
    // Charger les données initiales
    loadInitialData();
    
    // Démarrer l'auto-refresh
    startAutoRefresh();
    
    // Initialiser les graphiques si Chart.js est disponible
    if (typeof Chart !== 'undefined') {
        initializeCharts();
    } else {
        console.warn('Chart.js non disponible - graphiques désactivés');
    }
    
    // Charger les logs par défaut
    switchLogTab('attendance');
});

async function initializeDashboard() {
    try {
        // Vérifier la connexion au système
        const systemStatus = await api.get('/api/system/status');
        updateSystemComponents(systemStatus);
        
        // Charger les métriques initiales
        await updateMetrics();
        
        notifications.success('Dashboard initialisé');
    } catch (error) {
        console.error('Erreur initialisation dashboard:', error);
        notifications.error('Erreur d\'initialisation du dashboard');
    }
}

function loadInitialData() {
    // Charger toutes les données en parallèle
    Promise.all([
        updateMetrics(),
        updateSystemStatus(),
        updatePerformanceMetrics(),
        loadSystemAlerts()
    ]).then(() => {
        console.log('✅ Données initiales chargées');
    }).catch(error => {
        console.error('Erreur chargement données:', error);
    });
}

// ================================
// GESTION DES MÉTRIQUES
// ================================

async function updateMetrics() {
    try {
        const response = await api.get('/api/dashboard/metrics');
        if (response.success) {
            const metrics = response.metrics;
            
            // Mettre à jour les valeurs
            updateElement('totalAttendance', metrics.attendance_today || 0);
            updateElement('avgAttention', (metrics.average_attention || 0) + '%');
            updateElement('positiveEmotions', (metrics.positive_emotions || 0) + '%');
            updateElement('systemUptime', metrics.system_uptime || '0h');
            
            // Mettre à jour les tendances
            updateTrend('attendanceTrend', metrics.attendance_trend || '+0%');
            updateTrend('attentionTrend', metrics.attention_trend || '+0%');
            updateTrend('emotionTrend', metrics.emotion_trend || '+0%');
        }
    } catch (error) {
        console.error('Erreur mise à jour métriques:', error);
        // Utiliser des valeurs par défaut
        updateElement('totalAttendance', '0');
        updateElement('avgAttention', '0%');
        updateElement('positiveEmotions', '0%');
        updateElement('systemUptime', '0h');
    }
}

async function updateSystemStatus() {
    try {
        const response = await api.get('/api/system/status');
        
        updateComponentStatus('camera', response.camera_active);
        updateComponentStatus('recognition', response.face_recognition_active);
        updateComponentStatus('attention', response.attention_tracking_active);
        updateComponentStatus('emotion', response.emotion_analysis_active);
        updateComponentStatus('door', response.door_controller_connected);
        
    } catch (error) {
        console.error('Erreur statut système:', error);
        // Mettre tous les composants en erreur
        ['camera', 'recognition', 'attention', 'emotion', 'door'].forEach(component => {
            updateComponentStatus(component, false);
        });
    }
}

async function updatePerformanceMetrics() {
    try {
        const response = await api.get('/api/dashboard/performance');
        if (response.success) {
            const metrics = response.metrics;
            
            updateElement('cameraFPS', metrics.camera_fps || 0);
            updateElement('detectionsPerMin', metrics.detections_per_min || 0);
            updateElement('cpuUsage', metrics.cpu_usage || '0%');
            updateElement('memoryUsage', metrics.memory_usage || '0 MB');
            updateElement('errorsPerHour', metrics.errors_per_hour || 0);
        }
    } catch (error) {
        console.error('Erreur métriques performance:', error);
        // Valeurs par défaut
        updateElement('cameraFPS', '0');
        updateElement('detectionsPerMin', '0');
        updateElement('cpuUsage', '0%');
        updateElement('memoryUsage', '0 MB');
        updateElement('errorsPerHour', '0');
    }
}

// ================================
// GESTION DES GRAPHIQUES
// ================================

function initializeCharts() {
    initAttentionChart();
    initEmotionChart();
}

function initAttentionChart() {
    const ctx = document.getElementById('attentionChart');
    if (!ctx) {
        console.log('Canvas attentionChart non trouvé');
        return;
    }
    
    try {
        attentionChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Niveau d\'attention (%)',
                    data: [],
                    borderColor: '#667eea',
                    backgroundColor: 'rgba(102, 126, 234, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        title: {
                            display: true,
                            text: 'Attention (%)'
                        }
                    },
                    x: {
                        title: {
                            display: true,
                            text: 'Temps'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
        
        console.log('✅ Graphique d\'attention initialisé');
    } catch (error) {
        console.error('Erreur initialisation graphique attention:', error);
    }
}

function initEmotionChart() {
    const ctx = document.getElementById('emotionChart');
    if (!ctx) {
        console.log('Canvas emotionChart non trouvé');
        return;
    }
    
    try {
        emotionChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Heureux', 'Neutre', 'Surpris', 'Triste', 'En colère', 'Peur', 'Dégoût'],
                datasets: [{
                    data: [45, 30, 15, 5, 3, 1, 1],
                    backgroundColor: [
                        '#28a745', // Heureux - Vert
                        '#6c757d', // Neutre - Gris
                        '#ffc107', // Surpris - Jaune
                        '#17a2b8', // Triste - Bleu
                        '#dc3545', // En colère - Rouge
                        '#fd7e14', // Peur - Orange
                        '#6f42c1'  // Dégoût - Violet
                    ],
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom'
                    }
                }
            }
        });
        
        console.log('✅ Graphique d\'émotions initialisé');
    } catch (error) {
        console.error('Erreur initialisation graphique émotions:', error);
    }
}

async function updateCharts() {
    if (typeof Chart === 'undefined') return;
    
    await Promise.all([
        updateAttentionChart(),
        updateEmotionChart()
    ]);
}

async function updateAttentionChart() {
    if (!attentionChart) return;
    
    try {
        const response = await api.get('/api/dashboard/charts/attention?period=6h');
        if (response.success && response.data) {
            const labels = response.data.map(d => 
                new Date(d.timestamp).toLocaleTimeString('fr-FR', {
                    hour: '2-digit',
                    minute: '2-digit'
                })
            );
            const data = response.data.map(d => d.attention);
            
            attentionChart.data.labels = labels;
            attentionChart.data.datasets[0].data = data;
            attentionChart.update('none'); // Animation désactivée pour performance
        }
    } catch (error) {
        console.error('Erreur mise à jour graphique attention:', error);
    }
}

async function updateEmotionChart() {
    if (!emotionChart) return;
    
    try {
        const response = await api.get('/api/dashboard/charts/emotions');
        if (response.success && response.data) {
            // Mapper les émotions dans l'ordre correct
            const emotionOrder = ['happy', 'neutral', 'surprise', 'sad', 'angry', 'fear', 'disgust'];
            const values = emotionOrder.map(emotion => response.data[emotion] || 0);
            
            emotionChart.data.datasets[0].data = values;
            emotionChart.update('none');
            
            updateEmotionLegend(response.data);
        }
    } catch (error) {
        console.error('Erreur mise à jour graphique émotions:', error);
    }
}

function updateEmotionLegend(emotionData) {
    const legendContainer = document.getElementById('emotionLegend');
    if (!legendContainer) return;
    
    const emotions = [
        { key: 'happy', label: 'Heureux', color: '#28a745' },
        { key: 'neutral', label: 'Neutre', color: '#6c757d' },
        { key: 'surprise', label: 'Surpris', color: '#ffc107' },
        { key: 'sad', label: 'Triste', color: '#17a2b8' },
        { key: 'angry', label: 'En colère', color: '#dc3545' }
    ];
    
    const legendHTML = emotions.map(emotion => `
        <div class="emotion-item">
            <div class="emotion-color" style="background-color: ${emotion.color}"></div>
            <span>${emotion.label}: ${(emotionData[emotion.key] || 0).toFixed(1)}%</span>
        </div>
    `).join('');
    
    legendContainer.innerHTML = legendHTML;
}

// ================================
// GESTION DES LOGS
// ================================

async function switchLogTab(tabType) {
    currentLogTab = tabType;
    
    // Mettre à jour l'UI des onglets
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.getAttribute('data-tab') === tabType);
    });
    
    await loadLogs(tabType);
}

async function loadLogs(type, limit = 50) {
    try {
        console.log(`📝 Chargement logs: ${type}`);
        const response = await api.get(`/api/logs/${type}?limit=${limit}`);
        
        if (response && response.logs) {
            displayLogs(response.logs, type);
            updateLogCount(response.logs.length);
        } else {
            console.log(`Aucun log ${type} reçu`);
            displayLogs([], type);
        }
    } catch (error) {
        console.error('Erreur chargement logs:', error);
        const container = document.getElementById('logContent');
        if (container) {
            container.innerHTML = 
                '<div class="error-message">Erreur de chargement des logs</div>';
        }
    }
}

function displayLogs(logs, type) {
    const container = document.getElementById('logContent');
    if (!container) {
        console.error('Container logContent non trouvé');
        return;
    }
    
    if (!logs || logs.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div style="text-align: center; padding: 2rem; color: #666;">
                    <div style="font-size: 2rem; margin-bottom: 1rem;">📝</div>
                    <h3>Aucun log ${type} disponible</h3>
                    <p>Les logs apparaîtront ici une fois que le système détectera de l'activité.</p>
                </div>
            </div>
        `;
        return;
    }
    
    const logsHTML = logs.map(log => {
        const timeFormatted = formatLogTime(log.timestamp);
        const message = formatLogMessage(log, type);
        const details = getLogDetails(log, type);
        const icon = getLogIcon(type);
        
        return `
            <div class="log-entry ${type}">
                <div class="log-time">${timeFormatted}</div>
                <div class="log-icon">${icon}</div>
                <div class="log-message">${message}</div>
                <div class="log-details">${details}</div>
            </div>
        `;
    }).join('');
    
    container.innerHTML = logsHTML;
}

function formatLogTime(timestamp) {
    try {
        return new Date(timestamp).toLocaleString('fr-FR', {
            day: '2-digit',
            month: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    } catch (error) {
        return timestamp || 'Temps inconnu';
    }
}

function formatLogMessage(log, type) {
    switch(type) {
        case 'attendance':
            return `${log.student_name || 'Étudiant'} - ${log.course || 'Présence'}`;
        case 'attention':
            return `${log.student_name || 'Étudiant'} - ${log.status || 'Statut'}`;
        case 'emotions':
            return `${log.student_name || 'Étudiant'} - ${log.emotion || 'Émotion'}`;
        case 'access':
            return `${log.student_name || 'Système'} - ${log.action || 'Action'}`;
        default:
            return 'Activité système';
    }
}

function getLogDetails(log, type) {
    switch(type) {
        case 'attendance':
            return log.classroom ? `Salle: ${log.classroom}` : '';
        case 'attention':
            return log.std_x && log.std_y ? `STD: ${log.std_x}, ${log.std_y}` : '';
        case 'emotions':
            return log.confidence ? `Confiance: ${log.confidence}%` : '';
        case 'access':
            return log.reason || '';
        default:
            return '';
    }
}

function getLogIcon(type) {
    const icons = {
        attendance: '👥',
        attention: '👁️',
        emotions: '😊',
        access: '🚪'
    };
    return icons[type] || 'ℹ️';
}

function updateLogCount(count) {
    const visibleElement = document.getElementById('visibleLogs');
    const totalElement = document.getElementById('totalLogs');
    
    if (visibleElement) visibleElement.textContent = count;
    if (totalElement) totalElement.textContent = count;
}

// ================================
// GESTION DES ALERTES
// ================================

async function loadSystemAlerts() {
    try {
        const response = await api.get('/api/dashboard/alerts');
        if (response.success) {
            displayAlerts(response.alerts || []);
        }
    } catch (error) {
        console.error('Erreur chargement alertes:', error);
        displayAlerts([{
            type: 'warning',
            icon: '⚠️',
            message: 'Impossible de charger les alertes système',
            time_ago: 'Maintenant'
        }]);
    }
}

function displayAlerts(alerts) {
    const container = document.getElementById('alertsContainer');
    if (!container) return;
    
    if (alerts.length === 0) {
        container.innerHTML = '<div class="empty-state" style="text-align: center; padding: 1rem; color: #666;">Aucune alerte</div>';
        return;
    }
    
    const alertsHTML = alerts.map(alert => `
        <div class="alert-item ${alert.type}">
            <div class="alert-icon">${alert.icon}</div>
            <div class="alert-message">${alert.message}</div>
            <div class="alert-time">${alert.time_ago}</div>
        </div>
    `).join('');
    
    container.innerHTML = alertsHTML;
}

// ================================
// AUTO-REFRESH ET CONTRÔLES
// ================================

function startAutoRefresh() {
    if (autoRefreshEnabled) {
        autoRefreshInterval = setInterval(() => {
            if (!logsPaused) {
                refreshAllData();
            }
        }, 5000); // Actualisation toutes les 5 secondes
    }
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

function toggleAutoRefresh() {
    autoRefreshEnabled = !autoRefreshEnabled;
    const btn = event.target;
    
    if (autoRefreshEnabled) {
        startAutoRefresh();
        btn.textContent = '⏸️ Auto-refresh';
        btn.className = 'btn btn-warning';
        notifications.info('Auto-refresh activé');
    } else {
        stopAutoRefresh();
        btn.textContent = '▶️ Auto-refresh';
        btn.className = 'btn btn-success';
        notifications.info('Auto-refresh désactivé');
    }
}

async function refreshAllData() {
    try {
        // Afficher un indicateur de chargement subtil
        document.body.classList.add('refreshing');
        
        // Mettre à jour toutes les données
        await Promise.all([
            updateMetrics(),
            updateSystemStatus(),
            updatePerformanceMetrics(),
            refreshCurrentLogs()
        ]);
        
        // Mettre à jour les graphiques
        if (typeof Chart !== 'undefined') {
            await updateCharts();
        }
        
    } catch (error) {
        console.error('Erreur refresh données:', error);
        notifications.error('Erreur lors de l\'actualisation');
    } finally {
        document.body.classList.remove('refreshing');
    }
}

async function refreshCurrentLogs() {
    if (currentLogTab && !logsPaused) {
        await loadLogs(currentLogTab);
    }
}

// ================================
// FONCTIONS UTILITAIRES
// ================================

function updateElement(elementId, value) {
    const element = document.getElementById(elementId);
    if (element) {
        element.textContent = value;
    }
}

function updateComponentStatus(component, isActive) {
    const statusElement = document.getElementById(`${component}-status-dash`);
    const textElement = document.getElementById(`${component}-status-text`);
    
    if (statusElement) {
        statusElement.className = `status-indicator ${isActive ? '' : 'inactive'}`;
    }
    
    if (textElement) {
        textElement.textContent = isActive ? 'Actif' : 'Inactif';
    }
}

function updateSystemComponents(systemStatus) {
    if (!systemStatus) return;
    
    updateComponentStatus('camera', systemStatus.camera_active);
    updateComponentStatus('recognition', systemStatus.face_recognition_active);
    updateComponentStatus('attention', systemStatus.attention_tracking_active);
    updateComponentStatus('emotion', systemStatus.emotion_analysis_active);
    updateComponentStatus('door', systemStatus.door_controller_connected);
}

function updateTrend(elementId, trendValue) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    element.textContent = trendValue;
    element.className = 'metric-trend';
    
    if (trendValue.startsWith('-')) {
        element.classList.add('negative');
    }
}

// ================================
// FONCTIONS DE CONTRÔLE
// ================================

function pauseLogUpdates() {
    logsPaused = !logsPaused;
    const btn = document.getElementById('pauseLogsBtn');
    
    if (btn) {
        if (logsPaused) {
            btn.textContent = '▶️ Reprendre';
            btn.className = 'btn btn-sm btn-success';
            notifications.info('Mise à jour des logs en pause');
        } else {
            btn.textContent = '⏸️ Pause';
            btn.className = 'btn btn-sm';
            notifications.info('Mise à jour des logs reprise');
        }
    }
}

function clearLogDisplay() {
    const container = document.getElementById('logContent');
    if (container) {
        container.innerHTML = 
            '<div class="loading-indicator">Actualisation des logs...</div>';
    }
    
    setTimeout(() => {
        loadLogs(currentLogTab);
    }, 1000);
}

function clearAlerts() {
    const container = document.getElementById('alertsContainer');
    if (container) {
        container.innerHTML = '<div class="empty-state" style="text-align: center; padding: 1rem; color: #666;">Alertes effacées</div>';
    }
    notifications.info('Alertes effacées');
}

function refreshAlerts() {
    loadSystemAlerts();
    notifications.info('Alertes actualisées');
}

function setChartPeriod(chartId, period) {
    // Mettre à jour les boutons actifs
    if (event && event.target) {
        const parent = event.target.parentElement;
        if (parent) {
            parent.querySelectorAll('.btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
        }
    }
    
    // Recharger les données du graphique
    if (chartId === 'attentionChart') {
        updateAttentionChart();
    }
}

function filterLogs() {
    const filter = document.getElementById('logFilter');
    if (!filter) return;
    
    const filterValue = filter.value.toLowerCase();
    const logEntries = document.querySelectorAll('.log-entry');
    
    let visibleCount = 0;
    logEntries.forEach(entry => {
        const text = entry.textContent.toLowerCase();
        const isVisible = text.includes(filterValue);
        entry.style.display = isVisible ? 'flex' : 'none';
        
        if (isVisible) visibleCount++;
    });
    
    updateLogCount(visibleCount);
}

function loadMoreLogs() {
    // Charger plus de logs (augmenter la limite)
    loadLogs(currentLogTab, 100);
    notifications.info('Chargement de plus de logs...');
}

// ================================
// EXPORT ET UTILITAIRES
// ================================

async function exportDashboardData() {
    try {
        const response = await api.get('/api/export/dashboard');
        if (response.success) {
            const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
            const filename = `dashboard_export_${timestamp}.json`;
            
            if (typeof Utils !== 'undefined' && Utils.downloadFile) {
                Utils.downloadFile(
                    JSON.stringify(response.data, null, 2),
                    filename,
                    'application/json'
                );
            } else {
                // Fallback
                const dataStr = JSON.stringify(response.data, null, 2);
                const blob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                URL.revokeObjectURL(url);
            }
            
            notifications.success('Données exportées');
        }
    } catch (error) {
        notifications.error('Erreur lors de l\'export');
    }
}

function exportCurrentLogs() {
    const logs = [];
    const logEntries = document.querySelectorAll('.log-entry');
    
    logEntries.forEach(entry => {
        const time = entry.querySelector('.log-time')?.textContent || '';
        const message = entry.querySelector('.log-message')?.textContent || '';
        const details = entry.querySelector('.log-details')?.textContent || '';
        
        logs.push({
            timestamp: time,
            message: message,
            details: details,
            type: currentLogTab
        });
    });
    
    const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, '-');
    const filename = `logs_${currentLogTab}_${timestamp}.json`;
    
    const dataStr = JSON.stringify(logs, null, 2);
    const blob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    notifications.success(`Logs ${currentLogTab} exportés`);
}

// Nettoyage à la fermeture
window.addEventListener('beforeunload', () => {
    stopAutoRefresh();
});