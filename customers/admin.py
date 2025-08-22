from django.contrib import admin
from .models import Customer, CustomField, CustomerCustomFieldValue, CustomerFile


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'mobile', 'city', 'is_active', 'created_at']
    list_filter = ['is_active', 'city', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'mobile']
    list_editable = ['is_active']
    ordering = ['last_name', 'first_name']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Personal Information', {
            'fields': ('first_name', 'last_name', 'email', 'mobile')
        }),
        ('Address', {
            'fields': ('street_address', 'suburb', 'city', 'postcode')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = 'Name'


@admin.register(CustomField)
class CustomFieldAdmin(admin.ModelAdmin):
    list_display = ['label', 'name', 'field_type', 'is_required', 'is_active', 'created_at']
    list_filter = ['field_type', 'is_required', 'is_active']
    search_fields = ['name', 'label']
    list_editable = ['is_required', 'is_active']
    ordering = ['name']


@admin.register(CustomerCustomFieldValue)
class CustomerCustomFieldValueAdmin(admin.ModelAdmin):
    list_display = ['customer', 'custom_field', 'value_preview']
    list_filter = ['custom_field']
    search_fields = ['customer__first_name', 'customer__last_name', 'value']
    
    def value_preview(self, obj):
        return obj.value[:50] + '...' if len(obj.value) > 50 else obj.value
    value_preview.short_description = 'Value'


@admin.register(CustomerFile)
class CustomerFileAdmin(admin.ModelAdmin):
    list_display = ['customer', 'file_name', 'file_type', 'file_size', 'uploaded_at']
    list_filter = ['file_type', 'uploaded_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'description']
    date_hierarchy = 'uploaded_at'
    
    def file_name(self, obj):
        return obj.file.name.split('/')[-1]
    file_name.short_description = 'File Name'


# Customize admin site header
admin.site.site_header = "mAgent CRM Administration"
admin.site.site_title = "mAgent CRM Admin"
admin.site.index_title = "Welcome to mAgent CRM Admin Panel"
