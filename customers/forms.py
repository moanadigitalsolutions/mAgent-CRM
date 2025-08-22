from django import forms
from django.core.validators import RegexValidator
from .models import Customer, CustomField, CustomerFile


class CustomerForm(forms.ModelForm):
    """Form for creating and editing customers"""
    
    class Meta:
        model = Customer
        fields = [
            'first_name', 'last_name', 'mobile', 'email',
            'street_address', 'suburb', 'city', 'postcode', 'is_active'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter last name'
            }),
            'mobile': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., +64211234567 or 0211234567'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter email address'
            }),
            'street_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter street address'
            }),
            'suburb': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter suburb'
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Auckland, Wellington, Christchurch'
            }),
            'postcode': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter 4-digit postcode'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_mobile(self):
        mobile = self.cleaned_data.get('mobile')
        if mobile:
            # Remove spaces and formatting
            mobile = mobile.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            
            # Validate NZ mobile format
            nz_mobile_regex = RegexValidator(
                regex=r'^\+?64\d{8,9}$|^0\d{8,9}$',
                message="Please enter a valid New Zealand mobile number"
            )
            nz_mobile_regex(mobile)
        
        return mobile


class CustomFieldForm(forms.ModelForm):
    """Form for creating and editing custom fields"""
    
    class Meta:
        model = CustomField
        fields = ['name', 'label', 'field_type', 'options', 'is_required', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., company_size (no spaces, lowercase)'
            }),
            'label': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Company Size'
            }),
            'field_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'options': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'For dropdown fields, enter options separated by commas. e.g., Small, Medium, Large'
            }),
            'is_required': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if name:
            # Ensure name is lowercase and contains no spaces
            name = name.lower().replace(' ', '_')
            
            # Check for valid field name format
            import re
            if not re.match(r'^[a-z][a-z0-9_]*$', name):
                raise forms.ValidationError(
                    'Field name must start with a letter and contain only lowercase letters, numbers, and underscores.'
                )
        
        return name


class CustomerFileForm(forms.ModelForm):
    """Form for uploading customer files"""
    
    class Meta:
        model = CustomerFile
        fields = ['file', 'file_type', 'description']
        widgets = {
            'file': forms.FileInput(attrs={
                'class': 'form-control'
            }),
            'file_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Optional description for the file'
            })
        }


class CustomerSearchForm(forms.Form):
    """Form for searching customers"""
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search customers by name, email, mobile, or location...',
            'id': 'search-input'
        })
    )
    
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by city'
        })
    )
    
    is_active = forms.ChoiceField(
        choices=[('', 'All'), ('true', 'Active'), ('false', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    order_by = forms.ChoiceField(
        choices=[
            ('last_name', 'Last Name A-Z'),
            ('-last_name', 'Last Name Z-A'),
            ('first_name', 'First Name A-Z'),
            ('-first_name', 'First Name Z-A'),
            ('email', 'Email A-Z'),
            ('-email', 'Email Z-A'),
            ('city', 'City A-Z'),
            ('-city', 'City Z-A'),
            ('created_at', 'Oldest First'),
            ('-created_at', 'Newest First'),
        ],
        required=False,
        initial='last_name',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )


class BulkActionForm(forms.Form):
    """Form for bulk actions on customers"""
    
    ACTION_CHOICES = [
        ('', 'Select Action'),
        ('activate', 'Activate Selected'),
        ('deactivate', 'Deactivate Selected'),
        ('delete', 'Delete Selected'),
        ('export', 'Export Selected'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    selected_customers = forms.CharField(
        widget=forms.HiddenInput()
    )