from django.core.mail import send_mail, EmailMultiAlternatives
from django.template import Template, Context
from django.conf import settings
from django.utils import timezone
from django.contrib.auth.models import User
from datetime import timedelta
import re
import logging
from typing import Dict, List, Optional, Any

from customers.models import Customer
from .models import (
    EmailTemplate, EmailSequence, EmailSequenceStep, 
    EmailDelivery, AnalyticsEvent
)

logger = logging.getLogger(__name__)


class EmailTemplateProcessor:
    """Process email templates with variable substitution"""
    
    # Available template variables
    AVAILABLE_VARIABLES = [
        'customer_name',
        'customer_first_name', 
        'customer_last_name',
        'customer_email',
        'customer_mobile',
        'customer_city',
        'current_date',
        'current_time',
        'company_name',
        'company_email',
        'company_phone',
    ]
    
    @staticmethod
    def get_customer_context(customer: Customer) -> Dict[str, Any]:
        """Get template context for a customer"""
        return {
            'customer_name': f"{customer.first_name} {customer.last_name}".strip(),
            'customer_first_name': customer.first_name,
            'customer_last_name': customer.last_name,
            'customer_email': customer.email,
            'customer_mobile': customer.mobile or '',
            'customer_city': customer.city or '',
            'current_date': timezone.now().strftime('%B %d, %Y'),
            'current_time': timezone.now().strftime('%I:%M %p'),
            'company_name': getattr(settings, 'COMPANY_NAME', 'Your Company'),
            'company_email': getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
            'company_phone': getattr(settings, 'COMPANY_PHONE', ''),
        }
    
    @staticmethod
    def process_template(template_content: str, context: Dict[str, Any]) -> str:
        """Process template content with context variables"""
        # Use Django template engine for processing
        template = Template(template_content)
        django_context = Context(context)
        
        try:
            processed_content = template.render(django_context)
            return processed_content
        except Exception as e:
            logger.error(f"Error processing template: {e}")
            # Fallback to simple string replacement
            return EmailTemplateProcessor._simple_variable_replacement(template_content, context)
    
    @staticmethod
    def _simple_variable_replacement(content: str, context: Dict[str, Any]) -> str:
        """Simple variable replacement fallback"""
        processed_content = content
        
        for key, value in context.items():
            # Replace {variable} format
            processed_content = processed_content.replace(f"{{{key}}}", str(value))
            # Replace {{variable}} format
            processed_content = processed_content.replace(f"{{{{{key}}}}}", str(value))
        
        return processed_content
    
    @staticmethod
    def extract_variables(content: str) -> List[str]:
        """Extract variables from template content"""
        # Find variables in {variable} and {{variable}} format
        pattern = r'\{\{?(\w+)\}?\}'
        matches = re.findall(pattern, content)
        return list(set(matches))
    
    @staticmethod
    def validate_template(template: EmailTemplate) -> Dict[str, Any]:
        """Validate template content and variables"""
        issues = []
        warnings = []
        
        # Check for empty content
        if not template.subject.strip():
            issues.append("Subject cannot be empty")
        
        if not template.content.strip():
            issues.append("Content cannot be empty")
        
        # Extract variables from content
        subject_vars = EmailTemplateProcessor.extract_variables(template.subject)
        content_vars = EmailTemplateProcessor.extract_variables(template.content)
        all_vars = set(subject_vars + content_vars)
        
        # Check for undefined variables
        available_vars = set(EmailTemplateProcessor.AVAILABLE_VARIABLES)
        undefined_vars = all_vars - available_vars
        
        if undefined_vars:
            warnings.append(f"Undefined variables found: {', '.join(undefined_vars)}")
        
        # Update template's available_variables
        template.available_variables = list(all_vars & available_vars)
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'variables_found': list(all_vars),
            'variables_available': template.available_variables
        }


