from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator
from django.db.models import Q
from django.views.decorators.http import require_POST
from django.views import View
from django.core.files.storage import default_storage
import json
import csv
from datetime import datetime

from .models import Customer, CustomField, CustomerCustomFieldValue, CustomerFile, Tag, CustomerNote
from .forms import CustomerForm, CustomFieldForm, CustomerFileForm


@method_decorator(login_required, name='dispatch')
class CustomerListView(View):
    """Customer list with search & filters (login required)"""

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

        # Filter by tag (single or multiple comma-separated)
        tag_filter = request.GET.get('tag', '')
        selected_tags = []
        if tag_filter:
            tag_slugs = [t.strip() for t in tag_filter.split(',') if t.strip()]
            if tag_slugs:
                tag_objs = Tag.objects.filter(slug__in=tag_slugs)
                selected_tags = list(tag_objs.values_list('slug', flat=True))
                for t in tag_objs:
                    customers = customers.filter(tags=t)
        
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
        
        all_tags = Tag.objects.all().order_by('name')

        context = {
            'customers': page_obj,
            'custom_fields': custom_fields,
            'search_query': search_query,
            'city_filter': city_filter,
            'stats': stats,
            'order_by': order_by,
            'all_tags': all_tags,
            'selected_tags': selected_tags,
            'tag_filter': tag_filter,
        }
        
        return render(request, 'customers/customer_list.html', context)


@login_required
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
    
    # Get recent notes (limit to first 10 for initial load)
    notes = customer.notes.select_related('created_by').all()[:10]
    
    # Gather tags
    all_tags = Tag.objects.all().order_by('name')

    context = {
        'customer': customer,
        'custom_fields': custom_fields,
        'custom_values': custom_values,
        'files': files,
        'notes': notes,
        'all_tags': all_tags,
    }
    
    return render(request, 'customers/customer_detail.html', context)


@login_required
def customer_create(request):
    """Create new customer"""
    custom_fields = CustomField.objects.filter(is_active=True)
    
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save(commit=False)
            if request.user.is_authenticated:
                customer.created_by = request.user
            customer.save()
            
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
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
@login_required
def custom_field_list(request):
    """List all custom fields"""
    custom_fields = CustomField.objects.all().order_by('name')
    
    context = {
        'custom_fields': custom_fields,
    }
    
    return render(request, 'customers/custom_field_list.html', context)


@login_required
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


@login_required
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


@login_required
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


@login_required
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


@login_required
@require_POST
def add_tag_to_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.user.groups.filter(name='ReadOnly').exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    tag_name = request.POST.get('tag', '').strip()
    color = request.POST.get('color', '#0d6efd')
    if not tag_name:
        return JsonResponse({'success': False, 'error': 'Tag name required'}, status=400)
    tag, _ = Tag.objects.get_or_create(name=tag_name, defaults={'color': color})
    customer.tags.add(tag)
    return JsonResponse({'success': True, 'tag': {'name': tag.name, 'slug': tag.slug, 'color': tag.color}})


@login_required
@require_POST
def remove_tag_from_customer(request, pk):
    customer = get_object_or_404(Customer, pk=pk)
    if request.user.groups.filter(name='ReadOnly').exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    tag_slug = request.POST.get('tag', '').strip()
    if not tag_slug:
        return JsonResponse({'success': False, 'error': 'Tag slug required'}, status=400)
    try:
        tag = Tag.objects.get(slug=tag_slug)
        customer.tags.remove(tag)
        return JsonResponse({'success': True})
    except Tag.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Tag not found'}, status=404)


