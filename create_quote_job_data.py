"""
Sample data for quote/job automation system
Creates email auto-response templates and sample quotes/jobs
"""

import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magent.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Customer
from analytics.models import QuoteRequest, Job, JobUpdate, EmailAutoResponse
from analytics.quote_job_automation import QuoteJobAutomationEngine
from decimal import Decimal
import random


def create_email_templates():
    """Create auto-response email templates"""
    
    # Get first staff user as creator
    staff_user = User.objects.filter(is_staff=True).first()
    if not staff_user:
        print("No staff users found. Please create a staff user first.")
        return 0
    
    templates = [
        {
            'name': 'Quote Request Auto-Response',
            'trigger_type': 'quote_request',
            'subject_template': 'Thank you for your quote request - #{reference_number}',
            'body_template': '''Dear {customer_name},

Thank you for contacting us about your {service_type} project.

We've received your quote request and assigned it reference number #{reference_number}. Our team will review your requirements and provide you with a detailed quote within 2-3 business days.

Your Request Details:
- Service Type: {service_type}
- Priority: {priority}
- Request Date: {request_date}

What happens next:
1. Our team will review your requirements
2. We'll prepare a detailed quote with timeline and pricing
3. You'll receive your personalized quote within 2-3 business days
4. We'll follow up to discuss any questions you may have

If you have any urgent questions, please don't hesitate to contact us at your-email@company.com or call (555) 123-4567.

We appreciate your business and look forward to working with you!

Best regards,
mAgent CRM Team
            ''',
            'delay_minutes': 0,
        },
        {
            'name': 'Quote Response Sent',
            'trigger_type': 'quote_response',
            'subject_template': 'Your Quote is Ready - #{reference_number}',
            'body_template': '''Dear {customer_name},

Great news! Your quote #{reference_number} is ready for review.

Quote Details:
- Project: {title}
- Service Type: {service_type}
- Quote Amount: ${quote_amount}
- Valid Until: {quote_valid_date}

{quote_notes}

Next Steps:
To accept this quote, simply reply to this email or call us at (555) 123-4567. We can begin work as soon as you're ready!

If you have any questions about the quote or would like to discuss any modifications, our team is here to help.

We appreciate your consideration and look forward to working with you.

Best regards,
mAgent CRM Team
            ''',
            'delay_minutes': 0,
        },
        {
            'name': 'Job Started Notification',
            'trigger_type': 'job_started',
            'subject_template': 'Your Project Has Started - Job #{job_number}',
            'body_template': '''Dear {customer_name},

Excellent! We're excited to begin work on your project.

Project Details:
- Job Number: #{job_number}
- Project: {title}
- Start Date: {start_date}
- Expected Completion: {due_date}
- Assigned Team Member: {assigned_to}

We'll keep you updated on our progress {update_frequency}. You can expect regular updates as we work through each phase of your project.

If you have any questions or concerns at any time, please don't hesitate to reach out to us.

Thank you for choosing mAgent CRM!

Best regards,
Your Project Team
            ''',
            'delay_minutes': 0,
        },
        {
            'name': 'Job Progress Update',
            'trigger_type': 'job_progress',
            'subject_template': 'Progress Update - Job #{job_number}',
            'body_template': '''Dear {customer_name},

Here's an update on your project:

Project: {title}
Current Status: {progress_percentage}% Complete
{progress_text}

Hours Worked This Period: {hours_worked}
Total Hours: {total_hours}

Next Steps:
{next_steps}

We remain on track to complete your project by {due_date}. If you have any questions about this update, please feel free to contact your assigned team member.

Thank you for your continued trust in our services.

Best regards,
Your Project Team
            ''',
            'delay_minutes': 0,
        },
        {
            'name': 'Job Completed Notification',
            'trigger_type': 'job_completed',
            'subject_template': 'Project Complete! - Job #{job_number}',
            'body_template': '''Dear {customer_name},

Congratulations! Your project has been completed successfully.

Project Summary:
- Job Number: #{job_number}
- Project: {title}
- Completion Date: {completion_date}
- Final Amount: ${final_amount}

What's Included:
{completion_summary}

Next Steps:
1. Please review the completed work
2. We'll send your invoice shortly
3. Let us know if you have any questions

We hope you're delighted with the results! Your feedback is important to us, so please let us know how we did.

Thank you for choosing mAgent CRM. We look forward to working with you again in the future.

Best regards,
mAgent CRM Team
            ''',
            'delay_minutes': 0,
        },
        {
            'name': 'Quote Follow-up',
            'trigger_type': 'follow_up',
            'subject_template': 'Following up on your quote - #{reference_number}',
            'body_template': '''Dear {customer_name},

I hope this message finds you well. I wanted to follow up on the quote we sent you a few days ago for your {service_type} project.

Quote Reference: #{reference_number}
Project: {title}
Quote Amount: ${quote_amount}

We understand that choosing the right service provider is an important decision, and we're here to answer any questions you might have about our proposal.

Some common questions we can help with:
- Timeline and scheduling details
- Specific services included
- Payment terms and options
- Any modifications to the scope

Would you like to schedule a quick call to discuss your project further? We're committed to providing excellent service and want to ensure we meet all your needs.

Please feel free to reply to this email or call us at (555) 123-4567.

Best regards,
mAgent CRM Team
            ''',
            'delay_minutes': 0,
        },
    ]
    
    created_count = 0
    for template_data in templates:
        template_data['created_by'] = staff_user  # Add creator
        template, created = EmailAutoResponse.objects.get_or_create(
            name=template_data['name'],
            defaults=template_data
        )
        if created:
            created_count += 1
            print(f"Created template: {template.name}")
    
    print(f"\nCreated {created_count} email templates")
    return created_count


