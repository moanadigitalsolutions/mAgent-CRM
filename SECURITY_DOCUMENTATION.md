# 🔒 mAgent CRM - Security Documentation

## Overview

This document outlines the security measures, best practices, and guidelines implemented in mAgent CRM to protect customer data and ensure system integrity.

## 🛡️ Security Framework

### Authentication & Authorization

#### User Authentication
- **Django Session Authentication**: Secure session-based authentication
- **Password Requirements**: Strong password enforcement (minimum 8 characters, mixed case, numbers)
- **Account Lockout**: Protection against brute force attacks
- **Session Management**: Automatic session expiry and secure session cookies

```python
# Password validation settings
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]
```

#### Permission System
- **Role-Based Access Control (RBAC)**: Granular permissions for different user roles
- **Staff vs User Permissions**: Differentiated access levels
- **Object-Level Permissions**: Customer-specific access controls

```python
# User permission levels
ADMIN_USERS = 'Full system access'
STAFF_USERS = 'Read/write customer data'
REGULAR_USERS = 'Read-only customer data'
```

### Data Protection

#### Data Encryption
- **In Transit**: HTTPS/TLS encryption for all communications
- **At Rest**: Database field encryption for sensitive data
- **Session Data**: Encrypted session storage

#### Database Security
```sql
-- Sensitive field protection
CREATE TABLE customers_customer (
    -- Standard fields
    id INTEGER PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    email VARCHAR(254) UNIQUE NOT NULL,
    -- Encrypted sensitive fields
    mobile_encrypted BLOB,
    notes_encrypted BLOB
);
```

#### File Upload Security
- **File Type Validation**: Whitelist approach for allowed file types
- **Size Limitations**: Maximum 10MB per file upload
- **Virus Scanning**: Automated malware detection (planned)
- **Secure Storage**: Files stored outside web root

```python
# Allowed file types
ALLOWED_FILE_TYPES = [
    'application/pdf',
    'text/plain',
    'image/jpeg',
    'image/png',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
]

# File upload validation
def validate_file_upload(file):
    if file.size > MAX_FILE_SIZE:
        raise ValidationError("File too large")
    if file.content_type not in ALLOWED_FILE_TYPES:
        raise ValidationError("File type not allowed")
```

## 🔐 CSRF Protection

### Implementation
All forms include CSRF tokens to prevent Cross-Site Request Forgery attacks:

```html
<!-- Template example -->
<form method="post">
    {% csrf_token %}
    <!-- form fields -->
</form>
```

```javascript
// AJAX requests
function getCsrfToken() {
    return document.querySelector('[name=csrfmiddlewaretoken]').value;
}

fetch('/api/endpoint/', {
    method: 'POST',
    headers: {
        'X-CSRFToken': getCsrfToken(),
        'Content-Type': 'application/json',
    },
    body: JSON.stringify(data)
});
```

### CSRF Settings
```python
# CSRF protection settings
CSRF_COOKIE_SECURE = True  # HTTPS only
CSRF_COOKIE_HTTPONLY = True  # Prevent XSS
CSRF_COOKIE_SAMESITE = 'Strict'  # CSRF protection
CSRF_TRUSTED_ORIGINS = ['https://yourdomain.com']
```

## 🌐 Cross-Site Scripting (XSS) Prevention

### Template Security
```html
<!-- Always escape user input -->
{{ user_input|escape }}

<!-- For HTML content, use safe filter carefully -->
{{ trusted_html|safe }}

<!-- Auto-escaping is enabled by default -->
{% autoescape on %}
    {{ user_content }}
{% endautoescape %}
```

### Content Security Policy (CSP)
```python
# CSP Headers
CSP_DEFAULT_SRC = "'self'"
CSP_SCRIPT_SRC = "'self' 'unsafe-inline'"
CSP_STYLE_SRC = "'self' 'unsafe-inline'"
CSP_IMG_SRC = "'self' data:"
CSP_FONT_SRC = "'self'"
```

## 🗃️ SQL Injection Prevention