@login_required
@require_POST
def add_customer_note(request, pk):
    """Add a new note to a customer"""
    customer = get_object_or_404(Customer, pk=pk)
    if request.user.groups.filter(name='ReadOnly').exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    note_content = request.POST.get('note', '').strip()
    note_type = request.POST.get('note_type', 'general')
    is_important = request.POST.get('is_important') == 'on'
    
    if not note_content:
        return JsonResponse({'success': False, 'error': 'Note content is required'}, status=400)
    
    note = CustomerNote.objects.create(
        customer=customer,
        note=note_content,
        note_type=note_type,
        is_important=is_important,
        created_by=request.user
    )
    
    return JsonResponse({
        'success': True,
        'note': {
            'id': note.id,
            'note': note.note,
            'note_type': note.note_type,
            'note_type_display': note.get_note_type_display(),
            'is_important': note.is_important,
            'created_at': note.created_at.strftime('%Y-%m-%d %H:%M'),
            'created_by': note.created_by.username,
        }
    })


@login_required
def customer_notes_list(request, pk):
    """Get paginated notes for a customer"""
    customer = get_object_or_404(Customer, pk=pk)
    offset = int(request.GET.get('offset', 0))
    limit = int(request.GET.get('limit', 10))
    
    notes = customer.notes.select_related('created_by').all()[offset:offset + limit]
    has_more = customer.notes.count() > offset + limit
    
    notes_data = []
    for note in notes:
        notes_data.append({
            'id': note.id,
            'note': note.note,
            'note_type': note.note_type,
            'note_type_display': note.get_note_type_display(),
            'is_important': note.is_important,
            'created_at': note.created_at.strftime('%Y-%m-%d %H:%M'),
            'created_by': note.created_by.username,
        })
    
    return JsonResponse({
        'success': True,
        'notes': notes_data,
        'has_more': has_more,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def duplicate_detection(request):
    """View to display potential duplicate customers."""
    from .utils import get_duplicate_summary
    
    duplicate_groups = get_duplicate_summary()
    
    context = {
        'duplicate_groups': duplicate_groups,
        'total_groups': len(duplicate_groups),
        'total_duplicates': sum(group['group_size'] for group in duplicate_groups),
    }
    
    return render(request, 'customers/duplicate_detection.html', context)


@login_required
def check_customer_duplicates(request, pk):
    """AJAX endpoint to check for duplicates of a specific customer."""
    customer = get_object_or_404(Customer, pk=pk)
    from .utils import find_potential_duplicates
    
    duplicates = find_potential_duplicates(customer=customer)
    
    duplicates_data = []
    for dup in duplicates:
        duplicates_data.append({
            'id': dup['customer'].id,
            'full_name': dup['customer'].full_name,
            'email': dup['customer'].email,
            'mobile': dup['customer'].mobile,
            'created_at': dup['customer'].created_at.strftime('%Y-%m-%d'),
            'confidence_score': dup['confidence_score'],
            'match_reasons': dup['match_reasons'],
        })
    
    return JsonResponse({
        'success': True,
        'duplicates': duplicates_data,
    })


@login_required
@require_POST
def ignore_duplicate(request, pk):
    """Mark a duplicate as ignored (placeholder for future implementation)."""
    if request.user.groups.filter(name='ReadOnly').exists():
        return JsonResponse({'success': False, 'error': 'Permission denied'}, status=403)
    
    # For now, just return success - in a full implementation, 
    # you might want to store ignored duplicates in the database
    return JsonResponse({'success': True, 'message': 'Duplicate marked as ignored'})


@login_required
def export_customers_csv(request):
    """Export customers to CSV format"""
    # Create HTTP response with CSV content type
    response = HttpResponse(content_type='text/csv')
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    response['Content-Disposition'] = f'attachment; filename="customers_export_{timestamp}.csv"'
    
    # Get all active customers
    customers = Customer.objects.filter(is_active=True).select_related('created_by').prefetch_related('tags', 'custom_field_values__custom_field')
    
    # Apply search filters if provided
    search_query = request.GET.get('search', '')
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(mobile__icontains=search_query)
        )
    
    # Apply tag filter if provided
    tag_filter = request.GET.get('tag', '')
    if tag_filter:
        tag_slugs = [t.strip() for t in tag_filter.split(',') if t.strip()]
        if tag_slugs:
            customers = customers.filter(tags__slug__in=tag_slugs).distinct()
    
    # Apply city filter if provided
    city_filter = request.GET.get('city', '')
    if city_filter:
        customers = customers.filter(city__icontains=city_filter)
    
    # Get all active custom fields for headers
    custom_fields = CustomField.objects.filter(is_active=True).order_by('name')
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    headers = [
        'ID',
        'First Name',
        'Last Name', 
        'Email',
        'Mobile',
        'Street Address',
        'Suburb',
        'City',
        'Postcode',
        'Tags',
        'Created At',
        'Created By',
        'Active'
    ]
    
    # Add custom field headers
    for field in custom_fields:
        headers.append(f'Custom: {field.label}')
    
    writer.writerow(headers)
    
    # Write customer data
    for customer in customers:
        # Get custom field values for this customer
        custom_values = {}
        for cf_value in customer.custom_field_values.all():
            custom_values[cf_value.custom_field.id] = cf_value.value
        
        # Prepare row data
        row = [
            customer.id,
            customer.first_name,
            customer.last_name,
            customer.email,
            customer.mobile,
            customer.street_address,
            customer.suburb,
            customer.city,
            customer.postcode,
            ', '.join([tag.name for tag in customer.tags.all()]),
            customer.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            customer.created_by.username if customer.created_by else '',
            'Yes' if customer.is_active else 'No'
        ]
        
        # Add custom field values
        for field in custom_fields:
            row.append(custom_values.get(field.id, ''))
        
        writer.writerow(row)
    
    return response


@login_required 
@user_passes_test(lambda u: u.is_superuser)
def export_customers_page(request):
    """Page to configure and download customer exports"""
    # Get filter options for the form
    cities = Customer.objects.filter(is_active=True).values_list('city', flat=True).distinct().order_by('city')
    cities = [city for city in cities if city]  # Remove empty cities
    
    tags = Tag.objects.all().order_by('name')
    custom_fields = CustomField.objects.filter(is_active=True).order_by('name')
    
    # Get current filter values
    search_query = request.GET.get('search', '')
    selected_city = request.GET.get('city', '')
    selected_tags = request.GET.get('tag', '').split(',') if request.GET.get('tag') else []
    
    # Get count of customers that would be exported
    customers = Customer.objects.filter(is_active=True)
    if search_query:
        customers = customers.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(mobile__icontains=search_query)
        )
    if selected_city:
        customers = customers.filter(city__icontains=selected_city)
    if selected_tags and selected_tags != ['']:
        customers = customers.filter(tags__slug__in=selected_tags).distinct()
    
    export_count = customers.count()
    
    context = {
        'cities': cities,
        'tags': tags,
        'custom_fields': custom_fields,
        'search_query': search_query,
        'selected_city': selected_city,
        'selected_tags': selected_tags,
        'export_count': export_count,
    }
    
    return render(request, 'customers/export_customers.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def import_customers_page(request):
    """Page to upload and import customer CSV files"""
    context = {
        'custom_fields': CustomField.objects.filter(is_active=True).order_by('name'),
        'sample_headers': [
            'First Name', 'Last Name', 'Email', 'Mobile', 
            'Street Address', 'Suburb', 'City', 'Postcode'
        ]
    }
    return render(request, 'customers/import_customers.html', context)


@login_required
@user_passes_test(lambda u: u.is_superuser)
def import_customers_csv(request):
    """Process uploaded CSV file and import customers"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    if 'csv_file' not in request.FILES:
        return JsonResponse({'success': False, 'error': 'No file uploaded'})
    
    csv_file = request.FILES['csv_file']
    
    # Validate file extension
    if not csv_file.name.endswith('.csv'):
        return JsonResponse({'success': False, 'error': 'File must be a CSV file'})
    
    # Validate file size (limit to 10MB)
    if csv_file.size > 10 * 1024 * 1024:
        return JsonResponse({'success': False, 'error': 'File size must be less than 10MB'})
    
    try:
        # Read CSV content
        decoded_file = csv_file.read().decode('utf-8-sig')  # utf-8-sig handles BOM
        csv_reader = csv.DictReader(decoded_file.splitlines())
        
        # Validate required headers
        required_headers = ['First Name', 'Last Name', 'Email', 'Mobile', 'Street Address', 'Suburb', 'City', 'Postcode']
        missing_headers = []
        for header in required_headers:
            if header not in csv_reader.fieldnames:
                missing_headers.append(header)
        
        if missing_headers:
            return JsonResponse({
                'success': False, 
                'error': f'Missing required columns: {", ".join(missing_headers)}'
            })
        
        # Get custom fields for mapping
        custom_fields = {}
        for field in CustomField.objects.filter(is_active=True):
            custom_field_header = f'Custom: {field.label}'
            if custom_field_header in csv_reader.fieldnames:
                custom_fields[custom_field_header] = field
        
        # Process rows
        results = {
            'total_rows': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': [],
            'duplicates_found': 0
        }
        
        # Get existing emails for duplicate checking
        existing_emails = set(Customer.objects.values_list('email', flat=True))
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 for Excel row numbers
            results['total_rows'] += 1
            
            try:
                # Clean and validate data
                email = row.get('Email', '').strip().lower()
                if not email:
                    results['errors'].append(f'Row {row_num}: Email is required')
                    results['skipped'] += 1
                    continue
                
                # Check for duplicates
                if email in existing_emails:
                    results['duplicates_found'] += 1
                    if request.POST.get('skip_duplicates') == 'true':
                        results['skipped'] += 1
                        continue
                    # If not skipping duplicates, update existing customer
                    try:
                        customer = Customer.objects.get(email=email)
                        update_customer_from_csv_row(customer, row, custom_fields, request.user)
                        results['updated'] += 1
                        continue
                    except Customer.DoesNotExist:
                        pass  # Create new customer
                
                # Create new customer
                customer_data = {
                    'first_name': row.get('First Name', '').strip(),
                    'last_name': row.get('Last Name', '').strip(),
                    'email': email,
                    'mobile': row.get('Mobile', '').strip(),
                    'street_address': row.get('Street Address', '').strip(),
                    'suburb': row.get('Suburb', '').strip(),
                    'city': row.get('City', '').strip(),
                    'postcode': row.get('Postcode', '').strip(),
                    'created_by': request.user
                }
                
                # Validate required fields
                if not customer_data['first_name']:
                    results['errors'].append(f'Row {row_num}: First Name is required')
                    results['skipped'] += 1
                    continue
                if not customer_data['last_name']:
                    results['errors'].append(f'Row {row_num}: Last Name is required')
                    results['skipped'] += 1
                    continue
                if not customer_data['mobile']:
                    results['errors'].append(f'Row {row_num}: Mobile is required')
                    results['skipped'] += 1
                    continue
                
                # Create customer
                customer = Customer.objects.create(**customer_data)
                existing_emails.add(email)  # Add to set to prevent duplicates in same file
                
                # Add custom field values
                for header, custom_field in custom_fields.items():
                    value = row.get(header, '').strip()
                    if value:
                        CustomerCustomFieldValue.objects.create(
                            customer=customer,
                            custom_field=custom_field,
                            value=value
                        )
                
                results['created'] += 1
                
            except Exception as e:
                results['errors'].append(f'Row {row_num}: {str(e)}')
                results['skipped'] += 1
        
        return JsonResponse({'success': True, 'results': results})
        
    except UnicodeDecodeError:
        return JsonResponse({'success': False, 'error': 'Unable to decode file. Please ensure it is a valid CSV file with UTF-8 encoding.'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error processing file: {str(e)}'})


def update_customer_from_csv_row(customer, row, custom_fields, user):
    """Update existing customer from CSV row data"""
    # Update basic fields
    customer.first_name = row.get('First Name', '').strip() or customer.first_name
    customer.last_name = row.get('Last Name', '').strip() or customer.last_name
    customer.mobile = row.get('Mobile', '').strip() or customer.mobile
    customer.street_address = row.get('Street Address', '').strip() or customer.street_address
    customer.suburb = row.get('Suburb', '').strip() or customer.suburb
    customer.city = row.get('City', '').strip() or customer.city
    customer.postcode = row.get('Postcode', '').strip() or customer.postcode
    customer.save()
    
    # Update custom field values
    for header, custom_field in custom_fields.items():
        value = row.get(header, '').strip()
        if value:
            field_value, created = CustomerCustomFieldValue.objects.get_or_create(
                customer=customer,
                custom_field=custom_field,
                defaults={'value': value}
            )
            if not created:
                field_value.value = value
                field_value.save()


@login_required
def validate_email(request):
    """AJAX endpoint to validate email uniqueness"""
    email = request.GET.get('email', '').strip().lower()
    customer_id = request.GET.get('customer_id')  # For edit forms
    
    if not email:
        return JsonResponse({'valid': False, 'message': 'Email is required'})
    
    # Check if email already exists
    existing_customer = Customer.objects.filter(email=email)
    if customer_id:
        existing_customer = existing_customer.exclude(id=customer_id)
    
    if existing_customer.exists():
        customer = existing_customer.first()
        return JsonResponse({
            'valid': False, 
            'message': f'Email already exists for {customer.full_name}',
            'duplicate_customer': {
                'id': customer.id,
                'name': customer.full_name,
                'mobile': customer.mobile
            }
        })
    
    return JsonResponse({'valid': True, 'message': 'Email is available'})


@login_required
def validate_mobile(request):
    """AJAX endpoint to validate mobile number format and uniqueness"""
    mobile = request.GET.get('mobile', '').strip()
    customer_id = request.GET.get('customer_id')  # For edit forms
    
    if not mobile:
        return JsonResponse({'valid': False, 'message': 'Mobile number is required'})
    
    # Import here to avoid circular imports
    import re
    from .utils import normalize_phone
    
    # Validate NZ mobile format
    # Allow formats like: 021234567, 0211234567, +64211234567, +6421234567
    nz_mobile_pattern = r'^\+?64[2-9]\d{7,8}$|^0[2-9]\d{7,8}$'
    if not re.match(nz_mobile_pattern, mobile):
        return JsonResponse({
            'valid': False, 
            'message': 'Please enter a valid New Zealand mobile number (e.g., +64211234567 or 0211234567)'
        })
    
    # Normalize for duplicate checking
    normalized_mobile = normalize_phone(mobile)
    
    # Check for similar mobile numbers
    existing_customers = Customer.objects.all()
    if customer_id:
        existing_customers = existing_customers.exclude(id=customer_id)
    
    for customer in existing_customers:
        if normalize_phone(customer.mobile) == normalized_mobile:
            return JsonResponse({
                'valid': False,
                'message': f'Similar mobile number already exists for {customer.full_name}',
                'duplicate_customer': {
                    'id': customer.id,
                    'name': customer.full_name,
                    'email': customer.email,
                    'mobile': customer.mobile
                }
            })
    
    return JsonResponse({'valid': True, 'message': 'Mobile number is valid'})


@login_required
def validate_postcode(request):
    """AJAX endpoint to validate NZ postcode format"""
    postcode = request.GET.get('postcode', '').strip()
    
    if not postcode:
        return JsonResponse({'valid': False, 'message': 'Postcode is required'})
    
    # Validate 4-digit NZ postcode
    if not postcode.isdigit() or len(postcode) != 4:
        return JsonResponse({
            'valid': False, 
            'message': 'Please enter a valid 4-digit New Zealand postcode'
        })
    
    return JsonResponse({'valid': True, 'message': 'Postcode is valid'})
