// Report Builder JavaScript

let selectedFields = [];
let reportConfig = {
    name: '',
    fields: [],
    filters: {},
    format: 'csv'
};

function initializeReportBuilder() {
    setupDragAndDrop();
    setupEventListeners();
}

function setupDragAndDrop() {
    // Make field selectors draggable
    const fieldSelectors = document.querySelectorAll('.field-selector');
    fieldSelectors.forEach(selector => {
        selector.addEventListener('dragstart', handleDragStart);
    });

    // Setup drop zone
    const dropZone = document.getElementById('selectedFields');
    dropZone.addEventListener('dragover', handleDragOver);
    dropZone.addEventListener('drop', handleDrop);
}

function setupEventListeners() {
    // Report name input
    document.getElementById('reportName').addEventListener('input', updateReportConfig);
    
    // Filter inputs
    document.getElementById('cityFilter').addEventListener('input', updateReportConfig);
    document.getElementById('dateFilter').addEventListener('input', updateReportConfig);
    
    // Export format radio buttons
    document.querySelectorAll('input[name="exportFormat"]').forEach(radio => {
        radio.addEventListener('change', updateReportConfig);
    });
}

function handleDragStart(e) {
    e.dataTransfer.setData('text/plain', e.target.dataset.field);
    e.dataTransfer.setData('application/json', JSON.stringify({
        field: e.target.dataset.field,
        type: e.target.dataset.type,
        label: e.target.querySelector('strong').textContent
    }));
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    const fieldData = JSON.parse(e.dataTransfer.getData('application/json'));
    addFieldToReport(fieldData);
}

function addFieldToReport(fieldData) {
    // Check if field already added
    if (selectedFields.find(f => f.field === fieldData.field)) {
        return;
    }
    
    selectedFields.push(fieldData);
    updateSelectedFieldsDisplay();
    updateReportConfig();
}

function removeFieldFromReport(fieldName) {
    selectedFields = selectedFields.filter(f => f.field !== fieldName);
    updateSelectedFieldsDisplay();
    updateReportConfig();
}

function updateSelectedFieldsDisplay() {
    const container = document.getElementById('selectedFields');
    
    if (selectedFields.length === 0) {
        container.innerHTML = '<p class="text-muted">Drag fields here to include them in your report</p>';
        return;
    }
    
    const fieldsHtml = selectedFields.map(field => `
        <div class="selected-field d-flex justify-content-between align-items-center mb-2 p-2 border rounded">
            <div>
                <strong>${field.label}</strong>
                <small class="text-muted ms-2">(${field.type})</small>
            </div>
            <button type="button" class="btn btn-sm btn-outline-danger" onclick="removeFieldFromReport('${field.field}')">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `).join('');
    
    container.innerHTML = fieldsHtml;
}

function updateReportConfig() {
    reportConfig.name = document.getElementById('reportName').value;
    reportConfig.fields = selectedFields.map(f => f.field);
    reportConfig.filters = {
        city: document.getElementById('cityFilter').value,
        created_after: document.getElementById('dateFilter').value
    };
    reportConfig.format = document.querySelector('input[name="exportFormat"]:checked').value;
    
    updatePreview();
}

function updatePreview() {
    const preview = document.getElementById('reportPreview');
    
    if (selectedFields.length === 0) {
        preview.innerHTML = '<p class="text-muted">Configure your report above to see a preview</p>';
        return;
    }
    
    let previewHtml = '<h6>Report Configuration:</h6>';
    previewHtml += `<p><strong>Name:</strong> ${reportConfig.name || 'Untitled Report'}</p>`;
    previewHtml += `<p><strong>Fields:</strong> ${selectedFields.map(f => f.label).join(', ')}</p>`;
    
    // Show active filters
    const activeFilters = [];
    if (reportConfig.filters.city) {
        activeFilters.push(`City: ${reportConfig.filters.city}`);
    }
    if (reportConfig.filters.created_after) {
        activeFilters.push(`Created after: ${reportConfig.filters.created_after}`);
    }
    
    if (activeFilters.length > 0) {
        previewHtml += `<p><strong>Filters:</strong> ${activeFilters.join(', ')}</p>`;
    }
    
    previewHtml += `<p><strong>Format:</strong> ${reportConfig.format.toUpperCase()}</p>`;
    
    // Sample data preview
    previewHtml += '<h6 class="mt-3">Sample Output:</h6>';
    previewHtml += '<div class="table-responsive">';
    previewHtml += '<table class="table table-sm table-bordered">';
    previewHtml += '<thead><tr>';
    selectedFields.forEach(field => {
        previewHtml += `<th>${field.label}</th>`;
    });
    previewHtml += '</tr></thead>';
    previewHtml += '<tbody>';
    
    // Sample rows
    for (let i = 0; i < 3; i++) {
        previewHtml += '<tr>';
        selectedFields.forEach(field => {
            let sampleValue = getSampleValue(field.type, field.field);
            previewHtml += `<td>${sampleValue}</td>`;
        });
        previewHtml += '</tr>';
    }
    
    previewHtml += '</tbody></table></div>';
    preview.innerHTML = previewHtml;
}

function getSampleValue(type, fieldName) {
    const sampleData = {
        text: ['John Doe', 'Jane Smith', 'Mike Johnson'],
        email: ['john@example.com', 'jane@example.com', 'mike@example.com'],
        date: ['2025-08-01', '2025-08-15', '2025-08-20'],
        number: ['85.5', '92.3', '78.1']
    };
    
    const cityData = ['Auckland', 'Wellington', 'Christchurch'];
    
    if (fieldName === 'city') {
        return cityData[Math.floor(Math.random() * cityData.length)];
    }
    
    const values = sampleData[type] || ['Sample Value'];
    return values[Math.floor(Math.random() * values.length)];
}

function generateReport() {
    if (selectedFields.length === 0) {
        alert('Please select at least one field for your report.');
        return;
    }
    
    if (!reportConfig.name) {
        reportConfig.name = `Report_${new Date().toISOString().split('T')[0]}`;
    }
    
    // Show loading state
    const generateBtn = document.querySelector('button[onclick="generateReport()"]');
    const originalHtml = generateBtn.innerHTML;
    generateBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Generating...';
    generateBtn.disabled = true;
    
    // Simulate report generation (replace with actual API call)
    setTimeout(() => {
        // Reset button
        generateBtn.innerHTML = originalHtml;
        generateBtn.disabled = false;
        
        // Show success message
        alert(`Report "${reportConfig.name}" generated successfully!\n\nThis is a demo - in the full implementation, the report would be downloaded automatically.`);
        
        console.log('Report configuration:', reportConfig);
    }, 2000);
}

function saveReport() {
    if (selectedFields.length === 0) {
        alert('Please select at least one field for your report.');
        return;
    }
    
    if (!reportConfig.name) {
        alert('Please enter a report name.');
        return;
    }
    
    // TODO: Implement save functionality
    alert(`Report "${reportConfig.name}" saved successfully!\n\nThis is a demo - in the full implementation, the report would be saved to the database.`);
}