from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta
import json
import logging

from customers.models import Customer
from .models import (
    QuoteRequest, Job, JobUpdate, EmailAutoResponse, 
    AnalyticsEvent, EmailDelivery
)
from .quote_job_forms import (
    QuoteRequestForm, QuoteResponseForm, JobForm, JobUpdateForm,
    JobStatusUpdateForm, QuoteFilterForm, JobFilterForm,
    BulkActionForm, EmailProcessingForm, CustomerCommunicationForm
)
from .quote_job_automation import QuoteJobAutomationEngine

logger = logging.getLogger(__name__)


@login_required
def quote_job_dashboard(request):
    """Main dashboard for quote and job management"""
    
    # Get quick stats
    stats = {
        'quotes_pending': QuoteRequest.objects.filter(status__in=['received', 'reviewing']).count(),
        'quotes_overdue': QuoteRequest.objects.filter(
            status='quoted',
            quote_sent_at__lt=timezone.now() - timedelta(days=7)
        ).count(),
        'jobs_active': Job.objects.filter(status__in=['pending', 'in_progress']).count(),
        'jobs_overdue': Job.objects.filter(
            status__in=['pending', 'in_progress'],
            due_date__lt=timezone.now()
        ).count(),
    }
    
    # Recent quotes
    recent_quotes = QuoteRequest.objects.select_related('customer', 'assigned_to').order_by('-created_at')[:5]
    
    # Recent jobs
    recent_jobs = Job.objects.select_related('customer', 'assigned_to').order_by('-created_at')[:5]
    
    # Upcoming deadlines
    upcoming_deadlines = Job.objects.filter(
        status__in=['pending', 'in_progress'],
        due_date__gte=timezone.now(),
        due_date__lte=timezone.now() + timedelta(days=7)
    ).select_related('customer', 'assigned_to').order_by('due_date')[:5]
    
    # Charts data for the last 30 days
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    quotes_chart_data = []
    jobs_chart_data = []
    
    for i in range(30):
        date = thirty_days_ago + timedelta(days=i)
        quotes_count = QuoteRequest.objects.filter(
            created_at__date=date.date()
        ).count()
        jobs_count = Job.objects.filter(
            created_at__date=date.date()
        ).count()
        
        quotes_chart_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': quotes_count
        })
        jobs_chart_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': jobs_count
        })
    
    context = {
        'stats': stats,
        'recent_quotes': recent_quotes,
        'recent_jobs': recent_jobs,
        'upcoming_deadlines': upcoming_deadlines,
        'quotes_chart_data': json.dumps(quotes_chart_data),
        'jobs_chart_data': json.dumps(jobs_chart_data),
    }
    
    return render(request, 'analytics/quote_job_dashboard.html', context)


