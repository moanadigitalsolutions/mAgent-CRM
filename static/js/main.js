// mAgent CRM JavaScript

document.addEventListener('DOMContentLoaded', function() {
    initializeEditableCells();
    initializeFileUpload();
    initializeSearch();
    initializeNotifications();
});

// Editable cells functionality (Monday.com style)
function initializeEditableCells() {
    const editableCells = document.querySelectorAll('.editable-cell');
    
    editableCells.forEach(cell => {
        cell.addEventListener('dblclick', function() {
            if (this.classList.contains('editing')) return;
            
            const originalValue = this.textContent.trim();
            const fieldName = this.dataset.field;
            const customerId = this.dataset.customerId;
            
            // Create input element based on field type
            let input;
            const fieldType = this.dataset.fieldType || 'text';
            
            switch(fieldType) {
                case 'email':
                    input = document.createElement('input');
                    input.type = 'email';
                    break;
                case 'tel':
                    input = document.createElement('input');
                    input.type = 'tel';
                    break;
                case 'textarea':
                    input = document.createElement('textarea');
                    input.rows = 3;
                    break;
                case 'select':
                    input = document.createElement('select');
                    const options = this.dataset.options ? this.dataset.options.split(',') : [];
                    options.forEach(option => {
                        const optionElement = document.createElement('option');
                        optionElement.value = option.trim();
                        optionElement.textContent = option.trim();
                        if (option.trim() === originalValue) {
                            optionElement.selected = true;
                        }
                        input.appendChild(optionElement);
                    });
                    break;
                default:
                    input = document.createElement('input');
                    input.type = 'text';
            }
            
            input.value = originalValue;
            input.className = 'form-control';
            
            // Replace cell content with input
            this.innerHTML = '';
            this.appendChild(input);
            this.classList.add('editing');
            
            // Focus and select all text
            input.focus();
            if (input.select) input.select();
            
            // Save on Enter, cancel on Escape
            input.addEventListener('keydown', function(e) {
                if (e.key === 'Enter') {
                    saveEdit(cell, input, fieldName, customerId, originalValue);
                } else if (e.key === 'Escape') {
                    cancelEdit(cell, originalValue);
                }
            });
            
            // Save on blur
            input.addEventListener('blur', function() {
                saveEdit(cell, input, fieldName, customerId, originalValue);
            });
        });
    });
}

function saveEdit(cell, input, fieldName, customerId, originalValue) {
    const newValue = input.value.trim();
    
    if (newValue === originalValue) {
        cancelEdit(cell, originalValue);
        return;
    }
    
    // Show loading state
    cell.classList.add('loading');
    cell.innerHTML = 'Saving...';
    
    // Prepare data for AJAX request
    const formData = new FormData();
    formData.append('field', fieldName);
    formData.append('value', newValue);
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    // Send AJAX request
    fetch(`/customers/${customerId}/update-field/`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        cell.classList.remove('loading', 'editing');
        
        if (data.success) {
            cell.textContent = newValue;
            showNotification('Field updated successfully', 'success');
        } else {
            cell.textContent = originalValue;
            showNotification(data.error || 'Error updating field', 'error');
        }
    })
    .catch(error => {
        cell.classList.remove('loading', 'editing');
        cell.textContent = originalValue;
        showNotification('Error updating field', 'error');
        console.error('Error:', error);
    });
}

function cancelEdit(cell, originalValue) {
    cell.classList.remove('editing');
    cell.textContent = originalValue;
}

// File upload functionality
function initializeFileUpload() {
    const uploadAreas = document.querySelectorAll('.file-upload-area');
    
    uploadAreas.forEach(area => {
        const fileInput = area.querySelector('input[type="file"]');
        
        // Click to select files
        area.addEventListener('click', () => {
            if (fileInput) fileInput.click();
        });
        
        // Drag and drop
        area.addEventListener('dragover', (e) => {
            e.preventDefault();
            area.classList.add('dragover');
        });
        
        area.addEventListener('dragleave', () => {
            area.classList.remove('dragover');
        });
        
        area.addEventListener('drop', (e) => {
            e.preventDefault();
            area.classList.remove('dragover');
            
            const files = e.dataTransfer.files;
            if (fileInput && files.length > 0) {
                fileInput.files = files;
                handleFileUpload(fileInput);
            }
        });
        
        // File input change
        if (fileInput) {
            fileInput.addEventListener('change', () => {
                handleFileUpload(fileInput);
            });
        }
    });
}

