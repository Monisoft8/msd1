// Basic DOMContentLoaded handler for MSD1 Application
document.addEventListener('DOMContentLoaded', function() {
    console.log('MSD1 Application loaded successfully');
    
    // Initialize form focus effects
    initializeFormEffects();
    
    // Initialize alert close buttons
    initializeAlerts();
    
    // Add smooth scroll behavior
    document.documentElement.style.scrollBehavior = 'smooth';
    
    // Initialize any custom functionality
    if (typeof initCustomFeatures === 'function') {
        initCustomFeatures();
    }
});

function initializeFormEffects() {
    const formGroups = document.querySelectorAll('.form-group');
    
    formGroups.forEach(group => {
        const input = group.querySelector('input');
        if (input) {
            input.addEventListener('focus', () => {
                group.classList.add('focused');
            });
            
            input.addEventListener('blur', () => {
                if (!input.value) {
                    group.classList.remove('focused');
                }
            });
            
            // Check if input already has value on page load
            if (input.value) {
                group.classList.add('focused');
            }
        }
    });
}

function initializeAlerts() {
    const alerts = document.querySelectorAll('.alert');
    
    alerts.forEach(alert => {
        const closeBtn = alert.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                alert.style.display = 'none';
            });
        }
        
        // Auto-dismiss alerts after 5 seconds
        setTimeout(() => {
            if (alert && alert.style.display !== 'none') {
                alert.style.opacity = '0';
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 300);
            }
        }, 5000);
    });
}

// Utility function to show notifications
function showNotification(message, type = 'info', duration = 5000) {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type}`;
    notification.innerHTML = `
        ${message}
        <span class="close-btn" onclick="this.parentElement.remove()">×</span>
    `;
    
    // Add notification to page
    const container = document.querySelector('.container') || document.body;
    container.insertBefore(notification, container.firstChild);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (notification.parentNode) {
            notification.remove();
        }
    }, duration);
}

// Helper function for AJAX requests
async function makeRequest(url, options = {}) {
    try {
        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        });
        
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        return await response.json();
    } catch (error) {
        console.error('Request failed:', error);
        showNotification('حدث خطأ في الاتصال بالخادم', 'danger');
        throw error;
    }
}

// Loading state management
function showLoading(element = null) {
    if (element) {
        element.style.opacity = '0.6';
        element.style.pointerEvents = 'none';
    } else {
        // Show global loading if no specific element
        const loading = document.createElement('div');
        loading.id = 'global-loading';
        loading.innerHTML = '<div style="position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.8); display: flex; justify-content: center; align-items: center; z-index: 9999;"><div style="text-align: center;"><i class="fas fa-spinner fa-spin fa-2x"></i><p style="margin-top: 1rem;">جاري التحميل...</p></div></div>';
        document.body.appendChild(loading);
    }
}

function hideLoading(element = null) {
    if (element) {
        element.style.opacity = '1';
        element.style.pointerEvents = 'auto';
    } else {
        const loading = document.getElementById('global-loading');
        if (loading) {
            loading.remove();
        }
    }
}