# 🚀 mAgent CRM - Deployment Documentation

## Overview

This comprehensive guide covers deploying mAgent CRM to production environments, including cloud platforms, security considerations, and maintenance procedures.

## 🎯 Deployment Options

### 1. Heroku Deployment (Recommended for Quick Start)

#### Prerequisites
- Heroku CLI installed
- Git repository configured
- Heroku account created

#### Step-by-Step Deployment
```bash
# 1. Create Heroku app
heroku create magent-crm-production

# 2. Add PostgreSQL database
heroku addons:create heroku-postgresql:hobby-dev

# 3. Set environment variables
heroku config:set SECRET_KEY="your-secret-key-here"
heroku config:set DEBUG=False
heroku config:set ALLOWED_HOSTS="magent-crm-production.herokuapp.com"

# 4. Deploy code
git push heroku main

# 5. Run migrations
heroku run python manage.py migrate

# 6. Create superuser
heroku run python manage.py createsuperuser

# 7. Collect static files
heroku run python manage.py collectstatic --noinput
```

#### Heroku Configuration Files

**Procfile**:
```
web: gunicorn magent.wsgi --log-file -
release: python manage.py migrate
```

**runtime.txt**:
```
python-3.12.0
```

**requirements.txt** (production):
```
Django==5.2.5
gunicorn==21.2.0
dj-database-url==2.1.0
whitenoise==6.6.0
psycopg2-binary==2.9.7
python-decouple==3.8
Pillow==10.0.0
bleach==6.0.0
```

### 2. AWS Deployment

#### EC2 Instance Setup
```bash
# 1. Launch EC2 instance (Ubuntu 22.04 LTS)
# 2. Connect via SSH
ssh -i your-key.pem ubuntu@your-ec2-ip

# 3. Update system
sudo apt update && sudo apt upgrade -y

# 4. Install Python and pip
sudo apt install python3 python3-pip python3-venv nginx postgresql postgresql-contrib -y

# 5. Create application user
sudo adduser magent
sudo usermod -aG sudo magent

# 6. Switch to app user
sudo su - magent
```

#### Application Setup on EC2
```bash
# 1. Clone repository
git clone https://github.com/yourusername/magent-crm.git
cd magent-crm

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set up environment variables
nano .env
# Add your environment variables

# 5. Run migrations
python manage.py migrate

# 6. Create superuser
python manage.py createsuperuser

# 7. Collect static files
python manage.py collectstatic --noinput
```

#### Nginx Configuration
```nginx
# /etc/nginx/sites-available/magent
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    location /static/ {
        alias /home/magent/magent-crm/staticfiles/;
    }

    location /media/ {
        alias /home/magent/magent-crm/media/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Systemd Service
```ini
# /etc/systemd/system/magent.service
[Unit]
Description=mAgent CRM Django Application
After=network.target

[Service]
User=magent
Group=magent
WorkingDirectory=/home/magent/magent-crm
Environment=PATH=/home/magent/magent-crm/venv/bin
EnvironmentFile=/home/magent/magent-crm/.env
ExecStart=/home/magent/magent-crm/venv/bin/gunicorn magent.wsgi:application --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

### 3. Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        netcat-traditional \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create staticfiles directory
RUN mkdir -p /app/staticfiles

# Collect static files
RUN python manage.py collectstatic --noinput

# Run migrations
RUN python manage.py migrate

EXPOSE 8000

CMD ["gunicorn", "magent.wsgi:application", "--bind", "0.0.0.0:8000"]
```

#### Docker Compose
```yaml
# docker-compose.yml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEBUG=False
      - DATABASE_URL=postgresql://magent:password@db:5432/magent_db
    depends_on:
      - db
    volumes:
      - static_volume:/app/staticfiles
      - media_volume:/app/media

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: magent_db
      POSTGRES_USER: magent
      POSTGRES_PASSWORD: password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - static_volume:/app/staticfiles
      - media_volume:/app/media
    depends_on:
      - web

volumes:
  postgres_data:
  static_volume:
  media_volume:
```

## ⚙️ Environment Configuration

### Production Settings
```python
# magent/settings.py (production overrides)
import os
from decouple import config
import dj_database_url

# Production settings
DEBUG = False
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='').split(',')

# Database
DATABASES = {
    'default': dj_database_url.parse(config('DATABASE_URL'))
}

# Security settings
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# Static files
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Email configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/magent/django.log',
        },
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

### Environment Variables
```bash
# .env file for production
SECRET_KEY=your-very-secure-secret-key-here
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com
DATABASE_URL=postgresql://user:password@host:port/database
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

## 🔒 Security Configuration

### SSL/TLS Setup
```bash
# Install Certbot for Let's Encrypt
sudo apt install certbot python3-certbot-nginx

# Obtain SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Firewall Configuration
```bash
# UFW firewall setup
sudo ufw enable
sudo ufw allow ssh
sudo ufw allow 'Nginx Full'
sudo ufw status
```

### Database Security
```sql
-- PostgreSQL security setup
CREATE USER magent_user WITH PASSWORD 'secure_password';
CREATE DATABASE magent_db OWNER magent_user;
GRANT ALL PRIVILEGES ON DATABASE magent_db TO magent_user;

-- Restrict database access
-- Edit /etc/postgresql/13/main/pg_hba.conf
-- local   magent_db    magent_user    md5
```

