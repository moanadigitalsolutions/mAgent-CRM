from django.core.management.base import BaseCommand
from django.utils import timezone
from analytics.email_automation import EmailAutomationEngine


class Command(BaseCommand):
    help = 'Process scheduled email sequences and deliveries'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be processed without actually sending emails',
        )
    
    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting email processing at {timezone.now()}')
        )
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No emails will be sent')
            )
        
        try:
            if not dry_run:
                processed_count, error_count = EmailAutomationEngine.process_scheduled_emails()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Successfully processed {processed_count} scheduled emails'
                    )
                )
                
                if error_count > 0:
                    self.stdout.write(
                        self.style.WARNING(
                            f'{error_count} emails failed to process'
                        )
                    )
            else:
                # Show what would be processed in dry run
                from analytics.models import EmailDelivery
                scheduled_emails = EmailDelivery.objects.filter(status='scheduled')
                
                self.stdout.write(
                    f'Would process {scheduled_emails.count()} scheduled emails:'
                )
                
                for delivery in scheduled_emails[:10]:  # Show first 10
                    self.stdout.write(
                        f'  - {delivery.customer.email}: {delivery.subject}'
                    )
                
                if scheduled_emails.count() > 10:
                    self.stdout.write(f'  ... and {scheduled_emails.count() - 10} more')
        
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error processing emails: {str(e)}')
            )
            raise
        
        self.stdout.write(
            self.style.SUCCESS('Email processing completed')
        )