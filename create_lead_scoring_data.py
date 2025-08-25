#!/usr/bin/env python
"""Create sample lead scoring data for the mAgent CRM system"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone
from django.db.models import Count

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magent.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Customer, Tag
from analytics.models import (
    LeadScoringRule, LeadScoringConfig, CustomerScore, 
    AnalyticsEvent, EmailDelivery, Task
)
from analytics.lead_scoring import LeadScoringEngine


def create_lead_scoring_sample_data():
    """Create comprehensive sample data for lead scoring system"""
    
    print("🎯 Creating Lead Scoring Sample Data...")
    
    # Get or create admin user
    admin_user, created = User.objects.get_or_create(
        username='admin',
        defaults={'email': 'admin@magent.co.nz', 'is_staff': True, 'is_superuser': True}
    )
    if created:
        admin_user.set_password('admin123')
        admin_user.save()
    
    # Create or update lead scoring configuration
    print("📋 Setting up lead scoring configuration...")
    config = LeadScoringConfig.get_config()
    config.min_score = 0
    config.max_score = 100
    config.cold_threshold = 20
    config.warm_threshold = 50
    config.hot_threshold = 75
    config.auto_calculation_enabled = True
    config.calculation_frequency = 'realtime'
    config.enable_score_decay = True
    config.decay_rate_percent = 2.0
    config.decay_frequency_days = 30
    config.notify_on_tier_change = True
    config.notify_on_qualified_lead = True
    config.updated_by = admin_user
    config.save()
    print(f"✅ Updated lead scoring configuration")
    
    # Create sample scoring rules
    print("📏 Creating sample scoring rules...")
    
    scoring_rules = [
        {
            'name': 'Email Not Empty',
            'description': 'Award points for having a valid email address',
            'rule_type': 'customer_attribute',
            'score_value': 10,
            'is_multiplier': False,
            'priority': 100,
            'condition_config': {
                'field_name': 'email',
                'condition': 'not_empty'
            }
        },
        {
            'name': 'Mobile Phone Provided',
            'description': 'Award points for providing mobile phone number',
            'rule_type': 'customer_attribute',
            'score_value': 8,
            'is_multiplier': False,
            'priority': 90,
            'condition_config': {
                'field_name': 'mobile',
                'condition': 'not_empty'
            }
        },
        {
            'name': 'Recent Interactions',
            'description': 'Points for customer interactions in last 30 days',
            'rule_type': 'interaction_count',
            'score_value': 5,
            'is_multiplier': False,
            'priority': 80,
            'condition_config': {
                'days_back': 30,
                'min_interactions': 1,
                'scale_by_count': True,
                'max_scaled_score': 25
            }
        },
        {
            'name': 'Email Engagement',
            'description': 'High points for email opens and clicks',
            'rule_type': 'email_engagement',
            'score_value': 15,
            'is_multiplier': False,
            'priority': 85,
            'condition_config': {
                'days_back': 30,
                'min_opens': 1,
                'min_clicks': 0,
                'engagement_rate_threshold': 25
            }
        },
        {
            'name': 'Task Completion',
            'description': 'Reward completed tasks',
            'rule_type': 'task_completion',
            'score_value': 10,
            'is_multiplier': False,
            'priority': 75,
            'condition_config': {
                'days_back': 60,
                'min_completed_tasks': 1,
                'scale_by_count': True,
                'max_scaled_score': 30
            }
        },
        {
            'name': 'File Uploads',
            'description': 'Points for uploading files',
            'rule_type': 'file_uploads',
            'score_value': 8,
            'is_multiplier': False,
            'priority': 70,
            'condition_config': {
                'days_back': 90,
                'min_uploads': 1
            }
        },
        {
            'name': 'Regular Notes',
            'description': 'Points for regular note activity',
            'rule_type': 'note_frequency',
            'score_value': 6,
            'is_multiplier': False,
            'priority': 65,
            'condition_config': {
                'days_back': 30,
                'min_notes': 2
            }
        },
        {
            'name': 'Auckland Location Bonus',
            'description': 'Bonus for Auckland-based customers',
            'rule_type': 'geographic_location',
            'score_value': 12,
            'is_multiplier': False,
            'priority': 60,
            'condition_config': {
                'cities': ['Auckland', 'auckland', 'AUCKLAND']
            }
        },
        {
            'name': 'VIP Tag Multiplier',
            'description': 'Multiplier for VIP customers',
            'rule_type': 'tag_presence',
            'score_value': 150,  # 150% = 1.5x multiplier
            'is_multiplier': True,
            'priority': 50,
            'condition_config': {
                'required_tags': ['VIP'],
                'condition': 'any'
            }
        },
        {
            'name': 'New Customer Period',
            'description': 'Bonus for new customers (within 30 days)',
            'rule_type': 'time_since_creation',
            'score_value': 15,
            'is_multiplier': False,
            'priority': 40,
            'condition_config': {
                'days_threshold': 30,
                'condition': 'newer_than'
            }
        }
    ]
    
    created_rules = []
    for rule_data in scoring_rules:
        rule_data['created_by'] = admin_user  # Add created_by field
        rule, created = LeadScoringRule.objects.get_or_create(
            name=rule_data['name'],
            defaults=rule_data
        )
        if created:
            print(f"  ✅ Created rule: {rule.name}")
            created_rules.append(rule)
        else:
            print(f"  ↻ Rule already exists: {rule.name}")
    
    # Create some sample tags
    print("🏷️ Creating sample tags...")
    vip_tag, created = Tag.objects.get_or_create(
        name='VIP',
        defaults={'color': '#dc3545'}  # Red color
    )
    premium_tag, created = Tag.objects.get_or_create(
        name='Premium',
        defaults={'color': '#ffc107'}  # Yellow color
    )
    enterprise_tag, created = Tag.objects.get_or_create(
        name='Enterprise',
        defaults={'color': '#198754'}  # Green color
    )
    
    # Add some analytics events and email deliveries for existing customers
    print("📊 Creating sample analytics events...")
    customers = Customer.objects.all()[:10]  # Work with first 10 customers
    
    for i, customer in enumerate(customers):
        # Create some analytics events
        events_count = (i % 5) + 1  # 1-5 events per customer
        for j in range(events_count):
            event_date = timezone.now() - timedelta(days=(j * 3))
            AnalyticsEvent.objects.get_or_create(
                customer=customer,
                event_type='viewed',
                timestamp=event_date,
                defaults={
                    'metadata': {
                        'page': f'/customer/{customer.pk}/',
                        'duration': 45 + (j * 10)
                    }
                }
            )
        
        # Create email deliveries
        if i % 2 == 0:  # Half the customers get email deliveries
            EmailDelivery.objects.get_or_create(
                customer=customer,
                subject='Welcome to our service!',
                defaults={
                    'status': 'opened' if i % 3 == 0 else 'delivered',
                    'sent_by': admin_user,
                    'sent_at': timezone.now() - timedelta(days=5)
                }
            )
        
        # Create some tasks
        if i % 3 == 0:  # Third of customers get tasks
            Task.objects.get_or_create(
                title=f'Follow up with {customer.first_name}',
                customer=customer,
                defaults={
                    'description': f'Follow up call for {customer.full_name}',
                    'status': 'completed' if i % 2 == 0 else 'pending',
                    'priority': 'medium',
                    'due_date': timezone.now() + timedelta(days=7),
                    'assigned_to': admin_user,
                    'created_by': admin_user,
                    'completed_at': timezone.now() - timedelta(days=1) if i % 2 == 0 else None
                }
            )
        
        # Add tags to some customers
        if i < 3:  # First 3 customers get VIP tag
            customer.tags.add(vip_tag)
        elif i < 6:  # Next 3 get Premium tag
            customer.tags.add(premium_tag)
        elif i < 8:  # Next 2 get Enterprise tag
            customer.tags.add(enterprise_tag)
    
    print("🧮 Calculating lead scores for all customers...")
    
    # Calculate scores for all customers
    calc_log = LeadScoringEngine.bulk_calculate_scores(user=admin_user)
    
    print(f"✅ Bulk calculation completed:")
    print(f"   📊 Calculation ID: {calc_log.calculation_id}")
    print(f"   👥 Customers processed: {calc_log.customers_processed}")
    print(f"   📈 Scores changed: {calc_log.scores_changed}")
    print(f"   🎯 Tier changes: {calc_log.tier_changes}")
    print(f"   ⏱️ Status: {calc_log.status}")
    
    # Display score summary
    print("\n📊 Lead Scoring Summary:")
    tier_counts = CustomerScore.objects.values('score_tier').annotate(
        count=Count('id')
    ).order_by('score_tier')
    
    for tier_stat in tier_counts:
        tier = tier_stat['score_tier']
        count = tier_stat['count']
        print(f"   {tier.upper()}: {count} customers")
    
    # Show top scoring customers
    print("\n🏆 Top 5 Scoring Customers:")
    top_customers = CustomerScore.objects.select_related('customer').order_by('-current_score')[:5]
    
    for i, customer_score in enumerate(top_customers, 1):
        customer = customer_score.customer
        print(f"   {i}. {customer.full_name} - {customer_score.current_score} points ({customer_score.score_tier})")
    
    print(f"\n🎯 Lead Scoring Sample Data Creation Complete!")
    print(f"   📏 Created {len(created_rules)} new scoring rules")
    print(f"   📊 Processed {customers.count()} customers")
    print(f"   🎯 Lead scoring system is ready for testing!")
    
    return calc_log


if __name__ == '__main__':
    create_lead_scoring_sample_data()