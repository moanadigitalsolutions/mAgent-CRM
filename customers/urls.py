from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Customer URLs
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', views.customer_create, name='customer_create'),
    path('customers/duplicates/', views.duplicate_detection, name='duplicate_detection'),
    path('customers/export/', views.export_customers_page, name='export_customers_page'),
    path('customers/export/download/', views.export_customers_csv, name='export_customers_csv'),
    path('customers/import/', views.import_customers_page, name='import_customers_page'),
    path('customers/import/upload/', views.import_customers_csv, name='import_customers_csv'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # AJAX endpoints
    path('customers/<int:pk>/update-field/', views.customer_update_field, name='customer_update_field'),
    path('customers/<int:pk>/upload-files/', views.customer_upload_files, name='customer_upload_files'),
    path('customers/<int:pk>/files/<int:file_id>/delete/', views.customer_delete_file, name='customer_delete_file'),
    path('customers/<int:pk>/add-tag/', views.add_tag_to_customer, name='add_tag_to_customer'),
    path('customers/<int:pk>/remove-tag/', views.remove_tag_from_customer, name='remove_tag_from_customer'),
    path('customers/<int:pk>/add-note/', views.add_customer_note, name='add_customer_note'),
    path('customers/<int:pk>/notes/', views.customer_notes_list, name='customer_notes_list'),
    path('customers/<int:pk>/check-duplicates/', views.check_customer_duplicates, name='check_customer_duplicates'),
    path('customers/<int:pk>/ignore-duplicate/', views.ignore_duplicate, name='ignore_duplicate'),
    
    # Validation endpoints
    path('validate/email/', views.validate_email, name='validate_email'),
    path('validate/mobile/', views.validate_mobile, name='validate_mobile'),
    path('validate/postcode/', views.validate_postcode, name='validate_postcode'),
    
    # Custom Fields URLs
    path('custom-fields/', views.custom_field_list, name='custom_field_list'),
    path('custom-fields/add/', views.custom_field_create, name='custom_field_create'),
    path('custom-fields/<int:pk>/edit/', views.custom_field_edit, name='custom_field_edit'),
    path('custom-fields/<int:pk>/delete/', views.custom_field_delete, name='custom_field_delete'),
]