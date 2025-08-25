from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView, CreateView, UpdateView
from django.http import JsonResponse
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse_lazy
from datetime import timedelta
import json

from customers.models import Customer
from .models import (
    AnalyticsEvent, CustomerMetrics, DashboardMetric, 
    Report, EmailTemplate, EmailSequence, EmailDelivery
)
from .utils import AnalyticsCalculator
from .email_automation import EmailAutomationEngine, EmailTemplateProcessor


class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    """Main analytics dashboard"""
    template_name = 'analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate fresh metrics
        AnalyticsCalculator.calculate_dashboard_metrics()
        
        # Get dashboard metrics
        metrics = {}
        for metric in DashboardMetric.objects.all():
            metrics[metric.metric_type] = metric.value
        
        context.update({
            'metrics': metrics,
            'page_title': 'Analytics Dashboard',
        })
        
        return context


class AnalyticsAPIView(LoginRequiredMixin, TemplateView):
    """API endpoint for analytics data"""
    
    def get(self, request, *args, **kwargs):
        chart_type = request.GET.get('chart', 'customer_trends')
        days = int(request.GET.get('days', 30))
        
        if chart_type == 'customer_trends':
            data = AnalyticsCalculator.get_customer_trends(days)
        elif chart_type == 'engagement_trends':
            data = AnalyticsCalculator.get_engagement_trends(days)
        elif chart_type == 'geographic_distribution':
            data = list(AnalyticsCalculator.get_geographic_distribution())
        elif chart_type == 'lead_scores':
            data = self._get_lead_score_distribution()
        elif chart_type == 'engagement_scores':
            data = self._get_engagement_score_distribution()
        else:
            data = []
        
        return JsonResponse({'data': data})
    
    def _get_lead_score_distribution(self):
        """Get distribution of lead scores"""
        ranges = [
            (0, 20, 'Low'),
            (20, 40, 'Fair'),
            (40, 60, 'Good'),
            (60, 80, 'High'),
            (80, 100, 'Excellent')
        ]
        
        distribution = []
        for min_score, max_score, label in ranges:
            count = CustomerMetrics.objects.filter(
                lead_score__gte=min_score,
                lead_score__lt=max_score
            ).count()
            distribution.append({
                'label': label,
                'count': count,
                'range': f"{min_score}-{max_score}"
            })
        
        return distribution
    
    def _get_engagement_score_distribution(self):
        """Get distribution of engagement scores"""
        ranges = [
            (0, 20, 'Very Low'),
            (20, 40, 'Low'),
            (40, 60, 'Medium'),
            (60, 80, 'High'),
            (80, 100, 'Very High')
        ]
        
        distribution = []
        for min_score, max_score, label in ranges:
            count = CustomerMetrics.objects.filter(
                engagement_score__gte=min_score,
                engagement_score__lt=max_score
            ).count()
            distribution.append({
                'label': label,
                'count': count,
                'range': f"{min_score}-{max_score}"
            })
        
        return distribution