@login_required
def quote_list(request):
    """List all quote requests with filtering"""
    
    quotes = QuoteRequest.objects.select_related('customer', 'assigned_to')
    filter_form = QuoteFilterForm(request.GET)
    
    if filter_form.is_valid():
        if filter_form.cleaned_data['status']:
            quotes = quotes.filter(status=filter_form.cleaned_data['status'])
        
        if filter_form.cleaned_data['priority']:
            quotes = quotes.filter(priority=filter_form.cleaned_data['priority'])
        
        if filter_form.cleaned_data['service_type']:
            quotes = quotes.filter(service_type=filter_form.cleaned_data['service_type'])
        
        if filter_form.cleaned_data['assigned_to']:
            quotes = quotes.filter(assigned_to=filter_form.cleaned_data['assigned_to'])
        
        if filter_form.cleaned_data['date_from']:
            quotes = quotes.filter(created_at__date__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data['date_to']:
            quotes = quotes.filter(created_at__date__lte=filter_form.cleaned_data['date_to'])
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        quotes = quotes.filter(
            Q(title__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__email__icontains=search_query) |
            Q(reference_number__icontains=search_query)
        )
    
    quotes = quotes.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(quotes, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'search_query': search_query,
        'total_count': quotes.count(),
    }
    
    return render(request, 'analytics/quote_list.html', context)


@login_required
def quote_detail(request, quote_id):
    """View quote request details"""
    
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    # Get related events
    events = AnalyticsEvent.objects.filter(
        customer=quote.customer,
        metadata__quote_reference=quote.reference_number
    ).order_by('-timestamp')
    
    # Get email deliveries for this quote
    emails = EmailDelivery.objects.filter(
        customer=quote.customer
    ).order_by('-sent_at')
    
    # Get approved quotes count for this customer
    approved_quotes_count = QuoteRequest.objects.filter(
        customer=quote.customer,
        status='approved'
    ).count()
    
    # Get all customers for the duplicate modal
    all_customers = Customer.objects.all().order_by('first_name', 'last_name')
    
    context = {
        'quote': quote,
        'events': events,
        'emails': emails,
        'approved_quotes_count': approved_quotes_count,
        'all_customers': all_customers,
    }
    
    return render(request, 'analytics/quote_detail.html', context)


@login_required
def quote_create(request):
    """Create new quote request"""
    
    if request.method == 'POST':
        form = QuoteRequestForm(request.POST)
        if form.is_valid():
            quote = form.save()
            
            # Create analytics event
            AnalyticsEvent.objects.create(
                customer=quote.customer,
                event_type='quote_request_created',
                metadata={
                    'quote_reference': quote.reference_number,
                    'created_by': request.user.username,
                    'manual_creation': True
                }
            )
            
            messages.success(request, f'Quote request {quote.reference_number} created successfully.')
            return redirect('analytics:quote_detail', quote_id=quote.pk)
    else:
        form = QuoteRequestForm()
    
    context = {
        'form': form,
        'title': 'Create Quote Request',
    }
    
    return render(request, 'analytics/quote_form.html', context)


@login_required
def quote_edit(request, quote_id):
    """Edit quote request"""
    
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    if request.method == 'POST':
        form = QuoteRequestForm(request.POST, instance=quote)
        if form.is_valid():
            quote = form.save()
            
            # Create analytics event
            AnalyticsEvent.objects.create(
                customer=quote.customer,
                event_type='quote_request_updated',
                metadata={
                    'quote_reference': quote.reference_number,
                    'updated_by': request.user.username,
                }
            )
            
            messages.success(request, f'Quote request {quote.reference_number} updated successfully.')
            return redirect('analytics:quote_detail', quote_id=quote.pk)
    else:
        form = QuoteRequestForm(instance=quote)
    
    context = {
        'form': form,
        'quote': quote,
        'title': f'Edit Quote Request {quote.reference_number}',
    }
    
    return render(request, 'analytics/quote_form.html', context)


@login_required
def quote_send(request, quote_id):
    """Send quote to customer"""
    
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    if request.method == 'POST':
        # Update quote status to sent
        quote.status = 'sent'
        quote.save()
        
        # Send quote email
        QuoteJobAutomationEngine.send_auto_response(quote, 'quote_sent')
        
        # Create analytics event
        AnalyticsEvent.objects.create(
            customer=quote.customer,
            event_type='quote_sent',
            metadata={
                'quote_reference': quote.reference_number,
                'sent_by': request.user.username,
            }
        )
        
        messages.success(request, f'Quote {quote.reference_number} sent to {quote.customer.email}.')
        return redirect('analytics:quote_detail', quote_id=quote.pk)
    
    context = {
        'quote': quote,
        'title': f'Send Quote {quote.reference_number}',
    }
    
    return render(request, 'analytics/quote_send_confirm.html', context)


@login_required
def quote_pdf(request, quote_id):
    """Generate and return a PDF version of the quote."""
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    try:
        from django.http import HttpResponse
        from reportlab.pdfgen import canvas
        from reportlab.lib.pagesizes import letter
        import io
        
        # Create a BytesIO buffer for the PDF
        buffer = io.BytesIO()
        
        # Create the PDF object
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        
        # Write the quote details to the PDF
        y_position = height - 100
        
        # Header
        p.setFont("Helvetica-Bold", 18)
        p.drawString(50, y_position, f"Quote #{quote.pk}")
        y_position -= 30
        
        # Customer details
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_position, "Customer:")
        y_position -= 20
        p.setFont("Helvetica", 10)
        p.drawString(70, y_position, f"Name: {quote.customer.first_name} {quote.customer.last_name}")
        y_position -= 15
        p.drawString(70, y_position, f"Email: {quote.customer.email}")
        y_position -= 15
        if quote.customer.mobile:
            p.drawString(70, y_position, f"Mobile: {quote.customer.mobile}")
            y_position -= 15
        
        y_position -= 20
        
        # Quote details
        p.setFont("Helvetica-Bold", 12)
        p.drawString(50, y_position, "Quote Details:")
        y_position -= 20
        p.setFont("Helvetica", 10)
        p.drawString(70, y_position, f"Description: {quote.description}")
        y_position -= 15
        p.drawString(70, y_position, f"Estimated Cost: ${quote.estimated_cost}")
        y_position -= 15
        p.drawString(70, y_position, f"Status: {quote.status.title()}")
        y_position -= 15
        p.drawString(70, y_position, f"Created: {quote.created_at.strftime('%B %d, %Y')}")
        
        if quote.quote_notes:
            y_position -= 20
            p.setFont("Helvetica-Bold", 12)
            p.drawString(50, y_position, "Notes:")
            y_position -= 20
            p.setFont("Helvetica", 10)
            # Handle multi-line notes
            for line in quote.quote_notes.split('\n'):
                p.drawString(70, y_position, line)
                y_position -= 15
        
        # Save the PDF
        p.showPage()
        p.save()
        
        # Get the value of the BytesIO buffer and return as response
        pdf = buffer.getvalue()
        buffer.close()
        
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="quote_{quote.pk}.pdf"'
        response.write(pdf)
        
        return response
        
    except ImportError:
        # If reportlab is not installed, return a simple text response
        from django.http import HttpResponse
        response = HttpResponse(content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="quote_{quote.pk}.txt"'
        
        content = f"""
QUOTE #{quote.pk}

Customer: {quote.customer.first_name} {quote.customer.last_name}
Email: {quote.customer.email}
Mobile: {quote.customer.mobile or 'N/A'}

Description: {quote.description}
Estimated Cost: ${quote.estimated_cost}
Status: {quote.status.title()}
Created: {quote.created_at.strftime('%B %d, %Y')}

Notes:
{quote.quote_notes or 'No additional notes'}
"""
        response.write(content)
        return response


@login_required
def job_create_from_quote(request, quote_id):
    """Create a new job from an accepted quote."""
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    if quote.status != 'accepted':
        messages.error(request, 'Only accepted quotes can be converted to jobs.')
        return redirect('analytics:quote_detail', quote_id=quote.pk)
    
    if request.method == 'POST':
        try:
            # Create a new job from the quote
            job = Job.objects.create(
                customer=quote.customer,
                quote_request=quote,
                title=quote.title,
                description=quote.description,
                service_type=quote.service_type,
                priority=quote.priority,
                assigned_to=request.user,
                created_by=request.user,
                status='pending',
                estimated_hours=8.0,  # Default value
                quoted_amount=quote.final_quote_amount or quote.estimated_cost,
                notes=f"Created from Quote #{quote.pk}"
            )
            
            # Log the action
            AnalyticsEvent.objects.create(
                event_type='job_created_from_quote',
                customer=quote.customer,
                user=request.user,
                metadata={
                    'quote_id': quote.pk,
                    'job_id': job.pk,
                    'quote_amount': str(quote.estimated_cost)
                }
            )
            
            messages.success(request, f'Job #{job.pk} has been created from Quote #{quote.pk}.')
            return redirect('analytics:job_detail', job_id=job.pk)
            
        except Exception as e:
            messages.error(request, f'Error creating job: {str(e)}')
            return redirect('analytics:quote_detail', quote_id=quote.pk)
    
    return render(request, 'analytics/job_create_from_quote.html', {
        'quote': quote,
        'title': f'Create Job from Quote #{quote.pk}',
    })


@login_required
def quote_generate_invoice(request, quote_id):
    """Generate an invoice from an accepted quote."""
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    if quote.status != 'accepted':
        messages.error(request, 'Only accepted quotes can be used to generate invoices.')
        return redirect('analytics:quote_detail', quote_id=quote.pk)
    
    if request.method == 'POST':
        try:
            # Create invoice data structure
            invoice_data = {
                'quote_id': quote.pk,
                'customer_name': f"{quote.customer.first_name} {quote.customer.last_name}",
                'customer_email': quote.customer.email,
                'description': quote.description,
                'amount': str(quote.estimated_cost),
                'date_generated': timezone.now().isoformat(),
                'status': 'pending'
            }
            
            # Log the invoice generation
            AnalyticsEvent.objects.create(
                event_type='invoice_generated',
                customer=quote.customer,
                user=request.user,
                metadata=invoice_data
            )
            
            messages.success(request, f'Invoice has been generated for Quote #{quote.pk}.')
            return render(request, 'analytics/invoice_generated.html', {
                'quote': quote,
                'invoice_data': invoice_data,
                'title': f'Invoice Generated - Quote #{quote.pk}',
            })
            
        except Exception as e:
            messages.error(request, f'Error generating invoice: {str(e)}')
            return redirect('analytics:quote_detail', quote_id=quote.pk)
    
    return render(request, 'analytics/quote_generate_invoice.html', {
        'quote': quote,
        'title': f'Generate Invoice - Quote #{quote.pk}',
    })


@login_required
def quote_respond(request, quote_id):
    """Respond to a quote request"""
    
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    if request.method == 'POST':
        form = QuoteResponseForm(request.POST, instance=quote)
        if form.is_valid():
            quote = form.save()
            
            # Send quote response email
            QuoteJobAutomationEngine.send_auto_response(quote, 'quote_response')
            
            # Create analytics event
            AnalyticsEvent.objects.create(
                customer=quote.customer,
                event_type='quote_sent',
                metadata={
                    'quote_reference': quote.reference_number,
                    'amount': float(quote.final_quote_amount),
                    'sent_by': request.user.username
                }
            )
            
            messages.success(request, f'Quote response sent for {quote.reference_number}.')
            return redirect('analytics:quote_detail', quote_id=quote.pk)
    else:
        form = QuoteResponseForm(instance=quote)
    
    context = {
        'form': form,
        'quote': quote,
        'title': f'Respond to Quote {quote.reference_number}',
    }
    
    return render(request, 'analytics/quote_response_form.html', context)


@login_required
def quote_convert_to_job(request, quote_id):
    """Convert quote to job"""
    
    quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    if quote.status != 'accepted':
        messages.error(request, 'Only accepted quotes can be converted to jobs.')
        return redirect('analytics:quote_detail', quote_id=quote.pk)
    
    job = QuoteJobAutomationEngine.convert_quote_to_job(quote, request.user)
    
    if job:
        messages.success(request, f'Quote {quote.reference_number} converted to job {job.job_number}.')
        return redirect('analytics:job_detail', job_id=job.pk)
    else:
        messages.error(request, 'Failed to convert quote to job.')
        return redirect('analytics:quote_detail', quote_id=quote.pk)


@login_required
@require_http_methods(["POST"])
def quote_duplicate(request, quote_id):
    """Duplicate an existing quote"""
    
    original_quote = get_object_or_404(QuoteRequest, pk=quote_id)
    
    # Get the new title and customer from the form
    new_title = request.POST.get('title', f"{original_quote.title} (Copy)")
    customer_id = request.POST.get('customer', original_quote.customer.pk)
    copy_attachments = request.POST.get('copy_attachments') == 'on'
    
    try:
        # Get the selected customer
        customer = get_object_or_404(Customer, pk=customer_id)
        
        # Create a new quote with copied data
        new_quote = QuoteRequest.objects.create(
            customer=customer,
            title=new_title,
            description=original_quote.description,
            service_type=original_quote.service_type,
            estimated_cost=original_quote.estimated_cost,
            final_quote_amount=original_quote.final_quote_amount,
            quote_notes=original_quote.quote_notes,
            priority=original_quote.priority,
            status='received',  # Reset to received status for new quote
            created_by=request.user,
            assigned_to=request.user
        )
        
        # Copy attachments if requested
        if copy_attachments and hasattr(original_quote, 'attachments'):
            # Note: This would need to be implemented based on your attachment model
            pass
        
        # Log the duplication
        AnalyticsEvent.objects.create(
            event_type='quote_duplicated',
            customer=customer,
            user=request.user,
            metadata={
                'original_quote_id': original_quote.pk,
                'new_quote_id': new_quote.pk,
                'title': new_title
            }
        )
        
        messages.success(request, f'Quote duplicated successfully as "{new_title}".')
        return redirect('analytics:quote_detail', quote_id=new_quote.pk)
        
    except Exception as e:
        logger.error(f"Error duplicating quote {quote_id}: {str(e)}")
        messages.error(request, 'Failed to duplicate quote. Please try again.')
        return redirect('analytics:quote_detail', quote_id=quote_id)


@login_required
def job_list(request):
    """List all jobs with filtering"""
    
    jobs = Job.objects.select_related('customer', 'assigned_to', 'quote_request')
    filter_form = JobFilterForm(request.GET)
    
    if filter_form.is_valid():
        if filter_form.cleaned_data['status']:
            jobs = jobs.filter(status=filter_form.cleaned_data['status'])
        
        if filter_form.cleaned_data['priority']:
            jobs = jobs.filter(priority=filter_form.cleaned_data['priority'])
        
        if filter_form.cleaned_data['service_type']:
            jobs = jobs.filter(service_type=filter_form.cleaned_data['service_type'])
        
        if filter_form.cleaned_data['assigned_to']:
            jobs = jobs.filter(assigned_to=filter_form.cleaned_data['assigned_to'])
        
        if filter_form.cleaned_data['overdue_only']:
            jobs = jobs.filter(
                status__in=['pending', 'in_progress'],
                due_date__lt=timezone.now()
            )
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        jobs = jobs.filter(
            Q(title__icontains=search_query) |
            Q(customer__first_name__icontains=search_query) |
            Q(customer__last_name__icontains=search_query) |
            Q(customer__email__icontains=search_query) |
            Q(job_number__icontains=search_query)
        )
    
    jobs = jobs.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(jobs, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'filter_form': filter_form,
        'search_query': search_query,
        'total_count': jobs.count(),
    }
    
    return render(request, 'analytics/job_list.html', context)


@login_required
def job_detail(request, job_id):
    """View job details"""
    
    job = get_object_or_404(Job, pk=job_id)
    
    # Get job updates
    updates = JobUpdate.objects.filter(job=job).order_by('-created_at')
    
    # Get related events
    events = AnalyticsEvent.objects.filter(
        customer=job.customer,
        metadata__job_number=job.job_number
    ).order_by('-created_at')
    
    # Get email deliveries for this job
    emails = EmailDelivery.objects.filter(
        customer=job.customer,
        metadata__job_number=job.job_number
    ).order_by('-sent_at')
    
    context = {
        'job': job,
        'updates': updates,
        'events': events,
        'emails': emails,
    }
    
    return render(request, 'analytics/job_detail.html', context)


@login_required
def job_create(request):
    """Create new job"""
    
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.created_by = request.user
            job.save()
            
            # Create analytics event
            AnalyticsEvent.objects.create(
                customer=job.customer,
                event_type='job_created',
                metadata={
                    'job_number': job.job_number,
                    'created_by': request.user.username,
                    'manual_creation': True
                }
            )
            
            messages.success(request, f'Job {job.job_number} created successfully.')
            return redirect('analytics:job_detail', job_id=job.pk)
    else:
        form = JobForm()
    
    context = {
        'form': form,
        'title': 'Create Job',
    }
    
    return render(request, 'analytics/job_form.html', context)


@login_required
def job_update_status(request, job_id):
    """Update job status"""
    
    job = get_object_or_404(Job, pk=job_id)
    
    if request.method == 'POST':
        form = JobStatusUpdateForm(request.POST)
        if form.is_valid():
            old_status = job.status
            new_status = form.cleaned_data['status']
            notes = form.cleaned_data['notes']
            
            job.status = new_status
            if new_status == 'completed':
                job.completed_date = timezone.now()
            job.save()
            
            # Create job update
            JobUpdate.objects.create(
                job=job,
                update_type='status_change',
                title=f'Status changed from {old_status} to {new_status}',
                description=notes or f'Job status updated by {request.user.get_full_name() or request.user.username}',
                created_by=request.user
            )
            
            # Send notification if completed
            if new_status == 'completed':
                QuoteJobAutomationEngine.complete_job(job, notes)
            
            messages.success(request, f'Job status updated to {new_status}.')
            return redirect('analytics:job_detail', job_id=job.pk)
    else:
        form = JobStatusUpdateForm(initial={'status': job.status})
    
    context = {
        'form': form,
        'job': job,
        'title': f'Update Status - {job.job_number}',
    }
    
    return render(request, 'analytics/job_status_form.html', context)


@login_required
def job_add_update(request, job_id):
    """Add update to job"""
    
    job = get_object_or_404(Job, pk=job_id)
    
    if request.method == 'POST':
        form = JobUpdateForm(request.POST)
        if form.is_valid():
            update = form.save(commit=False)
            update.job = job
            update.created_by = request.user
            update.save()
            
            # Send progress update email if requested
            if update.customer_notified:
                QuoteJobAutomationEngine.send_job_progress_update(
                    job=job,
                    update_text=update.description,
                    hours_worked=update.hours_worked,
                    percentage_complete=update.percentage_complete
                )
            
            messages.success(request, 'Job update added successfully.')
            return redirect('analytics:job_detail', job_id=job.pk)
    else:
        form = JobUpdateForm()
    
    context = {
        'form': form,
        'job': job,
        'title': f'Add Update - {job.job_number}',
    }
    
    return render(request, 'analytics/job_update_form.html', context)


@login_required
def process_email(request):
    """Manually process emails as quote requests"""
    
    if request.method == 'POST':
        form = EmailProcessingForm(request.POST)
        if form.is_valid():
            result = QuoteJobAutomationEngine.process_incoming_email(
                sender_email=form.cleaned_data['sender_email'],
                subject=form.cleaned_data['subject'],
                body=form.cleaned_data['body']
            )
            
            if result:
                messages.success(request, f'Created quote request {result.reference_number}.')
                return redirect('analytics:quote_detail', quote_id=result.pk)
            elif form.cleaned_data['force_create_quote']:
                # Force create quote even with low confidence
                customer, _ = Customer.objects.get_or_create(
                    email=form.cleaned_data['sender_email'],
                    defaults={
                        'first_name': form.cleaned_data['sender_email'].split('@')[0].title(),
                        'last_name': '',
                        'mobile': '',
                        'street_address': '',
                        'suburb': '',
                        'city': '',
                        'postcode': '0000',
                    }
                )
                
                quote = QuoteRequest.objects.create(
                    customer=customer,
                    title=form.cleaned_data['subject'],
                    description=form.cleaned_data['body'],
                    source='email',
                    priority='medium',
                    metadata={'forced_creation': True, 'processed_by': request.user.username}
                )
                
                messages.success(request, f'Manually created quote request {quote.reference_number}.')
                return redirect('analytics:quote_detail', quote_id=quote.pk)
            else:
                messages.warning(request, 'Email not identified as quote request. Use "Force Create" if needed.')
    else:
        form = EmailProcessingForm()
    
    context = {
        'form': form,
        'title': 'Process Email as Quote Request',
    }
    
    return render(request, 'analytics/email_processing_form.html', context)


@login_required
@require_http_methods(["GET"])
def quote_stats_api(request):
    """API endpoint for quote statistics"""
    
    # Get date range from query params
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    stats = {
        'total_quotes': QuoteRequest.objects.filter(created_at__gte=start_date).count(),
        'pending_quotes': QuoteRequest.objects.filter(status__in=['received', 'reviewing']).count(),
        'quoted_amount': float(QuoteRequest.objects.filter(
            status='quoted',
            created_at__gte=start_date
        ).aggregate(total=Sum('final_quote_amount'))['total'] or 0),
        'accepted_quotes': QuoteRequest.objects.filter(
            status='accepted',
            created_at__gte=start_date
        ).count(),
        'conversion_rate': 0,
    }
    
    if stats['total_quotes'] > 0:
        stats['conversion_rate'] = round((stats['accepted_quotes'] / stats['total_quotes']) * 100, 1)
    
    return JsonResponse(stats)


@login_required
@require_http_methods(["GET"])
def job_stats_api(request):
    """API endpoint for job statistics"""
    
    # Get date range from query params
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)
    
    stats = {
        'total_jobs': Job.objects.filter(created_at__gte=start_date).count(),
        'active_jobs': Job.objects.filter(status__in=['pending', 'in_progress']).count(),
        'completed_jobs': Job.objects.filter(
            status='completed',
            completed_date__gte=start_date
        ).count(),
        'overdue_jobs': Job.objects.filter(
            status__in=['pending', 'in_progress'],
            due_date__lt=timezone.now()
        ).count(),
        'total_revenue': float(Job.objects.filter(
            status='completed',
            completed_date__gte=start_date
        ).aggregate(total=Sum('final_amount'))['total'] or 0),
    }
    
    return JsonResponse(stats)


@csrf_exempt
@require_http_methods(["POST"])
def webhook_email_received(request):
    """Webhook endpoint for processing incoming emails"""
    
    try:
        data = json.loads(request.body)
        
        # Extract email data (format depends on email service)
        sender_email = data.get('from', {}).get('email', '')
        subject = data.get('subject', '')
        body = data.get('text', '') or data.get('html', '')
        
        if sender_email and subject:
            result = QuoteJobAutomationEngine.process_incoming_email(
                sender_email=sender_email,
                subject=subject,
                body=body
            )
            
            if result:
                return JsonResponse({
                    'success': True,
                    'quote_created': True,
                    'reference_number': result.reference_number
                })
            else:
                return JsonResponse({
                    'success': True,
                    'quote_created': False,
                    'message': 'Email processed but not identified as quote request'
                })
        else:
            return JsonResponse({
                'success': False,
                'error': 'Invalid email data'
            }, status=400)
    
    except Exception as e:
        logger.error(f"Error processing email webhook: {e}")
        return JsonResponse({
            'success': False,
            'error': 'Internal server error'
        }, status=500)