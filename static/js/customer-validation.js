/**
 * Real-time inline validation for customer forms
 * Provides instant feedback for email, mobile, and postcode fields
 */

class CustomerFormValidator {
    constructor(options = {}) {
        this.options = {
            emailField: '#id_email',
            mobileField: '#id_mobile', 
            postcodeField: '#id_postcode',
            customerId: null,
            debounceDelay: 500,
            ...options
        };
        
        this.debounceTimers = {};
        this.init();
    }
    
    init() {
        this.setupEmailValidation();
        this.setupMobileValidation();
        this.setupPostcodeValidation();
    }
    
    setupEmailValidation() {
        const emailField = document.querySelector(this.options.emailField);
        if (!emailField) return;
        
        emailField.addEventListener('input', (e) => {
            this.debounceValidation('email', () => {
                this.validateEmail(e.target.value.trim());
            });
        });
        
        emailField.addEventListener('blur', (e) => {
            this.validateEmail(e.target.value.trim());
        });
    }
    
    setupMobileValidation() {
        const mobileField = document.querySelector(this.options.mobileField);
        if (!mobileField) return;
        
        mobileField.addEventListener('input', (e) => {
            this.debounceValidation('mobile', () => {
                this.validateMobile(e.target.value.trim());
            });
        });
        
        mobileField.addEventListener('blur', (e) => {
            this.validateMobile(e.target.value.trim());
        });
    }
    
    setupPostcodeValidation() {
        const postcodeField = document.querySelector(this.options.postcodeField);
        if (!postcodeField) return;
        
        postcodeField.addEventListener('input', (e) => {
            this.debounceValidation('postcode', () => {
                this.validatePostcode(e.target.value.trim());
            });
        });
        
        postcodeField.addEventListener('blur', (e) => {
            this.validatePostcode(e.target.value.trim());
        });
    }
    
    debounceValidation(fieldType, callback) {
        if (this.debounceTimers[fieldType]) {
            clearTimeout(this.debounceTimers[fieldType]);
        }
        
        this.debounceTimers[fieldType] = setTimeout(callback, this.options.debounceDelay);
    }
    
    async validateEmail(email) {
        const field = document.querySelector(this.options.emailField);
        if (!field || !email) {
            this.clearFieldValidation(field);
            return;
        }
        
        this.showFieldLoading(field);
        
        try {
            const params = new URLSearchParams({
                email: email,
                ...(this.options.customerId && { customer_id: this.options.customerId })
            });
            
            const response = await fetch(`/customers/validate/email/?${params}`);
            const data = await response.json();
            
            if (data.valid) {
                this.showFieldSuccess(field, data.message);
            } else {
                this.showFieldError(field, data.message, data.duplicate_customer);
            }
        } catch (error) {
            this.showFieldError(field, 'Validation failed. Please try again.');
        }
    }
    
    async validateMobile(mobile) {
        const field = document.querySelector(this.options.mobileField);
        if (!field || !mobile) {
            this.clearFieldValidation(field);
            return;
        }
        
        this.showFieldLoading(field);
        
        try {
            const params = new URLSearchParams({
                mobile: mobile,
                ...(this.options.customerId && { customer_id: this.options.customerId })
            });
            
            const response = await fetch(`/customers/validate/mobile/?${params}`);
            const data = await response.json();
            
            if (data.valid) {
                this.showFieldSuccess(field, data.message);
            } else {
                this.showFieldError(field, data.message, data.duplicate_customer);
            }
        } catch (error) {
            this.showFieldError(field, 'Validation failed. Please try again.');
        }
    }
    
    async validatePostcode(postcode) {
        const field = document.querySelector(this.options.postcodeField);
        if (!field || !postcode) {
            this.clearFieldValidation(field);
            return;
        }
        
        this.showFieldLoading(field);
        
        try {
            const params = new URLSearchParams({ postcode: postcode });
            const response = await fetch(`/customers/validate/postcode/?${params}`);
            const data = await response.json();
            
            if (data.valid) {
                this.showFieldSuccess(field, data.message);
            } else {
                this.showFieldError(field, data.message);
            }
        } catch (error) {
            this.showFieldError(field, 'Validation failed. Please try again.');
        }
    }
    
    showFieldLoading(field) {
        this.clearFieldValidation(field);
        field.classList.add('is-validating');
        
        const feedback = this.getOrCreateFeedback(field);
        feedback.className = 'invalid-feedback d-block text-info';
        feedback.innerHTML = '<i class="bi bi-hourglass-split"></i> Validating...';
    }
    
