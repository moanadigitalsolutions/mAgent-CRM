from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings
from datetime import timedelta
import re
import logging

from customers.models import Customer
from .models import (
    QuoteRequest, Job, JobUpdate, EmailAutoResponse, 
    AnalyticsEvent, EmailDelivery, Task
)
from .email_automation import EmailAutomationEngine

logger = logging.getLogger(__name__)


class QuoteJobAutomationEngine:
    """Handle automation for quote requests and job management"""
    
    # Keywords that indicate a quote/job request
    QUOTE_KEYWORDS = [
        'quote', 'quotation', 'estimate', 'price', 'cost', 'how much',
        'job', 'project', 'work', 'service', 'help', 'need', 'require',
        'install', 'repair', 'fix', 'build', 'create', 'develop'
    ]
    
    URGENT_KEYWORDS = [
        'urgent', 'asap', 'emergency', 'immediately', 'rush', 'priority'
    ]
    
    @staticmethod
    def detect_quote_request(email_subject, email_body, sender_email):
        """Detect if an email is a quote/job request"""
        
        # Combine subject and body for analysis
        content = f"{email_subject} {email_body}".lower()
        
        # Count quote-related keywords
        quote_score = sum(1 for keyword in QuoteJobAutomationEngine.QUOTE_KEYWORDS 
                         if keyword in content)
        
        # Check for urgent indicators
        is_urgent = any(keyword in content for keyword in QuoteJobAutomationEngine.URGENT_KEYWORDS)
        
        # Additional patterns that suggest quote requests
        quote_patterns = [
            r'how much.*cost',
            r'what.*price',
            r'can you.*quote',
            r'need.*estimate',
            r'looking for.*service',
            r'interested in.*job',
            r'would like.*work',
        ]
        
        pattern_matches = sum(1 for pattern in quote_patterns 
                            if re.search(pattern, content))
        
        # Calculate confidence score
        confidence = min((quote_score + pattern_matches * 2) * 20, 100)
        
        return {
            'is_quote_request': confidence >= 40,
            'confidence': confidence,
            'is_urgent': is_urgent,
            'keywords_found': [kw for kw in QuoteJobAutomationEngine.QUOTE_KEYWORDS if kw in content]
        }
    
    @staticmethod
    def categorize_service_type(email_subject, email_body):
        """Categorize the type of service being requested"""
        
        content = f"{email_subject} {email_body}".lower()
        
        service_keywords = {
            'consultation': ['consult', 'advice', 'discuss', 'meeting', 'talk'],
            'project': ['project', 'build', 'create', 'develop', 'design'],
            'maintenance': ['maintain', 'service', 'check', 'inspect', 'upkeep'],
            'repair': ['repair', 'fix', 'broken', 'problem', 'issue', 'fault'],
            'installation': ['install', 'setup', 'mount', 'connect', 'configure'],
        }
        
        for service_type, keywords in service_keywords.items():
            if any(keyword in content for keyword in keywords):
                return service_type
        
        return 'other'
    
    @staticmethod
    def process_incoming_email(sender_email, subject, body, received_at=None):
        """Process incoming email and create quote request if applicable"""
        
        if received_at is None:
            received_at = timezone.now()
        
        try:
            # Get or create customer
            customer, created = Customer.objects.get_or_create(
                email=sender_email,
                defaults={
                    'first_name': sender_email.split('@')[0].title(),
                    'last_name': '',
                    'mobile': '',
                    'street_address': '',
                    'suburb': '',
                    'city': '',
                    'postcode': '0000',
                }
            )
            
            # Detect if this is a quote request
            detection_result = QuoteJobAutomationEngine.detect_quote_request(subject, body, sender_email)
            
            if detection_result['is_quote_request']:
                # Create quote request
                quote_request = QuoteRequest.objects.create(
                    customer=customer,
                    title=subject[:200],  # Truncate if too long
                    description=body,
                    service_type=QuoteJobAutomationEngine.categorize_service_type(subject, body),
                    priority='urgent' if detection_result['is_urgent'] else 'medium',
                    original_email_subject=subject,
                    original_email_body=body,
                    source='email',
                    metadata={
                        'detection_confidence': detection_result['confidence'],
                        'keywords_found': detection_result['keywords_found'],
                        'auto_detected': True
                    }
                )
                
                # Log analytics event
                AnalyticsEvent.objects.create(
                    customer=customer,
                    event_type='quote_request_received',
                    metadata={
                        'quote_reference': quote_request.reference_number,
                        'confidence': detection_result['confidence'],
                        'source': 'email_automation'
                    }
                )
                
                # Send auto-response
                QuoteJobAutomationEngine.send_auto_response(quote_request, 'quote_request')
                
                # Create task for team
                QuoteJobAutomationEngine.create_quote_task(quote_request)
                
                # Assign to available team member
                QuoteJobAutomationEngine.auto_assign_quote(quote_request)
                
                logger.info(f"Created quote request {quote_request.reference_number} for {customer.email}")
                
                return quote_request
            
            else:
                # Not a quote request, but log the interaction
                AnalyticsEvent.objects.create(
                    customer=customer,
                    event_type='email_received',
                    metadata={
                        'subject': subject,
                        'detection_score': detection_result['confidence'],
                        'auto_processed': True
                    }
                )
                
                logger.info(f"Email from {customer.email} processed but not identified as quote request (confidence: {detection_result['confidence']}%)")
                
                return None
        
        except Exception as e:
            logger.error(f"Error processing email from {sender_email}: {e}")
            return None
    
    @staticmethod
    def send_auto_response(quote_request, trigger_type):
        """Send automated response email"""
        
        try:
            # Get appropriate auto-response template
            auto_response = EmailAutoResponse.objects.filter(
                trigger_type=trigger_type,
                is_active=True
            ).first()
            
            if not auto_response:
                logger.warning(f"No auto-response template found for trigger: {trigger_type}")
                return False
            
            # Check if response should apply to this service type
            if auto_response.service_types and quote_request.service_type not in auto_response.service_types:
                return False
            
            # Generate email content
            subject, body = auto_response.get_email_content(quote_request=quote_request)
            
            # Send email
            try:
                send_mail(
                    subject=subject,
                    message=body,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[quote_request.customer.email],
                    fail_silently=False
                )
                
                # Log email delivery
                EmailDelivery.objects.create(
                    customer=quote_request.customer,
                    subject=subject,
                    status='sent',
                    sent_by=User.objects.filter(is_staff=True).first(),  # System user
                    metadata={
                        'quote_reference': quote_request.reference_number,
                        'trigger_type': trigger_type,
                        'template_name': auto_response.name
                    }
                )
                
                # Update quote request
                quote_request.auto_response_sent = True
                quote_request.save()
                
                logger.info(f"Auto-response sent for quote {quote_request.reference_number}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to send auto-response email: {e}")
                return False
        
        except Exception as e:
            logger.error(f"Error in send_auto_response: {e}")
            return False
    
    @staticmethod
    def create_quote_task(quote_request):
        """Create a task for the team to handle the quote request"""
        
        try:
            # Get default assignee (could be configurable)
            default_assignee = User.objects.filter(is_staff=True).first()
            
            task = Task.objects.create(
                title=f"Prepare quote for {quote_request.customer.full_name}",
                description=f"Quote Request: {quote_request.title}\n\n"
                           f"Customer: {quote_request.customer.full_name} ({quote_request.customer.email})\n"
                           f"Service Type: {quote_request.get_service_type_display()}\n"
                           f"Priority: {quote_request.get_priority_display()}\n\n"
                           f"Request Details:\n{quote_request.description}",
                customer=quote_request.customer,
                status='pending',
                priority=quote_request.priority,
                due_date=timezone.now() + timedelta(
                    hours=24 if quote_request.priority == 'urgent' else 72
                ),
                assigned_to=default_assignee,
                created_by=default_assignee,
                metadata={
                    'quote_reference': quote_request.reference_number,
                    'auto_created': True,
                    'task_type': 'quote_preparation'
                }
            )
            
            logger.info(f"Created task for quote {quote_request.reference_number}")
            return task
        
        except Exception as e:
            logger.error(f"Error creating quote task: {e}")
            return None
    
    @staticmethod
    def auto_assign_quote(quote_request):
        """Automatically assign quote to available team member"""
        
        try:
            # Simple assignment logic - can be made more sophisticated
            # For now, assign to staff member with least active quotes
            
            staff_members = User.objects.filter(is_staff=True, is_active=True)
            
            if not staff_members:
                return None
            
            # Find staff member with least active quotes
            best_assignee = None
            min_quotes = float('inf')
            
            for staff in staff_members:
                active_quotes = QuoteRequest.objects.filter(
                    assigned_to=staff,
                    status__in=['received', 'reviewing']
                ).count()
                
                if active_quotes < min_quotes:
                    min_quotes = active_quotes
                    best_assignee = staff
            
            if best_assignee:
                quote_request.assigned_to = best_assignee
                quote_request.save()
                
                logger.info(f"Assigned quote {quote_request.reference_number} to {best_assignee.username}")
                return best_assignee
        
        except Exception as e:
            logger.error(f"Error auto-assigning quote: {e}")
            return None
    
    @staticmethod
    def send_quote_follow_up(quote_request):
        """Send follow-up email for quotes that haven't been responded to"""
        
        try:
            # Check if enough time has passed since quote was sent
            if not quote_request.quote_sent_at:
                return False
            
            days_since_quote = (timezone.now() - quote_request.quote_sent_at).days
            
            if days_since_quote < 3:  # Wait at least 3 days
                return False
            
            # Send follow-up using auto-response system
            return QuoteJobAutomationEngine.send_auto_response(quote_request, 'follow_up')
        
        except Exception as e:
            logger.error(f"Error sending quote follow-up: {e}")
            return False
    
    @staticmethod
    def convert_quote_to_job(quote_request, user=None):
        """Convert accepted quote to a job"""
        
        try:
            job = Job.objects.create(
                customer=quote_request.customer,
                quote_request=quote_request,
                title=quote_request.title,
                description=quote_request.description,
                service_type=quote_request.service_type,
                priority=quote_request.priority,
                quoted_amount=quote_request.final_quote_amount,
                assigned_to=quote_request.assigned_to,
                created_by=user or quote_request.assigned_to,
                metadata={
                    'converted_from_quote': True,
                    'original_quote_id': quote_request.id
                }
            )
            
            # Update quote status
            quote_request.status = 'accepted'
            quote_request.save()
            
            # Log analytics event
            AnalyticsEvent.objects.create(
                customer=quote_request.customer,
                event_type='quote_accepted',
                metadata={
                    'quote_reference': quote_request.reference_number,
                    'job_number': job.job_number,
                    'amount': float(quote_request.final_quote_amount) if quote_request.final_quote_amount else 0
                }
            )
            
            # Send job started notification
            QuoteJobAutomationEngine.send_auto_response_for_job(job, 'job_started')
            
            logger.info(f"Converted quote {quote_request.reference_number} to job {job.job_number}")
            return job
        
        except Exception as e:
            logger.error(f"Error converting quote to job: {e}")
            return None
    
    @staticmethod
    def send_auto_response_for_job(job, trigger_type):
        """Send automated response for job-related events"""
        
        try:
            auto_response = EmailAutoResponse.objects.filter(
                trigger_type=trigger_type,
                is_active=True
            ).first()
            
            if not auto_response:
                return False
            
            subject, body = auto_response.get_email_content(job=job)
            
            send_mail(
                subject=subject,
                message=body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[job.customer.email],
                fail_silently=False
            )
            
            # Log email delivery
            EmailDelivery.objects.create(
                customer=job.customer,
                subject=subject,
                status='sent',
                sent_by=User.objects.filter(is_staff=True).first(),
                metadata={
                    'job_number': job.job_number,
                    'trigger_type': trigger_type,
                    'template_name': auto_response.name
                }
            )
            
            return True
        
        except Exception as e:
            logger.error(f"Error sending job auto-response: {e}")
            return False
    
    @staticmethod
    def send_job_progress_update(job, update_text, hours_worked=None, percentage_complete=None):
        """Send progress update to customer"""
        
        try:
            # Create job update record
            job_update = JobUpdate.objects.create(
                job=job,
                update_type='progress',
                title=f"Progress Update - {job.title}",
                description=update_text,
                hours_worked=hours_worked,
                percentage_complete=percentage_complete,
                created_by=job.assigned_to or User.objects.filter(is_staff=True).first()
            )
            
            # Send email if customer wants updates
            if job.send_progress_updates:
                auto_response = EmailAutoResponse.objects.filter(
                    trigger_type='job_progress',
                    is_active=True
                ).first()
                
                if auto_response:
                    # Create custom context for progress update
                    context = {
                        'customer': job.customer,
                        'job': job,
                        'update': job_update,
                        'progress_text': update_text,
                        'hours_worked': hours_worked,
                        'percentage_complete': percentage_complete,
                        'company_name': 'mAgent CRM',
                        'date': timezone.now().strftime('%B %d, %Y'),
                    }
                    
                    # Use custom template rendering for progress updates
                    subject = auto_response.render_template(auto_response.subject_template, context)
                    body = auto_response.render_template(auto_response.body_template, context)
                    
                    send_mail(
                        subject=subject,
                        message=body,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[job.customer.email],
                        fail_silently=False
                    )
                    
                    job_update.customer_notified = True
                    job_update.email_sent_at = timezone.now()
                    job_update.save()
            
            return job_update
        
        except Exception as e:
            logger.error(f"Error sending job progress update: {e}")
            return None
    
    @staticmethod
    def complete_job(job, completion_notes=None, final_amount=None):
        """Mark job as completed and send completion notification"""
        
        try:
            # Update job status
            job.status = 'completed'
            job.completed_date = timezone.now()
            
            if final_amount:
                job.final_amount = final_amount
            
            if completion_notes:
                job.notes = f"{job.notes}\n\nCompletion Notes:\n{completion_notes}" if job.notes else completion_notes
            
            job.save()
            
            # Create completion update
            JobUpdate.objects.create(
                job=job,
                update_type='completion',
                title=f"Job Completed - {job.title}",
                description=completion_notes or "Job has been completed successfully.",
                percentage_complete=100,
                created_by=job.assigned_to or User.objects.filter(is_staff=True).first()
            )
            
            # Send completion notification
            if job.send_completion_notification:
                QuoteJobAutomationEngine.send_auto_response_for_job(job, 'job_completed')
            
            # Log analytics event
            AnalyticsEvent.objects.create(
                customer=job.customer,
                event_type='job_completed',
                metadata={
                    'job_id': job.id,
                    'final_amount': float(final_amount) if final_amount else 0,
                    'completion_date': job.completed_date.isoformat()
                }
            )
            
            logger.info(f"Completed job {job.job_number}")
            return True
        
        except Exception as e:
            logger.error(f"Error completing job: {e}")
            return False


