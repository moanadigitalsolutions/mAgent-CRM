from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import random

from customers.models import Customer
from analytics.models import AnalyticsEvent, CustomerMetrics
from analytics.utils import AnalyticsCalculator


class Command(BaseCommand):
    help = 'Generate sample analytics data for testing'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=30,
            help='Number of days of historical data to generate'
        )
        parser.add_argument(
            '--events-per-day',
            type=int,
            default=10,
            help='Average number of events per day'
        )
    
    def handle(self, *args, **options):
        days = options['days']
        events_per_day = options['events_per_day']
        
        self.stdout.write(f'Generating {days} days of analytics data...')
        
        # Get customers and users
        customers = list(Customer.objects.filter(is_active=True))
        users = list(User.objects.all())
        
        if not customers:
            self.stdout.write(
                self.style.WARNING('No customers found. Please create some customers first.')
            )
            return
        
        if not users:
            self.stdout.write(
                self.style.WARNING('No users found. Please create a user first.')
            )
            return
        
        # Event types to generate
        event_types = [
            'created', 'updated', 'viewed', 'note_added', 
            'file_uploaded', 'email_sent', 'call_made', 'meeting_scheduled'
        ]
        
        events_created = 0
        
        # Generate events for each day
        for day_offset in range(days):
            event_date = timezone.now() - timedelta(days=day_offset)
            
            # Generate random number of events for this day
            num_events = random.randint(
                max(1, events_per_day - 5), 
                events_per_day + 5
            )
            
            for _ in range(num_events):
                customer = random.choice(customers)
                event_type = random.choice(event_types)
                user = random.choice(users)
                
                # Create the event with backdated timestamp
                event = AnalyticsEvent.objects.create(
                    customer=customer,
                    event_type=event_type,
                    user=user,
                    metadata={
                        'generated': True,
                        'day_offset': day_offset
                    }
                )
                
                # Manually set the timestamp to the backdated time
                random_hour = random.randint(8, 18)  # Business hours
                random_minute = random.randint(0, 59)
                
                event.timestamp = event_date.replace(
                    hour=random_hour,
                    minute=random_minute,
                    second=random.randint(0, 59)
                )
                event.save()
                
                events_created += 1
        
        self.stdout.write(f'Created {events_created} analytics events')
        
        # Calculate metrics for all customers
        self.stdout.write('Calculating customer metrics...')
        metrics_updated = 0
        
        for customer in customers:
            AnalyticsCalculator.calculate_customer_metrics(customer)
            metrics_updated += 1
        
        self.stdout.write(f'Updated metrics for {metrics_updated} customers')
        
        # Calculate dashboard metrics
        self.stdout.write('Calculating dashboard metrics...')
        AnalyticsCalculator.calculate_dashboard_metrics()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully generated analytics data:\n'
                f'- {events_created} events over {days} days\n'
                f'- {metrics_updated} customer metrics updated\n'
                f'- Dashboard metrics calculated'
            )
        )