## 📊 Performance Optimization

### Database Optimization
```python
# Database connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'OPTIONS': {
            'MAX_CONNS': 20,
            'CONN_MAX_AGE': 600,
        },
    }
}

# Caching
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
    }
}
```

### Static File Optimization
```python
# Compression and caching
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# CDN configuration (optional)
AWS_S3_CUSTOM_DOMAIN = 'cdn.yourdomain.com'
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
```

## 🔄 Continuous Deployment

### GitHub Actions Workflow
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
    
    - name: Run tests
      run: |
        python manage.py test
    
    - name: Deploy to Heroku
      uses: akhileshns/heroku-deploy@v3.12.12
      with:
        heroku_api_key: ${{secrets.HEROKU_API_KEY}}
        heroku_app_name: "magent-crm-production"
        heroku_email: "your-email@example.com"
```

### Automated Backup Script
```bash
#!/bin/bash
# backup.sh

# Database backup
pg_dump $DATABASE_URL > backups/db_$(date +%Y%m%d_%H%M%S).sql

# Media files backup
tar -czf backups/media_$(date +%Y%m%d_%H%M%S).tar.gz media/

# Clean old backups (keep last 7 days)
find backups/ -name "*.sql" -mtime +7 -delete
find backups/ -name "*.tar.gz" -mtime +7 -delete

# Upload to S3 (optional)
aws s3 sync backups/ s3://magent-backups/
```

## 📈 Monitoring & Logging

### Health Check Endpoint
```python
# magent/urls.py
from django.http import JsonResponse
from django.db import connection

def health_check(request):
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "OK"
    except Exception as e:
        db_status = f"ERROR: {str(e)}"
    
    return JsonResponse({
        'status': 'OK' if db_status == 'OK' else 'ERROR',
        'database': db_status,
        'timestamp': timezone.now().isoformat()
    })

urlpatterns = [
    path('health/', health_check, name='health_check'),
    # ... other patterns
]
```

### Application Monitoring
```python
# Sentry integration
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)
```

### Log Management
```bash
# Logrotate configuration
# /etc/logrotate.d/magent
/var/log/magent/*.log {
    daily
    missingok
    rotate 52
    compress
    delaycompress
    notifempty
    create 644 magent magent
    postrotate
        systemctl reload magent
    endscript
}
```

## 🔧 Maintenance Procedures

### Regular Maintenance Tasks
```bash
#!/bin/bash
# maintenance.sh

# Update system packages
sudo apt update && sudo apt upgrade -y

# Update Python dependencies
source venv/bin/activate
pip list --outdated
pip install --upgrade package-name

# Database maintenance
python manage.py dbshell <<EOF
VACUUM FULL;
REINDEX DATABASE magent_db;
EOF

# Clear expired sessions
python manage.py clearsessions

# Collect static files
python manage.py collectstatic --noinput

# Restart services
sudo systemctl restart magent
sudo systemctl restart nginx
```

### Scaling Considerations
```bash
# Horizontal scaling setup
# Load balancer configuration
upstream magent_app {
    server 10.0.1.10:8000;
    server 10.0.1.11:8000;
    server 10.0.1.12:8000;
}

server {
    location / {
        proxy_pass http://magent_app;
    }
}
```

## 🚨 Troubleshooting

### Common Deployment Issues

#### Static Files Not Loading
```bash
# Check static files collection
python manage.py collectstatic --noinput --verbosity=2

# Verify nginx configuration
sudo nginx -t
sudo systemctl reload nginx
```

#### Database Connection Issues
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test database connection
python manage.py dbshell

# Check database logs
sudo tail -f /var/log/postgresql/postgresql-13-main.log
```

#### Application Errors
```bash
# Check application logs
sudo journalctl -u magent -f

# Django debug information
python manage.py check --deploy

# Test WSGI application
python manage.py runserver 0.0.0.0:8000
```

## 📋 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Environment variables configured
- [ ] Database migrations ready
- [ ] Static files collected
- [ ] SSL certificate obtained
- [ ] Backup procedures tested
- [ ] Security scan completed

### Post-Deployment
- [ ] Health check endpoint responding
- [ ] All pages loading correctly
- [ ] Database queries working
- [ ] File uploads functional
- [ ] Email sending working
- [ ] SSL/HTTPS enforced
- [ ] Monitoring alerts configured
- [ ] Backup automation verified

### Production Monitoring
- [ ] Server resource usage
- [ ] Application response times
- [ ] Error rates and types
- [ ] Database performance
- [ ] Security logs
- [ ] Backup completion
- [ ] SSL certificate expiry

## 📞 Deployment Support

For deployment assistance:
1. **Review this documentation** for step-by-step procedures
2. **Check application logs** for specific error messages
3. **Verify environment configuration** matches requirements
4. **Test in staging environment** before production deployment

**Emergency Rollback**: Keep previous version available for quick rollback if deployment fails.

---

*This deployment guide should be updated as new deployment methods and best practices are adopted.*