class EmailAutomationEngine:
    """Core email automation engine"""
    
    @staticmethod
    def send_template_email(
        customer: Customer,
        template: EmailTemplate,
        sent_by: User,
        sequence: Optional[EmailSequence] = None,
        sequence_step: Optional[EmailSequenceStep] = None
    ) -> EmailDelivery:
        """Send an email using a template"""
        
        # Get customer context
        context = EmailTemplateProcessor.get_customer_context(customer)
        
        # Process template content
        processed_subject = EmailTemplateProcessor.process_template(template.subject, context)
        processed_content = EmailTemplateProcessor.process_template(template.content, context)
        processed_html = None
        
        if template.html_content:
            processed_html = EmailTemplateProcessor.process_template(template.html_content, context)
        
        # Create email delivery record
        email_delivery = EmailDelivery.objects.create(
            customer=customer,
            template=template,
            sequence=sequence,
            sequence_step=sequence_step,
            subject=processed_subject,
            sent_by=sent_by,
            status='pending'
        )
        
        try:
            # Send email
            if processed_html:
                # Send HTML email
                email = EmailMultiAlternatives(
                    subject=processed_subject,
                    body=processed_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[customer.email]
                )
                email.attach_alternative(processed_html, "text/html")
                email.send()
            else:
                # Send plain text email
                send_mail(
                    subject=processed_subject,
                    message=processed_content,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[customer.email],
                    fail_silently=False
                )
            
            # Update delivery status
            email_delivery.status = 'sent'
            email_delivery.save()
            
            # Track analytics event
            AnalyticsEvent.objects.create(
                customer=customer,
                event_type='email_sent',
                user=sent_by,
                metadata={
                    'template_id': template.pk,
                    'template_name': template.name,
                    'subject': processed_subject,
                    'sequence_id': sequence.pk if sequence else None,
                    'sequence_step_id': sequence_step.pk if sequence_step else None,
                }
            )
            
            logger.info(f"Email sent to {customer.email} using template {template.name}")
            
        except Exception as e:
            # Update delivery status
            email_delivery.status = 'failed'
            email_delivery.save()
            
            logger.error(f"Failed to send email to {customer.email}: {e}")
            raise
        
        return email_delivery
    
    @staticmethod
    def trigger_sequence(
        sequence: EmailSequence,
        customer: Customer,
        triggered_by: User
    ) -> List[EmailDelivery]:
        """Trigger an email sequence for a customer"""
        
        if not sequence.is_active:
            logger.warning(f"Attempted to trigger inactive sequence {sequence.name}")
            return []
        
        deliveries = []
        
        # Get sequence steps
        steps = sequence.steps.all().order_by('step_number')
        
        if not steps.exists():
            logger.warning(f"No steps found for sequence {sequence.name}")
            return []
        
        # Send first step immediately
        first_step = steps.first()
        try:
            delivery = EmailAutomationEngine.send_template_email(
                customer=customer,
                template=first_step.template,
                sent_by=triggered_by,
                sequence=sequence,
                sequence_step=first_step
            )
            deliveries.append(delivery)
        except Exception as e:
            logger.error(f"Failed to send first step of sequence {sequence.name}: {e}")
            return deliveries
        
        # Schedule remaining steps
        for step in steps[1:]:
            try:
                EmailAutomationEngine.schedule_sequence_step(
                    customer=customer,
                    sequence_step=step,
                    triggered_by=triggered_by,
                    base_time=timezone.now()
                )
            except Exception as e:
                logger.error(f"Failed to schedule step {step.step_number} of sequence {sequence.name}: {e}")
        
        # Track analytics event
        AnalyticsEvent.objects.create(
            customer=customer,
            event_type='email_sequence_triggered',
            user=triggered_by,
            metadata={
                'sequence_id': sequence.pk,
                'sequence_name': sequence.name,
                'steps_count': steps.count(),
            }
        )
        
        return deliveries
    
    @staticmethod
    def schedule_sequence_step(
        customer: Customer,
        sequence_step: EmailSequenceStep,
        triggered_by: User,
        base_time: timezone.datetime
    ):
        """Schedule a sequence step for later delivery"""
        
        # Calculate send time
        delay = timedelta(
            days=sequence_step.delay_days,
            hours=sequence_step.delay_hours
        )
        send_time = base_time + delay
        
        # In a production environment, you would schedule this using:
        # - Celery for task queuing
        # - Django-RQ for Redis-based queuing  
        # - Database-based scheduling
        # - External services like AWS SQS
        
        # For now, we'll create a delivery record with pending status
        # and implement a management command to process scheduled emails
        
        EmailDelivery.objects.create(
            customer=customer,
            template=sequence_step.template,
            sequence=sequence_step.sequence,
            sequence_step=sequence_step,
            subject=sequence_step.template.subject,  # Will be processed when sent
            sent_by=triggered_by,
            status='scheduled',
            # You would add a scheduled_for field to EmailDelivery model
        )
        
        logger.info(f"Scheduled step {sequence_step.step_number} for {customer.email} at {send_time}")
    
    @staticmethod
    def process_scheduled_emails():
        """Process scheduled emails (to be called by management command)"""
        
        # Get pending scheduled emails
        scheduled_emails = EmailDelivery.objects.filter(
            status='scheduled'
            # scheduled_for__lte=timezone.now()  # Add this field to model
        )
        
        processed_count = 0
        error_count = 0
        
        for delivery in scheduled_emails:
            try:
                # Re-send the email if template exists
                if delivery.template:
                    EmailAutomationEngine.send_template_email(
                        customer=delivery.customer,
                        template=delivery.template,
                        sent_by=delivery.sent_by,
                        sequence=delivery.sequence,
                        sequence_step=delivery.sequence_step
                    )
                    
                    # Delete the scheduled record
                    delivery.delete()
                    processed_count += 1
                else:
                    delivery.status = 'failed'
                    delivery.save()
                    error_count += 1
                    logger.error(f"No template found for scheduled email {delivery.pk}")
                
            except Exception as e:
                delivery.status = 'failed'
                delivery.save()
                error_count += 1
                logger.error(f"Failed to process scheduled email {delivery.pk}: {e}")
        
        logger.info(f"Processed {processed_count} scheduled emails, {error_count} errors")
        return processed_count, error_count