def create_sample_quotes():
    """Create sample quote requests"""
    
    # Get some customers
    customers = list(Customer.objects.all()[:5])
    staff = list(User.objects.filter(is_staff=True))
    
    if not customers or not staff:
        print("Need customers and staff users to create sample quotes")
        return 0
    
    sample_quotes = [
        {
            'customer': random.choice(customers),
            'title': 'Website Development Project',
            'description': 'Need a modern, responsive website for our small business. Should include contact forms, gallery, and basic SEO.',
            'service_type': 'project',
            'priority': 'medium',
            'source': 'email',
            'assigned_to': random.choice(staff),
            'estimated_cost': Decimal('2500.00'),
            'status': 'quoted',
            'final_quote_amount': Decimal('2800.00'),
            'auto_response_sent': True,
        },
        {
            'customer': random.choice(customers),
            'title': 'Computer Repair Service',
            'description': 'Laptop is running very slowly and getting overheated. Needs diagnosis and repair.',
            'service_type': 'repair',
            'priority': 'high',
            'source': 'phone',
            'assigned_to': random.choice(staff),
            'estimated_cost': Decimal('150.00'),
            'status': 'reviewing',
            'auto_response_sent': True,
        },
        {
            'customer': random.choice(customers),
            'title': 'Network Installation',
            'description': 'Small office needs new network setup with WiFi access points and security configuration.',
            'service_type': 'installation',
            'priority': 'medium',
            'source': 'email',
            'assigned_to': random.choice(staff),
            'estimated_cost': Decimal('800.00'),
            'status': 'received',
            'auto_response_sent': False,
        },
        {
            'customer': random.choice(customers),
            'title': 'Software Consultation',
            'description': 'Need advice on choosing the right CRM system for our growing business.',
            'service_type': 'consultation',
            'priority': 'low',
            'source': 'website',
            'assigned_to': random.choice(staff),
            'estimated_cost': Decimal('200.00'),
            'status': 'quoted',
            'final_quote_amount': Decimal('250.00'),
            'auto_response_sent': True,
        },
        {
            'customer': random.choice(customers),
            'title': 'Emergency Server Recovery',
            'description': 'Server crashed and we need immediate assistance to recover data and get systems back online.',
            'service_type': 'repair',
            'priority': 'urgent',
            'source': 'phone',
            'assigned_to': random.choice(staff),
            'estimated_cost': Decimal('500.00'),
            'status': 'accepted',
            'final_quote_amount': Decimal('450.00'),
            'auto_response_sent': True,
        },
    ]
    
    created_count = 0
    for quote_data in sample_quotes:
        quote = QuoteRequest.objects.create(**quote_data)
        created_count += 1
        print(f"Created quote: {quote.reference_number} - {quote.title}")
    
    print(f"\nCreated {created_count} sample quotes")
    return created_count


def create_sample_jobs():
    """Create sample jobs from accepted quotes"""
    
    # Get accepted quotes
    accepted_quotes = QuoteRequest.objects.filter(status='accepted')
    staff = list(User.objects.filter(is_staff=True))
    
    if not accepted_quotes or not staff:
        print("Need accepted quotes and staff to create sample jobs")
        return 0
    
    created_count = 0
    for quote in accepted_quotes:
        if hasattr(quote, 'job'):
            continue  # Already has a job
        
        job = QuoteJobAutomationEngine.convert_quote_to_job(quote, random.choice(staff))
        if job:
            # Add some progress updates
            updates = [
                {
                    'update_type': 'progress',
                    'title': 'Project kickoff meeting completed',
                    'description': 'Met with customer to review requirements and project timeline. All systems go!',
                    'percentage_complete': 15,
                    'hours_worked': 2.0,
                },
                {
                    'update_type': 'progress',
                    'title': 'Initial setup phase complete',
                    'description': 'Completed initial analysis and setup. Moving to implementation phase.',
                    'percentage_complete': 40,
                    'hours_worked': 6.5,
                },
            ]
            
            for update_data in updates:
                JobUpdate.objects.create(
                    job=job,
                    created_by=job.assigned_to,
                    **update_data
                )
            
            created_count += 1
            print(f"Created job: {job.job_number} - {job.title}")
    
    print(f"\nCreated {created_count} sample jobs")
    return created_count


def main():
    """Main function to create all sample data"""
    
    print("Creating Quote/Job Automation Sample Data")
    print("=" * 50)
    
    template_count = create_email_templates()
    quote_count = create_sample_quotes()
    job_count = create_sample_jobs()
    
    print("\n" + "=" * 50)
    print("Sample Data Creation Complete!")
    print(f"- Email Templates: {template_count}")
    print(f"- Sample Quotes: {quote_count}")
    print(f"- Sample Jobs: {job_count}")
    print("\nYou can now test the quote/job automation system!")


if __name__ == '__main__':
    main()