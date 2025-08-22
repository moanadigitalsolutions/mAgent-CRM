import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magent.settings')
django.setup()

from customers.models import Customer, CustomField, CustomerCustomFieldValue

# Create sample customers
customers_data = [
    {
        'first_name': 'John',
        'last_name': 'Smith',
        'email': 'john.smith@email.com',
        'mobile': '+64211234567',
        'street_address': '123 Queen Street',
        'suburb': 'Auckland Central',
        'city': 'Auckland',
        'postcode': '1010'
    },
    {
        'first_name': 'Sarah',
        'last_name': 'Wilson',
        'email': 'sarah.wilson@email.com',
        'mobile': '0221234568',
        'street_address': '456 Lambton Quay',
        'suburb': 'Wellington Central',
        'city': 'Wellington',
        'postcode': '6011'
    },
    {
        'first_name': 'Michael',
        'last_name': 'Brown',
        'email': 'michael.brown@email.com',
        'mobile': '+64271234569',
        'street_address': '789 Cashel Street',
        'suburb': 'Christchurch Central',
        'city': 'Christchurch',
        'postcode': '8011'
    },
    {
        'first_name': 'Emma',
        'last_name': 'Davis',
        'email': 'emma.davis@email.com',
        'mobile': '0291234570',
        'street_address': '321 Devon Street',
        'suburb': 'New Plymouth Central',
        'city': 'New Plymouth',
        'postcode': '4310'
    },
    {
        'first_name': 'James',
        'last_name': 'Taylor',
        'email': 'james.taylor@email.com',
        'mobile': '+64211234571',
        'street_address': '654 George Street',
        'suburb': 'Dunedin Central',
        'city': 'Dunedin',
        'postcode': '9016'
    }
]

print("Creating sample customers...")
for customer_data in customers_data:
    customer, created = Customer.objects.get_or_create(
        email=customer_data['email'],
        defaults=customer_data
    )
    if created:
        print(f"Created customer: {customer.full_name}")
    else:
        print(f"Customer already exists: {customer.full_name}")

# Create sample custom fields
custom_fields_data = [
    {
        'name': 'company',
        'label': 'Company',
        'field_type': 'text',
        'is_required': False,
        'is_active': True
    },
    {
        'name': 'company_size',
        'label': 'Company Size',
        'field_type': 'select',
        'options': 'Small (1-10), Medium (11-50), Large (51-200), Enterprise (200+)',
        'is_required': False,
        'is_active': True
    },
    {
        'name': 'industry',
        'label': 'Industry',
        'field_type': 'select',
        'options': 'Technology, Healthcare, Finance, Education, Retail, Manufacturing, Other',
        'is_required': False,
        'is_active': True
    },
    {
        'name': 'preferred_contact',
        'label': 'Preferred Contact Method',
        'field_type': 'select',
        'options': 'Email, Phone, SMS, Post',
        'is_required': False,
        'is_active': True
    },
    {
        'name': 'notes',
        'label': 'Notes',
        'field_type': 'textarea',
        'is_required': False,
        'is_active': True
    }
]

print("\nCreating custom fields...")
for field_data in custom_fields_data:
    custom_field, created = CustomField.objects.get_or_create(
        name=field_data['name'],
        defaults=field_data
    )
    if created:
        print(f"Created custom field: {custom_field.label}")
    else:
        print(f"Custom field already exists: {custom_field.label}")

# Add sample custom field values
print("\nAdding sample custom field values...")
customers = Customer.objects.all()
company_field = CustomField.objects.get(name='company')
company_size_field = CustomField.objects.get(name='company_size')
industry_field = CustomField.objects.get(name='industry')
preferred_contact_field = CustomField.objects.get(name='preferred_contact')

sample_values = [
    {
        'customer': customers[0],
        'values': {
            company_field: 'Tech Solutions Ltd',
            company_size_field: 'Medium (11-50)',
            industry_field: 'Technology',
            preferred_contact_field: 'Email'
        }
    },
    {
        'customer': customers[1],
        'values': {
            company_field: 'Wellington Health Group',
            company_size_field: 'Large (51-200)',
            industry_field: 'Healthcare',
            preferred_contact_field: 'Phone'
        }
    },
    {
        'customer': customers[2],
        'values': {
            company_field: 'Canterbury Finance',
            company_size_field: 'Medium (11-50)',
            industry_field: 'Finance',
            preferred_contact_field: 'Email'
        }
    }
]

for sample in sample_values:
    customer = sample['customer']
    for field, value in sample['values'].items():
        custom_value, created = CustomerCustomFieldValue.objects.get_or_create(
            customer=customer,
            custom_field=field,
            defaults={'value': value}
        )
        if created:
            print(f"Added {field.label} for {customer.full_name}: {value}")

print("\nSample data creation completed!")
print("\nYou can now:")
print("1. Visit http://127.0.0.1:8000/ to see the dashboard")
print("2. Visit http://127.0.0.1:8000/customers/ to see the customer list")
print("3. Visit http://127.0.0.1:8000/admin/ to access the admin panel")
print("   Username: admin")
print("   Password: [the password you set during superuser creation]")