// Theme management
function toggleTheme() {
    const body = document.body;
    const currentTheme = body.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';
    
    body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // Update button text and icon
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');
    
    if (newTheme === 'dark') {
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light';
    } else {
        themeIcon.textContent = '🌙';
        themeText.textContent = 'Dark';
    }
}

// Load saved theme on page load
function loadTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.body.setAttribute('data-theme', savedTheme);
    
    const themeIcon = document.getElementById('theme-icon');
    const themeText = document.getElementById('theme-text');
    
    if (savedTheme === 'dark') {
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light';
    } else {
        themeIcon.textContent = '🌙';
        themeText.textContent = 'Dark';
    }
}

// Tab switching
function switchTab(tabName) {
    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Remove active from all buttons
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
    });
    
    // Show selected tab
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}

// Load statistics
async function loadStats() {
    try {
        // Load handler count
        const handlersResp = await fetch('/api/handlers');
        const handlersData = await handlersResp.json();
        const connectedHandlers = handlersData.handlers.filter(h => h.status === 'Connected').length;
        document.getElementById('handler-count').textContent = connectedHandlers;
        
        // Load schedule count
        const schedulesResp = await fetch('/api/schedules');
        const schedulesData = await schedulesResp.json();
        document.getElementById('schedule-count').textContent = schedulesData.count || 0;
    } catch (error) {
        console.error('Error loading stats:', error);
        document.getElementById('handler-count').textContent = 'Error';
        document.getElementById('schedule-count').textContent = 'Error';
    }
}

// Check server health and update status badge
async function checkServerHealth() {
    const badge = document.getElementById('status-badge');
    if (!badge) return;
    
    try {
        const response = await fetch('/api/health');
        if (response.ok) {
            const data = await response.json();
            badge.textContent = '● ONLINE';
            badge.className = 'status-badge online';
        } else {
            badge.textContent = '● OFFLINE';
            badge.className = 'status-badge offline';
        }
    } catch (error) {
        badge.textContent = '● OFFLINE';
        badge.className = 'status-badge offline';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    loadTheme();
    loadStats();
    checkServerHealth();
    
    // Refresh stats and health every 25 seconds
    setInterval(loadStats, 25000);
    setInterval(checkServerHealth, 25000);
});
