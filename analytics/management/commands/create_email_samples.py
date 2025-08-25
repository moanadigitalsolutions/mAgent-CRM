from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from analytics.models import EmailTemplate, EmailSequence, EmailSequenceStep


class Command(BaseCommand):
    help = 'Create sample email templates and sequences for testing'
    
    def handle(self, *args, **options):
        # Get or create a user for the templates
        try:
            user = User.objects.get(is_superuser=True)
        except User.DoesNotExist:
            user = User.objects.create_superuser(
                'admin', 'admin@example.com', 'admin123'
            )
        
        self.stdout.write('Creating sample email templates...')
        
        # Welcome email template
        welcome_template, created = EmailTemplate.objects.get_or_create(
            name='Welcome Email',
            defaults={
                'subject': 'Welcome to our service, {{customer_first_name}}!',
                'content': '''Dear {{customer_first_name}},

Welcome to our service! We're excited to have you on board.

Here's what you can expect:
- Personalized service tailored to your needs
- Regular updates and insights
- Dedicated support whenever you need it

If you have any questions, feel free to reach out to us at {{company_email}}.

Best regards,
{{company_name}} Team''',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: #007bff; color: white; padding: 20px; text-align: center; }
        .content { padding: 20px; background: #f9f9f9; }
        .footer { padding: 20px; text-align: center; color: #666; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to {{company_name}}!</h1>
        </div>
        <div class="content">
            <p>Dear {{customer_first_name}},</p>
            <p>Welcome to our service! We're excited to have you on board.</p>
            <h3>What you can expect:</h3>
            <ul>
                <li>Personalized service tailored to your needs</li>
                <li>Regular updates and insights</li>
                <li>Dedicated support whenever you need it</li>
            </ul>
            <p>If you have any questions, feel free to reach out to us.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>{{company_name}} Team</p>
        </div>
    </div>
</body>
</html>''',
                'available_variables': ['customer_first_name', 'customer_name', 'company_name', 'company_email'],
                'created_by': user,
                'is_active': True
            }
        )
        
        # Follow-up email template
        followup_template, created = EmailTemplate.objects.get_or_create(
            name='Follow-up Email',
            defaults={
                'subject': 'How are you enjoying our service, {{customer_first_name}}?',
                'content': '''Hi {{customer_first_name}},

We hope you're enjoying our service so far! It's been a few days since you joined us, and we wanted to check in.

Here are some things you might want to explore:
- Browse our latest features
- Connect with our community
- Schedule a consultation with our team

Is there anything we can help you with? Just reply to this email or give us a call at {{company_phone}}.

Best regards,
{{company_name}} Team''',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .content { padding: 20px; }
        .cta { background: #28a745; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 20px 0; }
    </style>
</head>
<body>
    <div class="container">
        <div class="content">
            <h2>How are you enjoying our service?</h2>
            <p>Hi {{customer_first_name}},</p>
            <p>We hope you're enjoying our service so far! It's been a few days since you joined us, and we wanted to check in.</p>
            
            <h3>Things to explore:</h3>
            <ul>
                <li>Browse our latest features</li>
                <li>Connect with our community</li>
                <li>Schedule a consultation with our team</li>
            </ul>
            
            <a href="#" class="cta">Get Support</a>
            
            <p>Is there anything we can help you with? Just reply to this email!</p>
            <p>Best regards,<br>{{company_name}} Team</p>
        </div>
    </div>
</body>
</html>''',
                'available_variables': ['customer_first_name', 'customer_name', 'company_name', 'company_phone'],
                'created_by': user,
                'is_active': True
            }
        )
        
        # Special offer email template
        offer_template, created = EmailTemplate.objects.get_or_create(
            name='Special Offer',
            defaults={
                'subject': 'Exclusive offer just for you, {{customer_first_name}}!',
                'content': '''Dear {{customer_first_name}},

We have a special offer just for you!

As a valued customer, you're eligible for:
- 20% off your next service
- Priority support
- Exclusive access to new features

This offer is valid until {{current_date}} and is exclusively for customers in {{customer_city}}.

Use code: SPECIAL20

Don't miss out on this limited-time offer!

Best regards,
{{company_name}} Team''',
                'html_content': '''<!DOCTYPE html>
<html>
<head>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
        .container { max-width: 600px; margin: 0 auto; padding: 20px; }
        .offer-box { background: #ff6b6b; color: white; padding: 30px; text-align: center; border-radius: 10px; margin: 20px 0; }
        .code { background: #fff; color: #ff6b6b; padding: 10px 20px; font-size: 24px; font-weight: bold; border-radius: 5px; margin: 15px 0; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Exclusive Offer!</h1>
        <p>Dear {{customer_first_name}},</p>
        
        <div class="offer-box">
            <h2>Special Offer Just for You!</h2>
            <p>As a valued customer, you're eligible for:</p>
            <ul style="text-align: left; display: inline-block;">
                <li>20% off your next service</li>
                <li>Priority support</li>
                <li>Exclusive access to new features</li>
            </ul>
            <div class="code">SPECIAL20</div>
            <p>Valid until {{current_date}}</p>
        </div>
        
        <p>Don't miss out on this limited-time offer!</p>
        <p>Best regards,<br>{{company_name}} Team</p>
    </div>
</body>
</html>''',
                'available_variables': ['customer_first_name', 'customer_name', 'customer_city', 'current_date', 'company_name'],
                'created_by': user,
                'is_active': True
            }
        )
        
        self.stdout.write('Creating sample email sequences...')
        
        # New customer onboarding sequence
        onboarding_sequence, created = EmailSequence.objects.get_or_create(
            name='New Customer Onboarding',
            defaults={
                'description': 'Welcome new customers and guide them through our service',
                'trigger_type': 'customer_created',
                'is_active': True,
                'created_by': user
            }
        )
        
        if created:
            # Step 1: Welcome email (immediate)
            EmailSequenceStep.objects.create(
                sequence=onboarding_sequence,
                template=welcome_template,
                step_number=1,
                delay_days=0,
                delay_hours=0
            )
            
            # Step 2: Follow-up email (3 days later)
            EmailSequenceStep.objects.create(
                sequence=onboarding_sequence,
                template=followup_template,
                step_number=2,
                delay_days=3,
                delay_hours=0
            )
            
            # Step 3: Special offer (7 days later)
            EmailSequenceStep.objects.create(
                sequence=onboarding_sequence,
                template=offer_template,
                step_number=3,
                delay_days=7,
                delay_hours=0
            )
        
        # Re-engagement sequence
        reengagement_sequence, created = EmailSequence.objects.get_or_create(
            name='Customer Re-engagement',
            defaults={
                'description': 'Re-engage customers who haven\'t been active',
                'trigger_type': 'manual',
                'is_active': True,
                'created_by': user
            }
        )
        
        if created:
            # Step 1: Follow-up email (immediate)
            EmailSequenceStep.objects.create(
                sequence=reengagement_sequence,
                template=followup_template,
                step_number=1,
                delay_days=0,
                delay_hours=0
            )
            
            # Step 2: Special offer (5 days later)
            EmailSequenceStep.objects.create(
                sequence=reengagement_sequence,
                template=offer_template,
                step_number=2,
                delay_days=5,
                delay_hours=0
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully created:'
                f'\n  - 3 email templates'
                f'\n  - 2 email sequences'
                f'\n  - 5 sequence steps'
            )
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                'Email automation samples created successfully!'
            )
        )