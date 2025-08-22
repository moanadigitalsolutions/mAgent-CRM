#!/usr/bin/env bash
# This script is run by Heroku after deployment

echo "Running post-deployment script..."

# Run migrations
python manage.py migrate --noinput

# Create sample data if no data exists
python manage.py shell -c "
from customers.models import Customer
if not Customer.objects.exists():
    from django.core.management import call_command
    call_command('create_sample_data')
    print('Sample data created')
else:
    print('Data already exists, skipping sample data creation')
"

echo "Post-deployment script completed."