    showFieldSuccess(field, message) {
        this.clearFieldValidation(field);
        field.classList.add('is-valid');
        
        const feedback = this.getOrCreateFeedback(field);
        feedback.className = 'valid-feedback d-block';
        feedback.innerHTML = `<i class="bi bi-check-circle"></i> ${message}`;
    }
    
    showFieldError(field, message, duplicateCustomer = null) {
        this.clearFieldValidation(field);
        field.classList.add('is-invalid');
        
        const feedback = this.getOrCreateFeedback(field);
        feedback.className = 'invalid-feedback d-block';
        
        let html = `<i class="bi bi-exclamation-circle"></i> ${message}`;
        
        if (duplicateCustomer) {
            html += `<div class="mt-2">
                <small class="text-muted">
                    <strong>Existing Customer:</strong><br>
                    ${duplicateCustomer.name}<br>
                    ${duplicateCustomer.email || duplicateCustomer.mobile}
                    <a href="/customers/${duplicateCustomer.id}/" class="ms-2 text-decoration-none" target="_blank">
                        <i class="bi bi-box-arrow-up-right"></i> View
                    </a>
                </small>
            </div>`;
        }
        
        feedback.innerHTML = html;
    }
    
    clearFieldValidation(field) {
        if (!field) return;
        
        field.classList.remove('is-valid', 'is-invalid', 'is-validating');
        
        const feedback = field.parentElement.querySelector('.field-feedback');
        if (feedback) {
            feedback.innerHTML = '';
            feedback.className = 'field-feedback';
        }
    }
    
    getOrCreateFeedback(field) {
        let feedback = field.parentElement.querySelector('.field-feedback');
        if (!feedback) {
            feedback = document.createElement('div');
            feedback.className = 'field-feedback';
            field.parentElement.appendChild(feedback);
        }
        return feedback;
    }
    
    // Public method to validate all fields
    validateAllFields() {
        const emailField = document.querySelector(this.options.emailField);
        const mobileField = document.querySelector(this.options.mobileField);
        const postcodeField = document.querySelector(this.options.postcodeField);
        
        if (emailField && emailField.value.trim()) {
            this.validateEmail(emailField.value.trim());
        }
        
        if (mobileField && mobileField.value.trim()) {
            this.validateMobile(mobileField.value.trim());
        }
        
        if (postcodeField && postcodeField.value.trim()) {
            this.validatePostcode(postcodeField.value.trim());
        }
    }
    
    // Check if form has any validation errors
    hasValidationErrors() {
        const form = document.querySelector('form');
        if (!form) return false;
        
        return form.querySelectorAll('.is-invalid').length > 0;
    }
}

// Auto-initialize on customer forms
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a customer form page
    const customerForm = document.querySelector('form[action*="customer"]');
    if (!customerForm) return;
    
    // Get customer ID for edit forms
    const pathParts = window.location.pathname.split('/');
    const isEditForm = pathParts.includes('edit');
    let customerId = null;
    
    if (isEditForm) {
        // Extract customer ID from URL like /customers/123/edit/
        const customerIndex = pathParts.indexOf('customers');
        if (customerIndex >= 0 && customerIndex + 1 < pathParts.length) {
            const potentialId = pathParts[customerIndex + 1];
            if (!isNaN(potentialId)) {
                customerId = potentialId;
            }
        }
    }
    
    // Initialize validator
    const validator = new CustomerFormValidator({
        customerId: customerId
    });
    
    // Add form submission validation
    customerForm.addEventListener('submit', function(e) {
        if (validator.hasValidationErrors()) {
            e.preventDefault();
            
            // Show alert
            const existingAlert = document.querySelector('.validation-error-alert');
            if (existingAlert) {
                existingAlert.remove();
            }
            
            const alert = document.createElement('div');
            alert.className = 'alert alert-danger validation-error-alert';
            alert.innerHTML = `
                <i class="bi bi-exclamation-triangle"></i>
                <strong>Validation Errors</strong><br>
                Please fix the validation errors below before submitting.
            `;
            
            customerForm.insertBefore(alert, customerForm.firstChild);
            
            // Scroll to first error
            const firstError = customerForm.querySelector('.is-invalid');
            if (firstError) {
                firstError.scrollIntoView({ behavior: 'smooth', block: 'center' });
                firstError.focus();
            }
        }
    });
    
    // Store validator globally for debugging
    window.customerValidator = validator;
});