#!/usr/bin/env python
"""
Script to create test data for duplicate detection functionality
"""
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magent.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Customer

def create_test_duplicates():
    """Create test customers that should be detected as potential duplicates"""
    
    # Get or create a test user
    user, created = User.objects.get_or_create(
        username='admin',
        defaults={
            'email': 'admin@example.com',
            'is_staff': True,
            'is_superuser': True
        }
    )
    if created:
        user.set_password('admin123')
        user.save()
        print(f"Created admin user: {user.username}")
    
    # Clear existing test customers more thoroughly
    Customer.objects.filter(email__icontains='test').delete()
    Customer.objects.filter(email__icontains='example.com').delete()
    Customer.objects.filter(email__icontains='company.com').delete()
    Customer.objects.filter(first_name__in=['John', 'Jon', 'Sarah', 'Sara', 'Mike', 'Michael', 'Alice', 'Bob']).delete()
    print("Cleared existing test customers")
    
    # Create potential duplicates - different emails but similar names and phones
    customers = [
        {
            'first_name': 'John',
            'last_name': 'Smith', 
            'email': 'john.smith@example.com',
            'mobile': '0211234567',
            'street_address': '123 Main St',
            'suburb': 'Central',
            'city': 'Auckland',
            'postcode': '1010',
            'created_by': user
        },
        {
            'first_name': 'Jon',
            'last_name': 'Smith',
            'email': 'jon.smith@test.com',  # Different email but similar name and same phone
            'mobile': '0211234567',  # Same phone number
            'street_address': '123 Main Street',
            'suburb': 'Central',
            'city': 'Auckland',
            'postcode': '1010',
            'created_by': user
        },
        
        # Similar names, different emails
        {
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'email': 'sarah.johnson@company.com',
            'mobile': '0275555123',
            'street_address': '456 Queen St',
            'suburb': 'CBD',
            'city': 'Auckland',
            'postcode': '1010',
            'created_by': user
        },
        {
            'first_name': 'Sara',
            'last_name': 'Johnston',  # Similar name
            'email': 'sara.johnston@company.com',  # Different email
            'mobile': '0275555123',  # Same phone number
            'street_address': '456 Queen Street',
            'suburb': 'CBD',
            'city': 'Auckland',
            'postcode': '1010',
            'created_by': user
        },
        
        # Similar phone numbers
        {
            'first_name': 'Mike',
            'last_name': 'Brown',
            'email': 'mike.brown@test.com',
            'mobile': '0211234567',  # Same as first duplicate pair
            'street_address': '789 Victoria St',
            'suburb': 'CBD',
            'city': 'Wellington',
            'postcode': '6011',
            'created_by': user
        },
        {
            'first_name': 'Michael',
            'last_name': 'Brown',
            'email': 'michael.brown@test.com',
            'mobile': '0211234567',  # Same number as Mike
            'street_address': '789 Victoria Street',
            'suburb': 'CBD',
            'city': 'Wellington',
            'postcode': '6011',
            'created_by': user
        },
        
        # No duplicates - control group
        {
            'first_name': 'Alice',
            'last_name': 'Wilson',
            'email': 'alice.wilson@unique.com',
            'mobile': '029876543',
            'street_address': '321 High St',
            'suburb': 'Albany',
            'city': 'Auckland',
            'postcode': '0632',
            'created_by': user
        },
        {
            'first_name': 'Bob',
            'last_name': 'Taylor',
            'email': 'bob.taylor@different.com',
            'mobile': '021999888',
            'street_address': '654 Low St',
            'suburb': 'Howick',
            'city': 'Auckland',
            'postcode': '2010',
            'created_by': user
        }
    ]
    
    created_customers = []
    for customer_data in customers:
        customer = Customer.objects.create(**customer_data)
        created_customers.append(customer)
        print(f"Created customer: {customer.full_name} ({customer.email})")
    
    print(f"\nCreated {len(created_customers)} test customers")
    print("\nExpected duplicate groups:")
    print("1. John Smith & Jon Smith (similar name + same phone: 0211234567)")
    print("2. Sarah Johnson & Sara Johnston (similar name + same phone: 0275555123)")
    print("3. Mike Brown & Michael Brown (similar name + same phone: 0211234567)")
    print("\nNote: Mike Brown and John Smith also share the same phone number")
    print("\nYou can now test the duplicate detection at: http://127.0.0.1:8000/customers/duplicates/")

if __name__ == '__main__':
    create_test_duplicates()