function handleFileUpload(fileInput) {
    const files = fileInput.files;
    if (files.length === 0) return;
    
    const uploadArea = fileInput.closest('.file-upload-area');
    const customerId = fileInput.dataset.customerId;
    
    // Create progress indicator
    const progressDiv = document.createElement('div');
    progressDiv.className = 'upload-progress mt-3';
    progressDiv.innerHTML = `
        <div class="progress">
            <div class="progress-bar" role="progressbar" style="width: 0%"></div>
        </div>
        <small class="text-muted">Uploading files...</small>
    `;
    uploadArea.appendChild(progressDiv);
    
    // Prepare form data
    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    formData.append('csrfmiddlewaretoken', getCsrfToken());
    
    // Upload files
    fetch(`/customers/${customerId}/upload-files/`, {
        method: 'POST',
        body: formData,
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.json())
    .then(data => {
        progressDiv.remove();
        
        if (data.success) {
            showNotification(`${data.uploaded_count} file(s) uploaded successfully`, 'success');
            // Refresh file list if it exists
            const fileList = document.querySelector('.file-list');
            if (fileList) {
                location.reload(); // Simple refresh for now
            }
        } else {
            showNotification(data.error || 'Error uploading files', 'error');
        }
    })
    .catch(error => {
        progressDiv.remove();
        showNotification('Error uploading files', 'error');
        console.error('Error:', error);
    });
}

// Search functionality
function initializeSearch() {
    const searchInput = document.querySelector('#search-input');
    const filterChips = document.querySelectorAll('.filter-chip');
    
    if (searchInput) {
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                performSearch(this.value);
            }, 300);
        });
    }
    
    filterChips.forEach(chip => {
        chip.addEventListener('click', function() {
            this.classList.toggle('active');
            applyFilters();
        });
    });
}

function performSearch(query) {
    const url = new URL(window.location);
    if (query.trim()) {
        url.searchParams.set('search', query);
    } else {
        url.searchParams.delete('search');
    }
    window.location.href = url.toString();
}

function applyFilters() {
    const activeFilters = Array.from(document.querySelectorAll('.filter-chip.active'))
        .map(chip => chip.dataset.filter);
    
    const url = new URL(window.location);
    
    // Clear existing filter params
    url.searchParams.delete('city');
    url.searchParams.delete('active');
    
    // Apply active filters
    activeFilters.forEach(filter => {
        const [key, value] = filter.split(':');
        url.searchParams.set(key, value);
    });
    
    window.location.href = url.toString();
}

// Notification system
function initializeNotifications() {
    // Auto-hide Django messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.classList.add('fade');
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });
}

function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="d-flex justify-content-between align-items-center">
            <span>${message}</span>
            <button type="button" class="btn-close btn-sm" onclick="this.parentElement.parentElement.remove()"></button>
        </div>
    `;
    
    document.body.appendChild(notification);
    
    // Show notification
    setTimeout(() => notification.classList.add('show'), 100);
    
    // Auto-hide after 5 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 5000);
}

// Utility functions
function getCsrfToken() {
    // First try to get from form input
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    if (csrfInput) {
        return csrfInput.value;
    }
    
    // Fallback to meta tag approach
    const csrfMeta = document.querySelector('meta[name=csrf-token]');
    if (csrfMeta) {
        return csrfMeta.getAttribute('content');
    }
    
    // Try to get from cookie as last resort
    const csrfCookie = document.cookie.split(';').find(c => c.trim().startsWith('csrftoken='));
    if (csrfCookie) {
        return csrfCookie.split('=')[1];
    }
    
    return '';
}

// Delete confirmation
function confirmDelete(message = 'Are you sure you want to delete this item?') {
    return confirm(message);
}

// Format phone number for New Zealand
function formatNZPhone(phone) {
    const cleaned = phone.replace(/\D/g, '');
    
    if (cleaned.startsWith('64')) {
        // International format
        return `+64 ${cleaned.slice(2, 3)} ${cleaned.slice(3, 6)} ${cleaned.slice(6)}`;
    } else if (cleaned.startsWith('0')) {
        // National format
        return `${cleaned.slice(0, 2)} ${cleaned.slice(2, 5)} ${cleaned.slice(5)}`;
    }
    
    return phone;
}

// Initialize tooltips and popovers (if using Bootstrap)
function initializeBootstrapComponents() {
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Call Bootstrap initialization when DOM is ready
document.addEventListener('DOMContentLoaded', initializeBootstrapComponents);

// Mobile sidebar toggle
function toggleSidebar() {
    const sidebar = document.querySelector('.sidebar');
    if (sidebar) {
        sidebar.classList.toggle('show');
    }
}

// Add to window for global access
window.confirmDelete = confirmDelete;
window.toggleSidebar = toggleSidebar;