### Django ORM Protection
```python
# Safe: Using Django ORM
customers = Customer.objects.filter(city=user_input)

# Safe: Using parameterized queries
Customer.objects.extra(
    where=["city = %s"],
    params=[user_input]
)

# AVOID: String concatenation
# customers = Customer.objects.raw(f"SELECT * FROM customers WHERE city = '{user_input}'")
```

### Input Validation
```python
# Form validation
class CustomerForm(forms.ModelForm):
    def clean_email(self):
        email = self.cleaned_data['email']
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise forms.ValidationError("Invalid email format")
        return email
    
    def clean_mobile(self):
        mobile = self.cleaned_data['mobile']
        # New Zealand mobile validation
        if not re.match(r'^02[0-9]{7,8}$', mobile):
            raise forms.ValidationError("Invalid NZ mobile number")
        return mobile
```

## 🔒 Session Security

### Session Configuration
```python
# Session settings
SESSION_COOKIE_SECURE = True  # HTTPS only
SESSION_COOKIE_HTTPONLY = True  # Prevent XSS
SESSION_COOKIE_SAMESITE = 'Strict'  # CSRF protection
SESSION_COOKIE_AGE = 3600  # 1 hour timeout
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_SAVE_EVERY_REQUEST = True
```

### Session Management
```python
# Manual session security
def secure_login(request, user):
    # Regenerate session ID after login
    request.session.cycle_key()
    
    # Set secure session data
    request.session['user_id'] = user.id
    request.session['login_time'] = timezone.now().isoformat()
    
    # Set session expiry
    request.session.set_expiry(3600)
```

## 🔍 Security Logging & Monitoring

### Audit Trail
```python
# Security event logging
import logging

security_logger = logging.getLogger('security')

class SecurityMiddleware:
    def process_request(self, request):
        # Log suspicious activity
        if self.is_suspicious_request(request):
            security_logger.warning(
                f"Suspicious request from {request.META.get('REMOTE_ADDR')}: "
                f"{request.method} {request.path}"
            )
```

### Failed Login Attempts
```python
# Track failed logins
class LoginAttempt(models.Model):
    ip_address = models.GenericIPAddressField()
    username = models.CharField(max_length=150)
    timestamp = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    
    @classmethod
    def is_blocked(cls, ip_address):
        # Block after 5 failed attempts in 15 minutes
        recent_failures = cls.objects.filter(
            ip_address=ip_address,
            success=False,
            timestamp__gte=timezone.now() - timedelta(minutes=15)
        ).count()
        return recent_failures >= 5
```

### Security Events to Monitor
- Failed login attempts
- Multiple rapid requests from same IP
- File upload attempts with malicious files
- SQL injection attempts
- XSS attempts
- Unusual database queries
- Admin panel access
- Password reset requests

## 🚫 Input Validation & Sanitization

### Data Validation Framework
```python
# Comprehensive validation
from django.core.validators import validate_email, RegexValidator

class CustomerValidator:
    @staticmethod
    def validate_name(name):
        if not re.match(r'^[a-zA-Z\s\-\'\.]+$', name):
            raise ValidationError("Name contains invalid characters")
        if len(name) > 100:
            raise ValidationError("Name too long")
        return name.strip()
    
    @staticmethod
    def validate_postcode(postcode):
        # New Zealand postcode validation
        if not re.match(r'^\d{4}$', postcode):
            raise ValidationError("Invalid NZ postcode")
        return postcode
    
    @staticmethod
    def sanitize_notes(notes):
        # Remove potentially dangerous HTML
        from bleach import clean
        allowed_tags = ['p', 'br', 'strong', 'em']
        return clean(notes, tags=allowed_tags, strip=True)
```

### File Upload Validation
```python
# Secure file handling
import magic

def validate_uploaded_file(file):
    # Check file size
    if file.size > settings.MAX_FILE_SIZE:
        raise ValidationError("File too large")
    
    # Validate MIME type
    file_type = magic.from_buffer(file.read(1024), mime=True)
    if file_type not in settings.ALLOWED_MIME_TYPES:
        raise ValidationError("File type not allowed")
    
    # Reset file pointer
    file.seek(0)
    
    # Check for embedded scripts in images
    if file_type.startswith('image/'):
        validate_image_file(file)
    
    return file
```

