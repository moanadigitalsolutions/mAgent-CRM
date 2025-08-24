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
    
    # Clear existing test customers
    Customer.objects.filter(email__icontains='test').delete()
    print("Cleared existing test customers")
    
    # Create potential duplicates - same email
    customers = [
        {
            'first_name': 'John',
            'last_name': 'Smith', 
            'email': 'john.smith@example.com',
            'mobile': '021234567',
            'company': 'ABC Corp',
            'created_by': user
        },
        {
            'first_name': 'Jon',
            'last_name': 'Smith',
            'email': 'john.smith@example.com',  # Same email - should be detected
            'mobile': '02123-4567',  # Same phone, different format
            'company': 'ABC Corporation',
            'created_by': user
        },
        
        # Similar names, different emails
        {
            'first_name': 'Sarah',
            'last_name': 'Johnson',
            'email': 'sarah.johnson@company.com',
            'mobile': '027555123',
            'company': 'XYZ Ltd',
            'created_by': user
        },
        {
            'first_name': 'Sara',
            'last_name': 'Johnston',  # Similar name
            'email': 'sara.j@company.com', 
            'mobile': '027-555-123',  # Same phone, different format
            'company': 'XYZ Limited',
            'created_by': user
        },
        
        # Similar phone numbers
        {
            'first_name': 'Mike',
            'last_name': 'Brown',
            'email': 'mike.brown@test.com',
            'mobile': '+64211234567',  # NZ format
            'company': 'Tech Solutions',
            'created_by': user
        },
        {
            'first_name': 'Michael',
            'last_name': 'Brown',
            'email': 'michael.b@test.com',
            'mobile': '0211234567',  # Same number, different format
            'company': 'Tech Solutions Ltd',
            'created_by': user
        },
        
        # No duplicates - control group
        {
            'first_name': 'Alice',
            'last_name': 'Wilson',
            'email': 'alice.wilson@unique.com',
            'mobile': '029876543',
            'company': 'Unique Business',
            'created_by': user
        },
        {
            'first_name': 'Bob',
            'last_name': 'Taylor',
            'email': 'bob.taylor@different.com',
            'mobile': '021999888',
            'company': 'Different Corp',
            'created_by': user
        }
    ]
    
    created_customers = []
    for customer_data in customers:
        customer = Customer.objects.create(**customer_data)
        created_customers.append(customer)
        print(f"Created customer: {customer.get_full_name()} ({customer.email})")
    
    print(f"\nCreated {len(created_customers)} test customers")
    print("\nExpected duplicate groups:")
    print("1. John Smith & Jon Smith (same email + similar name + same phone)")
    print("2. Sarah Johnson & Sara Johnston (similar name + same phone)")
    print("3. Mike Brown & Michael Brown (similar name + same phone)")
    print("\nYou can now test the duplicate detection at: http://127.0.0.1:8000/customers/duplicates/")

if __name__ == '__main__':
    create_test_duplicates()