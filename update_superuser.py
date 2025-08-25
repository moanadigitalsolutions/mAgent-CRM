#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magent.settings')
django.setup()

from django.contrib.auth.models import User

# Delete existing admin user if exists
User.objects.filter(username='admin').delete()

# Create new superuser with updated credentials
User.objects.create_superuser('admin', 'admin@example.com', 'M@Tty1301')

print("Superuser 'admin' created successfully with new password.")