# Utility functions for periodic tasks

def process_overdue_quotes():
    """Find and process overdue quotes that need follow-up"""
    
    overdue_quotes = QuoteRequest.objects.filter(
        status='quoted',
        quote_sent_at__lt=timezone.now() - timedelta(days=3),
        response_received_at__isnull=True
    )
    
    for quote in overdue_quotes:
        QuoteJobAutomationEngine.send_quote_follow_up(quote)


def check_job_deadlines():
    """Check for jobs approaching deadlines and send alerts"""
    
    upcoming_deadlines = Job.objects.filter(
        status__in=['pending', 'in_progress'],
        due_date__lte=timezone.now() + timedelta(days=1),
        due_date__gt=timezone.now()
    )
    
    for job in upcoming_deadlines:
        # Send alert to assigned user and customer
        QuoteJobAutomationEngine.send_auto_response_for_job(job, 'job_deadline_approaching')


def auto_update_job_progress():
    """Automatically update job progress based on time elapsed"""
    
    active_jobs = Job.objects.filter(
        status='in_progress',
        start_date__isnull=False,
        due_date__isnull=False
    )
    
    for job in active_jobs:
        if job.update_frequency == 'weekly':
            last_update = JobUpdate.objects.filter(job=job).order_by('-created_at').first()
            
            if not last_update or (timezone.now() - last_update.created_at).days >= 7:
                # Send weekly progress update
                progress = job.progress_percentage
                update_text = f"Weekly progress update: {progress:.0f}% complete"
                
                QuoteJobAutomationEngine.send_job_progress_update(
                    job=job,
                    update_text=update_text,
                    percentage_complete=int(progress)
                )