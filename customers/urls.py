from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    
    # Customer URLs
    path('customers/', views.CustomerListView.as_view(), name='customer_list'),
    path('customers/add/', views.customer_create, name='customer_create'),
    path('customers/<int:pk>/', views.customer_detail, name='customer_detail'),
    path('customers/<int:pk>/edit/', views.customer_edit, name='customer_edit'),
    path('customers/<int:pk>/delete/', views.customer_delete, name='customer_delete'),
    
    # AJAX endpoints
    path('customers/<int:pk>/update-field/', views.customer_update_field, name='customer_update_field'),
    path('customers/<int:pk>/upload-files/', views.customer_upload_files, name='customer_upload_files'),
    path('customers/<int:pk>/files/<int:file_id>/delete/', views.customer_delete_file, name='customer_delete_file'),
    
    # Custom Fields URLs
    path('custom-fields/', views.custom_field_list, name='custom_field_list'),
    path('custom-fields/add/', views.custom_field_create, name='custom_field_create'),
    path('custom-fields/<int:pk>/edit/', views.custom_field_edit, name='custom_field_edit'),
    path('custom-fields/<int:pk>/delete/', views.custom_field_delete, name='custom_field_delete'),
]