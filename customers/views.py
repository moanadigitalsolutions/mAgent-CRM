from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.files.storage import default_storage
import json

from .models import Customer, CustomField, CustomerCustomFieldValue, CustomerFile
from .forms import CustomerForm, CustomFieldForm, CustomerFileForm


class CustomerListView(View):
    """Monday.com style customer list with inline editing"""
    
    def get(self, request):
        customers = Customer.objects.filter(is_active=True)
        
        # Search functionality
        search_query = request.GET.get('search', '')
        if search_query:
            customers = customers.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(email__icontains=search_query) |
                Q(mobile__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(suburb__icontains=search_query)
            )
        
        # Filter by city
        city_filter = request.GET.get('city', '')
        if city_filter:
            customers = customers.filter(city__icontains=city_filter)
        
        # Filter by active status
        active_filter = request.GET.get('active', '')
        if active_filter:
            customers = customers.filter(is_active=active_filter.lower() == 'true')
        
        # Ordering
        order_by = request.GET.get('order_by', 'last_name')
        if order_by:
            customers = customers.order_by(order_by)
        
        # Pagination
        paginator = Paginator(customers, 25)  # 25 customers per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        # Get custom fields for display
        custom_fields = CustomField.objects.filter(is_active=True)
        
        # Statistics
        stats = {
            'total_customers': Customer.objects.filter(is_active=True).count(),
            'cities': Customer.objects.filter(is_active=True).values_list('city', flat=True).distinct().count(),
            'recent_customers': Customer.objects.filter(is_active=True).order_by('-created_at')[:5]
        }
        
        context = {
            'customers': page_obj,
            'custom_fields': custom_fields,
            'search_query': search_query,
            'city_filter': city_filter,
            'stats': stats,
            'order_by': order_by,
        }
        
        return render(request, 'customers/customer_list.html', context)


def customer_detail(request, pk):
    """Customer detail view with custom fields and files"""
    customer = get_object_or_404(Customer, pk=pk)
    custom_fields = CustomField.objects.filter(is_active=True)
    
    # Get custom field values for this customer
    custom_values = {}
    for field in custom_fields:
        try:
            value = CustomerCustomFieldValue.objects.get(
                customer=customer, 
                custom_field=field
            ).value
            custom_values[field.pk] = value
        except CustomerCustomFieldValue.DoesNotExist:
            custom_values[field.pk] = ''
    
    # Get customer files
    files = customer.files.all().order_by('-uploaded_at')
    
    context = {
        'customer': customer,
        'custom_fields': custom_fields,
        'custom_values': custom_values,
        'files': files,
    }
    
    return render(request, 'customers/customer_detail.html', context)


def customer_create(request):
    """Create new customer"""
    custom_fields = CustomField.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save()
            
            # Handle custom fields
            for field in custom_fields:
                field_name = f'custom_{field.pk}'
                if field_name in request.POST:
                    field_value = request.POST.get(field_name, '').strip()
                    
                    if field_value:  # Only save if value is provided
                        CustomerCustomFieldValue.objects.create(
                            customer=customer,
                            custom_field=field,
                            value=field_value
                        )
            
            messages.success(request, f'Customer {customer.full_name} created successfully!')
            return redirect('customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm()
    
    # Initialize empty custom values for new customer
    custom_values = {field.pk: '' for field in custom_fields}
    
    return render(request, 'customers/customer_form.html', {
        'form': form,
        'custom_fields': custom_fields,
        'custom_values': custom_values,
        'title': 'Add New Customer'
    })


def customer_edit(request, pk):
    """Edit existing customer"""
    customer = get_object_or_404(Customer, pk=pk)
    custom_fields = CustomField.objects.filter(is_active=True)
    
    # Get existing custom field values
    custom_values = {}
    for field in custom_fields:
        try:
            value = CustomerCustomFieldValue.objects.get(
                customer=customer, 
                custom_field=field
            ).value
            custom_values[field.pk] = value
        except CustomerCustomFieldValue.DoesNotExist:
            custom_values[field.pk] = ''
    
    if request.method == 'POST':
        form = CustomerForm(request.POST, instance=customer)
        if form.is_valid():
            customer = form.save()
            
            # Handle custom fields
            for field in custom_fields:
                field_name = f'custom_{field.pk}'
                if field_name in request.POST:
                    field_value = request.POST.get(field_name, '').strip()
                    
                    # Update or create custom field value
                    custom_value, created = CustomerCustomFieldValue.objects.get_or_create(
                        customer=customer,
                        custom_field=field,
                        defaults={'value': field_value}
                    )
                    if not created:
                        custom_value.value = field_value
                        custom_value.save()
            
            messages.success(request, f'Customer {customer.full_name} updated successfully!')
            return redirect('customers:customer_detail', pk=customer.pk)
    else:
        form = CustomerForm(instance=customer)
    
    return render(request, 'customers/customer_form.html', {
        'form': form,
        'customer': customer,
        'custom_fields': custom_fields,
        'custom_values': custom_values,
        'title': f'Edit {customer.full_name}'
    })


def customer_delete(request, pk):
    """Soft delete customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        customer.is_active = False
        customer.save()
        messages.success(request, f'Customer {customer.full_name} deleted successfully!')
        return redirect('customers:customer_list')
    
    return render(request, 'customers/customer_delete.html', {
        'customer': customer
    })


@require_POST
def customer_update_field(request, pk):
    """AJAX endpoint for inline editing"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if not request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'error': 'Invalid request'})
    
    field_name = request.POST.get('field')
    field_value = request.POST.get('value', '').strip()
    
    try:
        # Check if it's a custom field
        if field_name.startswith('custom_'):
            custom_field_id = field_name.replace('custom_', '')
            custom_field = get_object_or_404(CustomField, id=custom_field_id, is_active=True)
            
            # Update or create custom field value
            custom_value, created = CustomerCustomFieldValue.objects.get_or_create(
                customer=customer,
                custom_field=custom_field,
                defaults={'value': field_value}
            )
            if not created:
                custom_value.value = field_value
                custom_value.save()
                
        else:
            # Update regular field
            if hasattr(customer, field_name):
                setattr(customer, field_name, field_value)
                customer.save()
            else:
                return JsonResponse({'success': False, 'error': 'Invalid field name'})
        
        return JsonResponse({'success': True, 'message': 'Field updated successfully'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


def customer_upload_files(request, pk):
    """Upload files for customer"""
    customer = get_object_or_404(Customer, pk=pk)
    
    if request.method == 'POST':
        files = request.FILES.getlist('files')
        uploaded = []
        description = request.POST.get('description', '')

        for file in files:
            # Basic extension-based classification (model save will refine if needed)
            file_type = 'other'
            file_extension = file.name.lower().rsplit('.', 1)[-1] if '.' in file.name else ''
            if file_extension in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']:
                file_type = 'image'
            elif file_extension in ['mp4', 'avi', 'mov', 'wmv', 'flv', 'webm', 'mkv']:
                file_type = 'video'
            elif file_extension in ['mp3', 'wav', 'ogg', 'aac', 'flac', 'm4a']:
                file_type = 'audio'
            elif file_extension in ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'csv', 'json', 'xml', 'log']:
                file_type = 'document'

            customer_file = CustomerFile.objects.create(
                customer=customer,
                file=file,
                file_type=file_type,
                description=description
            )

            uploaded.append({
                'id': customer_file.id,
                'url': customer_file.file.url,
                'name': customer_file.file.name.split('/')[-1],
                'type': customer_file.file_type,
                'size': customer_file.file_size,
                'uploaded_at': customer_file.uploaded_at.strftime('%b %d, %Y'),
                'description': customer_file.description or ''
            })

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'uploaded_count': len(uploaded),
                'files': uploaded,
                'message': f"{len(uploaded)} file(s) uploaded successfully"
            })
        else:
            messages.success(request, f"{len(uploaded)} file(s) uploaded successfully!")
            return redirect('customers:customer_detail', pk=customer.pk)
    
    return redirect('customers:customer_detail', pk=customer.pk)


