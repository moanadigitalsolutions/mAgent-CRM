from django.db import models
from django.core.validators import RegexValidator


class Customer(models.Model):
    """Customer model for New Zealand CRM"""
    
    # Core fields
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    # Contact information
    mobile_validator = RegexValidator(
        regex=r'^\+?64\d{8,9}$|^0\d{8,9}$',
        message="Please enter a valid New Zealand mobile number (e.g., +64211234567 or 0211234567)"
    )
    mobile = models.CharField(max_length=15, validators=[mobile_validator])
    email = models.EmailField(unique=True)
    
    # Address fields for New Zealand
    street_address = models.CharField(max_length=200)
    suburb = models.CharField(max_length=100)
    city = models.CharField(max_length=100)
    postcode = models.CharField(max_length=4, validators=[
        RegexValidator(regex=r'^\d{4}$', message="Enter a valid 4-digit postcode")
    ])
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['last_name', 'first_name']
        
    def __str__(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def full_address(self):
        return f"{self.street_address}, {self.suburb}, {self.city} {self.postcode}"


class CustomField(models.Model):
    """Custom fields that can be added to customer profiles"""
    
    FIELD_TYPES = [
        ('text', 'Text'),
        ('number', 'Number'),
        ('email', 'Email'),
        ('date', 'Date'),
        ('boolean', 'Yes/No'),
        ('textarea', 'Long Text'),
        ('select', 'Dropdown'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    label = models.CharField(max_length=100)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)
    options = models.TextField(blank=True, help_text="For dropdown fields, enter options separated by commas")
    is_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['name']
        
    def __str__(self):
        return self.label
    
    def get_options_list(self):
        """Return options as a list for dropdown fields"""
        if self.options:
            return [option.strip() for option in self.options.split(',')]
        return []


class CustomerCustomFieldValue(models.Model):
    """Values for custom fields associated with customers"""
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='custom_field_values')
    custom_field = models.ForeignKey(CustomField, on_delete=models.CASCADE)
    value = models.TextField(blank=True)
    
    class Meta:
        unique_together = ['customer', 'custom_field']
        
    def __str__(self):
        return f"{self.customer} - {self.custom_field.label}: {self.value}"


class CustomerFile(models.Model):
    """Multimedia files attached to customer profiles"""
    
    FILE_TYPES = [
        ('image', 'Image'),
        ('document', 'Document'),
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('other', 'Other'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='files')
    file = models.FileField(upload_to='customer_files/%Y/%m/%d/')
    file_type = models.CharField(max_length=20, choices=FILE_TYPES, default='other')
    description = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-uploaded_at']
        
    def __str__(self):
        return f"{self.customer} - {self.file.name}"
    
    def save(self, *args, **kwargs):
        """Auto-detect file_type if still set to 'other'.

        Detection priority:
        1. Extension mapping
        2. (Optional future) MIME sniff if needed
        """
        if self.file and (not self.file_type or self.file_type == 'other'):
            name = self.file.name.lower()
            # Extension-based detection
            ext_map = {
                'image': ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.svg'],
                'video': ['.mp4', '.mov', '.avi', '.wmv', '.flv', '.mkv', '.webm'],
                'audio': ['.mp3', '.wav', '.ogg', '.aac', '.flac', '.m4a'],
                'document': ['.pdf', '.txt', '.md', '.log', '.csv', '.json', '.xml', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.html', '.css', '.js', '.py', '.java', '.cpp', '.c', '.h']
            }
            detected = None
            for ftype, exts in ext_map.items():
                if any(name.endswith(ext) for ext in exts):
                    detected = ftype
                    break
            if detected:
                self.file_type = detected
        super().save(*args, **kwargs)
    
    @property
    def file_size(self):
        """Get file size in human-readable format"""
        try:
            size = self.file.size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024.0:
                    return f"{size:.1f} {unit}"
                size /= 1024.0
            return f"{size:.1f} TB"
        except:
            return "Unknown"