## 🔐 API Security

### Rate Limiting
```python
# Simple rate limiting
from django.core.cache import cache
from django.http import HttpResponseTooManyRequests

class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Get client IP
        ip = self.get_client_ip(request)
        
        # Check rate limit
        key = f"rate_limit_{ip}"
        requests = cache.get(key, 0)
        
        if requests >= 100:  # 100 requests per minute
            return HttpResponseTooManyRequests("Rate limit exceeded")
        
        # Increment counter
        cache.set(key, requests + 1, 60)  # 60 seconds
        
        return self.get_response(request)
```

### API Authentication (Future)
```python
# Token-based authentication (planned)
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

class CustomerAPIView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Secure API endpoint
        pass
```

## 🛠️ Security Best Practices

### Development Security
1. **Never commit secrets** to version control
2. **Use environment variables** for sensitive configuration
3. **Regular dependency updates** for security patches
4. **Code review** for security vulnerabilities
5. **Static analysis** tools for security scanning

### Environment Configuration
```bash
# .env file (never commit this)
SECRET_KEY=your-secret-key-here
DATABASE_PASSWORD=secure-password
EMAIL_PASSWORD=email-password
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
```

### Database Security
```python
# Secure database configuration
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}
```

## 🚨 Incident Response

### Security Incident Checklist
1. **Immediate Response**
   - Identify and contain the threat
   - Preserve evidence
   - Assess impact

2. **Investigation**
   - Review security logs
   - Identify attack vector
   - Determine data exposure

3. **Recovery**
   - Patch vulnerabilities
   - Restore from clean backups
   - Reset compromised credentials

4. **Post-Incident**
   - Update security measures
   - Document lessons learned
   - Notify affected users if required

### Emergency Contacts
```python
# Security incident contacts
SECURITY_CONTACTS = {
    'primary': 'security@yourcompany.com',
    'backup': 'admin@yourcompany.com',
    'legal': 'legal@yourcompany.com'
}
```

## 📋 Security Checklist

### Pre-Deployment Security Review
- [ ] All forms include CSRF protection
- [ ] User input is properly validated and sanitized
- [ ] SQL injection protection verified
- [ ] XSS prevention measures in place
- [ ] File upload security implemented
- [ ] Session security configured
- [ ] HTTPS enforced
- [ ] Security headers configured
- [ ] Error handling doesn't expose sensitive info
- [ ] Logging and monitoring active
- [ ] Dependencies up to date
- [ ] Security testing completed

### Regular Security Maintenance
- [ ] Monthly dependency updates
- [ ] Quarterly security reviews
- [ ] Annual penetration testing
- [ ] Regular backup testing
- [ ] Security log analysis
- [ ] User access review
- [ ] SSL certificate renewal
- [ ] Security training for developers

## 🔄 Security Updates

### Staying Current
1. **Subscribe to security advisories**
   - Django security updates
   - Python security announcements
   - Third-party package vulnerabilities

2. **Regular updates**
   - Keep Django and Python updated
   - Update all dependencies monthly
   - Apply security patches immediately

3. **Security tools**
   - Use `safety` to check for known vulnerabilities
   - Implement automated security scanning
   - Regular code security reviews

```bash
# Check for vulnerabilities
pip install safety
safety check

# Update dependencies
pip list --outdated
pip install --upgrade package-name
```

## 📞 Security Support

For security-related questions or to report vulnerabilities:
1. **Review this documentation** for standard security practices
2. **Check Django security documentation** for framework-specific guidance
3. **Contact development team** for custom security implementations
4. **Report vulnerabilities** through secure channels

**Remember**: Security is everyone's responsibility. Always consider security implications when developing new features or modifying existing code.

---

*This document should be reviewed and updated regularly as new security measures are implemented and threats evolve.*