def customer_delete_file(request, pk, file_id):
    """Delete customer file"""
    customer = get_object_or_404(Customer, pk=pk)
    file = get_object_or_404(CustomerFile, pk=file_id, customer=customer)
    
    if request.method == 'POST':
        # Delete physical file
        if file.file:
            default_storage.delete(file.file.name)
        
        file.delete()
        messages.success(request, 'File deleted successfully!')
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'File deleted successfully'})
    
    return redirect('customers:customer_detail', pk=customer.pk)


# Custom Fields Views
def custom_field_list(request):
    """List all custom fields"""
    custom_fields = CustomField.objects.all().order_by('name')
    
    context = {
        'custom_fields': custom_fields,
    }
    
    return render(request, 'customers/custom_field_list.html', context)


def custom_field_create(request):
    """Create new custom field"""
    if request.method == 'POST':
        form = CustomFieldForm(request.POST)
        if form.is_valid():
            custom_field = form.save()
            messages.success(request, f'Custom field "{custom_field.label}" created successfully!')
            return redirect('customers:custom_field_list')
    else:
        form = CustomFieldForm()
    
    return render(request, 'customers/custom_field_form.html', {
        'form': form,
        'title': 'Add Custom Field'
    })


def custom_field_edit(request, pk):
    """Edit custom field"""
    custom_field = get_object_or_404(CustomField, pk=pk)
    
    if request.method == 'POST':
        form = CustomFieldForm(request.POST, instance=custom_field)
        if form.is_valid():
            custom_field = form.save()
            messages.success(request, f'Custom field "{custom_field.label}" updated successfully!')
            return redirect('customers:custom_field_list')
    else:
        form = CustomFieldForm(instance=custom_field)
    
    return render(request, 'customers/custom_field_form.html', {
        'form': form,
        'custom_field': custom_field,
        'title': f'Edit {custom_field.label}'
    })


def custom_field_delete(request, pk):
    """Delete custom field"""
    custom_field = get_object_or_404(CustomField, pk=pk)
    
    if request.method == 'POST':
        custom_field.delete()
        messages.success(request, f'Custom field "{custom_field.label}" deleted successfully!')
        return redirect('customers:custom_field_list')
    
    return render(request, 'customers/custom_field_delete.html', {
        'custom_field': custom_field
    })


def dashboard(request):
    """Dashboard with statistics and recent activity"""
    # Statistics
    total_customers = Customer.objects.filter(is_active=True).count()
    recent_customers = Customer.objects.filter(is_active=True).order_by('-created_at')[:5]
    
    # City breakdown
    city_stats = {}
    cities = Customer.objects.filter(is_active=True).values_list('city', flat=True)
    for city in cities:
        city_stats[city] = city_stats.get(city, 0) + 1
    
    # Recent files
    recent_files = CustomerFile.objects.order_by('-uploaded_at')[:5]
    
    context = {
        'total_customers': total_customers,
        'recent_customers': recent_customers,
        'city_stats': city_stats,
        'recent_files': recent_files,
        'custom_fields_count': CustomField.objects.filter(is_active=True).count(),
    }
    
    return render(request, 'customers/dashboard.html', context)