class CustomerAnalyticsView(LoginRequiredMixin, TemplateView):
    """Individual customer analytics"""
    template_name = 'analytics/customer_analytics.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer_id = kwargs.get('customer_id')
        customer = get_object_or_404(Customer, id=customer_id)
        
        # Calculate or get customer metrics
        metrics = AnalyticsCalculator.calculate_customer_metrics(customer)
        
        # Get recent events
        recent_events = AnalyticsEvent.objects.filter(
            customer=customer
        )[:20]
        
        # Get event timeline data
        timeline_data = self._get_customer_timeline(customer)
        
        context.update({
            'customer': customer,
            'metrics': metrics,
            'recent_events': recent_events,
            'timeline_data': timeline_data,
            'page_title': f'Analytics - {customer.first_name} {customer.last_name}',
        })
        
        return context
    
    def _get_customer_timeline(self, customer, days=90):
        """Get customer activity timeline"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        events = AnalyticsEvent.objects.filter(
            customer=customer,
            timestamp__date__gte=start_date
        ).values('timestamp__date', 'event_type').annotate(
            count=Count('id')
        ).order_by('timestamp__date')
        
        # Group by date
        timeline = {}
        for event in events:
            date_str = event['timestamp__date'].strftime('%Y-%m-%d')
            if date_str not in timeline:
                timeline[date_str] = {}
            timeline[date_str][event['event_type']] = event['count']
        
        return timeline


class ReportsListView(LoginRequiredMixin, ListView):
    """List of saved reports"""
    model = Report
    template_name = 'analytics/reports_list.html'
    context_object_name = 'reports'
    paginate_by = 20
    
    def get_queryset(self):
        return Report.objects.filter(
            Q(created_by=self.request.user) | Q(is_public=True)
        ).order_by('-created_at')


class ReportBuilderView(LoginRequiredMixin, TemplateView):
    """Interactive report builder"""
    template_name = 'analytics/report_builder.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get available fields for reports
        customer_fields = [
            {'name': 'first_name', 'label': 'First Name', 'type': 'text'},
            {'name': 'last_name', 'label': 'Last Name', 'type': 'text'},
            {'name': 'email', 'label': 'Email', 'type': 'email'},
            {'name': 'mobile', 'label': 'Mobile', 'type': 'text'},
            {'name': 'city', 'label': 'City', 'type': 'text'},
            {'name': 'created_date', 'label': 'Created Date', 'type': 'date'},
            {'name': 'engagement_score', 'label': 'Engagement Score', 'type': 'number'},
            {'name': 'lead_score', 'label': 'Lead Score', 'type': 'number'},
        ]
        
        context.update({
            'available_fields': customer_fields,
            'page_title': 'Report Builder',
        })
        
        return context


class EmailTemplatesView(LoginRequiredMixin, ListView):
    """Email templates management"""
    model = EmailTemplate
    template_name = 'analytics/email_templates.html'
    context_object_name = 'templates'
    paginate_by = 20
    
    def get_queryset(self):
        return EmailTemplate.objects.filter(is_active=True).order_by('name')


class EmailSequencesView(LoginRequiredMixin, ListView):
    """Email sequences management"""
    model = EmailSequence
    template_name = 'analytics/email_sequences.html'
    context_object_name = 'sequences'
    paginate_by = 20
    
    def get_queryset(self):
        return EmailSequence.objects.filter(is_active=True).order_by('name')


class EmailTemplateCreateView(LoginRequiredMixin, TemplateView):
    """Create/edit email template"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Get form data
            name = request.POST.get('name')
            subject = request.POST.get('subject')
            content = request.POST.get('content')
            html_content = request.POST.get('html_content', '')
            is_active = request.POST.get('is_active') == 'true'
            available_variables = request.POST.getlist('available_variables')
            
            # Create or update template
            template_id = request.POST.get('template_id')
            if template_id:
                template = get_object_or_404(EmailTemplate, id=template_id)
                template.name = name
                template.subject = subject
                template.content = content
                template.html_content = html_content
                template.is_active = is_active
                template.available_variables = available_variables
            else:
                template = EmailTemplate.objects.create(
                    name=name,
                    subject=subject,
                    content=content,
                    html_content=html_content,
                    is_active=is_active,
                    available_variables=available_variables,
                    created_by=request.user
                )
            
            template.save()
            
            # Validate template
            validation = EmailTemplateProcessor.validate_template(template)
            
            return JsonResponse({
                'success': True,
                'template_id': template.pk,
                'validation': validation,
                'message': 'Template saved successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class EmailSequenceCreateView(LoginRequiredMixin, TemplateView):
    """Create/edit email sequence"""
    
    def post(self, request, *args, **kwargs):
        try:
            # Get form data
            name = request.POST.get('name')
            description = request.POST.get('description', '')
            trigger_type = request.POST.get('trigger_type')
            is_active = request.POST.get('is_active') == 'true'
            steps_data = json.loads(request.POST.get('steps', '[]'))
            
            # Create or update sequence
            sequence_id = request.POST.get('sequence_id')
            if sequence_id:
                sequence = get_object_or_404(EmailSequence, id=sequence_id)
                sequence.name = name
                sequence.description = description
                sequence.trigger_type = trigger_type
                sequence.is_active = is_active
                # Clear existing steps
                sequence.steps.all().delete()
            else:
                sequence = EmailSequence.objects.create(
                    name=name,
                    description=description,
                    trigger_type=trigger_type,
                    is_active=is_active,
                    created_by=request.user
                )
            
            sequence.save()
            
            # Create sequence steps
            from .models import EmailSequenceStep
            for step_data in steps_data:
                template = get_object_or_404(EmailTemplate, id=step_data['template_id'])
                EmailSequenceStep.objects.create(
                    sequence=sequence,
                    template=template,
                    step_number=step_data['step_number'],
                    delay_days=step_data.get('delay_days', 0),
                    delay_hours=step_data.get('delay_hours', 0)
                )
            
            return JsonResponse({
                'success': True,
                'sequence_id': sequence.pk,
                'message': 'Sequence saved successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class EmailTemplateAPIView(LoginRequiredMixin, TemplateView):
    """API for email template operations"""
    
    def get(self, request, *args, **kwargs):
        template_id = kwargs.get('template_id')
        
        if template_id:
            # Get specific template
            template = get_object_or_404(EmailTemplate, id=template_id)
            return JsonResponse({
                'id': template.pk,
                'name': template.name,
                'subject': template.subject,
                'content': template.content,
                'html_content': template.html_content,
                'is_active': template.is_active,
                'available_variables': template.available_variables,
                'created_at': template.created_at.isoformat()
            })
        else:
            # List all templates
            templates = EmailTemplate.objects.filter(is_active=True).values(
                'id', 'name', 'subject', 'created_at'
            )
            return JsonResponse({'templates': list(templates)})
    
    def delete(self, request, *args, **kwargs):
        template_id = kwargs.get('template_id')
        template = get_object_or_404(EmailTemplate, id=template_id)
        
        # Soft delete by marking inactive
        template.is_active = False
        template.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Template deleted successfully!'
        })


class SendTestEmailView(LoginRequiredMixin, TemplateView):
    """Send test email"""
    
    def post(self, request, *args, **kwargs):
        try:
            template_id = request.POST.get('template_id')
            customer_id = request.POST.get('customer_id')
            test_email = request.POST.get('test_email')
            
            template = get_object_or_404(EmailTemplate, id=template_id)
            
            if customer_id:
                customer = get_object_or_404(Customer, id=customer_id)
            else:
                # Create a test customer object for demo
                customer = Customer(
                    first_name='Test',
                    last_name='Customer',
                    email=test_email or request.user.email,
                    mobile='555-0123',
                    city='Demo City'
                )
            
            # Send test email
            delivery = EmailAutomationEngine.send_template_email(
                customer=customer,
                template=template,
                sent_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Test email sent successfully!',
                'delivery_id': delivery.pk
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class TriggerSequenceView(LoginRequiredMixin, TemplateView):
    """Manually trigger email sequence"""
    
    def post(self, request, *args, **kwargs):
        try:
            sequence_id = request.POST.get('sequence_id')
            customer_id = request.POST.get('customer_id')
            
            sequence = get_object_or_404(EmailSequence, id=sequence_id)
            customer = get_object_or_404(Customer, id=customer_id)
            
            # Trigger sequence
            deliveries = EmailAutomationEngine.trigger_sequence(
                sequence=sequence,
                customer=customer,
                triggered_by=request.user
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Sequence triggered successfully! {len(deliveries)} emails queued.',
                'deliveries_count': len(deliveries)
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })


class EmailStatsView(LoginRequiredMixin, TemplateView):
    """Email statistics and analytics"""
    
    def get(self, request, *args, **kwargs):
        stats_type = request.GET.get('type', 'overview')
        template_id = request.GET.get('template_id')
        sequence_id = request.GET.get('sequence_id')
        days = int(request.GET.get('days', 30))
        
        if stats_type == 'template' and template_id:
            from .email_automation import EmailEngagementTracker
            stats = EmailEngagementTracker.get_engagement_stats(template_id=int(template_id))
        elif stats_type == 'sequence' and sequence_id:
            from .email_automation import EmailEngagementTracker
            stats = EmailEngagementTracker.get_engagement_stats(sequence_id=int(sequence_id))
        else:
            # Overview stats
            end_date = timezone.now()
            start_date = end_date - timedelta(days=days)
            
            total_sent = EmailDelivery.objects.filter(
                sent_at__gte=start_date
            ).count()
            
            total_opened = EmailDelivery.objects.filter(
                sent_at__gte=start_date,
                opened_at__isnull=False
            ).count()
            
            total_clicked = EmailDelivery.objects.filter(
                sent_at__gte=start_date,
                clicked_at__isnull=False
            ).count()
            
            stats = {
                'total_sent': total_sent,
                'total_opened': total_opened,
                'total_clicked': total_clicked,
                'open_rate': (total_opened / total_sent * 100) if total_sent > 0 else 0,
                'click_rate': (total_clicked / total_opened * 100) if total_opened > 0 else 0,
            }
        
        return JsonResponse(stats)