class EmailEngagementTracker:
    """Track email engagement (opens, clicks)"""
    
    @staticmethod
    def track_email_open(delivery_id: int):
        """Track email open"""
        try:
            delivery = EmailDelivery.objects.get(id=delivery_id)
            
            if not delivery.opened_at:
                delivery.opened_at = timezone.now()
                delivery.status = 'opened'
            
            delivery.open_count += 1
            delivery.save()
            
            # Track analytics event
            AnalyticsEvent.objects.create(
                customer=delivery.customer,
                event_type='email_opened',
                user=delivery.sent_by,
                metadata={
                    'delivery_id': delivery.pk,
                    'template_name': delivery.template.name if delivery.template else '',
                    'subject': delivery.subject,
                }
            )
            
        except EmailDelivery.DoesNotExist:
            logger.error(f"Email delivery {delivery_id} not found for open tracking")
    
    @staticmethod
    def track_email_click(delivery_id: int, url: str):
        """Track email click"""
        try:
            delivery = EmailDelivery.objects.get(id=delivery_id)
            
            if not delivery.clicked_at:
                delivery.clicked_at = timezone.now()
                delivery.status = 'clicked'
            
            delivery.click_count += 1
            delivery.save()
            
            # Track analytics event
            AnalyticsEvent.objects.create(
                customer=delivery.customer,
                event_type='email_clicked',
                user=delivery.sent_by,
                metadata={
                    'delivery_id': delivery.pk,
                    'template_name': delivery.template.name if delivery.template else '',
                    'subject': delivery.subject,
                    'clicked_url': url,
                }
            )
            
        except EmailDelivery.DoesNotExist:
            logger.error(f"Email delivery {delivery_id} not found for click tracking")
    
    @staticmethod
    def get_engagement_stats(template_id: Optional[int] = None, 
                           sequence_id: Optional[int] = None) -> Dict[str, Any]:
        """Get engagement statistics"""
        
        queryset = EmailDelivery.objects.all()
        
        if template_id:
            queryset = queryset.filter(template_id=template_id)
        
        if sequence_id:
            queryset = queryset.filter(sequence_id=sequence_id)
        
        total_sent = queryset.count()
        total_delivered = queryset.filter(status__in=['delivered', 'opened', 'clicked']).count()
        total_opened = queryset.filter(opened_at__isnull=False).count()
        total_clicked = queryset.filter(clicked_at__isnull=False).count()
        
        return {
            'total_sent': total_sent,
            'total_delivered': total_delivered,
            'total_opened': total_opened,
            'total_clicked': total_clicked,
            'delivery_rate': (total_delivered / total_sent * 100) if total_sent > 0 else 0,
            'open_rate': (total_opened / total_delivered * 100) if total_delivered > 0 else 0,
            'click_rate': (total_clicked / total_opened * 100) if total_opened > 0 else 0,
            'click_through_rate': (total_clicked / total_delivered * 100) if total_delivered > 0 else 0,
        }


# Utility functions for triggering sequences based on events

def trigger_sequence_on_customer_created(customer: Customer, created_by: User):
    """Trigger sequences when a new customer is created"""
    sequences = EmailSequence.objects.filter(
        trigger_type='customer_created',
        is_active=True
    )
    
    for sequence in sequences:
        try:
            EmailAutomationEngine.trigger_sequence(sequence, customer, created_by)
        except Exception as e:
            logger.error(f"Failed to trigger sequence {sequence.name} for new customer {customer.pk}: {e}")


def trigger_sequence_on_note_added(customer: Customer, added_by: User):
    """Trigger sequences when a note is added"""
    sequences = EmailSequence.objects.filter(
        trigger_type='note_added',
        is_active=True
    )
    
    for sequence in sequences:
        try:
            EmailAutomationEngine.trigger_sequence(sequence, customer, added_by)
        except Exception as e:
            logger.error(f"Failed to trigger sequence {sequence.name} for note added to customer {customer.pk}: {e}")


def trigger_sequence_on_file_uploaded(customer: Customer, uploaded_by: User):
    """Trigger sequences when a file is uploaded"""
    sequences = EmailSequence.objects.filter(
        trigger_type='file_uploaded',
        is_active=True
    )
    
    for sequence in sequences:
        try:
            EmailAutomationEngine.trigger_sequence(sequence, customer, uploaded_by)
        except Exception as e:
            logger.error(f"Failed to trigger sequence {sequence.name} for file uploaded to customer {customer.pk}: {e}")