from django.db import models
from django.utils import timezone
from django.db.models import Count, Q, Avg, F
from datetime import datetime, timedelta
from customers.models import Customer
from .models import AnalyticsEvent, CustomerMetrics, DashboardMetric
import json


class AnalyticsCalculator:
    """Calculate various analytics metrics"""
    
    @staticmethod
    def calculate_customer_metrics(customer):
        """Calculate metrics for a specific customer"""
        # Get or create metrics object
        metrics, created = CustomerMetrics.objects.get_or_create(
            customer=customer,
            defaults={
                'total_interactions': 0,
                'notes_count': 0,
                'files_count': 0,
                'engagement_score': 0.0,
                'profile_completeness': 0.0,
                'lead_score': 0.0,
            }
        )
        
        # Calculate interactions
        metrics.total_interactions = AnalyticsEvent.objects.filter(customer=customer).count()
        metrics.notes_count = customer.notes.count()
        metrics.files_count = customer.files.count()
        
        # Calculate last interaction
        last_event = AnalyticsEvent.objects.filter(customer=customer).first()
        if last_event:
            metrics.last_interaction_date = last_event.timestamp
        
        # Calculate profile completeness
        metrics.profile_completeness = AnalyticsCalculator._calculate_profile_completeness(customer)
        
        # Calculate engagement score
        metrics.engagement_score = AnalyticsCalculator._calculate_engagement_score(customer)
        
        # Calculate lead score
        metrics.lead_score = AnalyticsCalculator._calculate_lead_score(customer)
        
        metrics.save()
        return metrics
    
    @staticmethod
    def _calculate_profile_completeness(customer):
        """Calculate how complete a customer profile is"""
        total_fields = 10  # Adjust based on important fields
        completed_fields = 0
        
        # Check required fields
        if customer.first_name:
            completed_fields += 1
        if customer.last_name:
            completed_fields += 1
        if customer.email:
            completed_fields += 1
        if customer.mobile:
            completed_fields += 1
        if customer.street_address:
            completed_fields += 1
        if customer.suburb:
            completed_fields += 1
        if customer.city:
            completed_fields += 1
        if customer.postcode:
            completed_fields += 1
        
        # Check if has notes
        if customer.notes.exists():
            completed_fields += 1
        
        # Check if has custom field values
        if customer.custom_field_values.exists():
            completed_fields += 1
        
        return (completed_fields / total_fields) * 100
    
    @staticmethod
    def _calculate_engagement_score(customer):
        """Calculate customer engagement score"""
        score = 0.0
        
        # Recent activity (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_events = AnalyticsEvent.objects.filter(
            customer=customer,
            timestamp__gte=thirty_days_ago
        ).count()
        
        # Score based on recent activity
        score += min(recent_events * 10, 50)  # Max 50 points for activity
        
        # Score based on total interactions
        total_interactions = AnalyticsEvent.objects.filter(customer=customer).count()
        score += min(total_interactions * 2, 30)  # Max 30 points for total interactions
        
        # Score based on profile completeness
        profile_score = AnalyticsCalculator._calculate_profile_completeness(customer)
        score += profile_score * 0.2  # Max 20 points for completeness
        
        return min(score, 100)  # Cap at 100
    
    @staticmethod
    def _calculate_lead_score(customer):
        """Calculate lead scoring"""
        score = 0.0
        
        # Base scoring factors
        if customer.email:
            score += 20  # Has email
        if customer.mobile:
            score += 15  # Has mobile
        if customer.street_address:
            score += 10  # Has address
        
        # Engagement-based scoring
        engagement_score = AnalyticsCalculator._calculate_engagement_score(customer)
        score += engagement_score * 0.3  # 30% of engagement score
        
        # Notes and interactions
        notes_count = customer.notes.count()
        score += min(notes_count * 5, 25)  # Max 25 points for notes
        
        # Recent activity boost
        seven_days_ago = timezone.now() - timedelta(days=7)
        recent_activity = AnalyticsEvent.objects.filter(
            customer=customer,
            timestamp__gte=seven_days_ago
        ).exists()
        
        if recent_activity:
            score += 10  # Recent activity bonus
        
        return min(score, 100)  # Cap at 100
    
    @staticmethod
    def calculate_dashboard_metrics():
        """Calculate and store dashboard metrics"""
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # Total customers
        total_customers = Customer.objects.filter(is_active=True).count()
        DashboardMetric.objects.update_or_create(
            metric_type='total_customers',
            defaults={'value': {'count': total_customers}}
        )
        
        # New customers today
        new_today = Customer.objects.filter(
            created_at__date=today,
            is_active=True
        ).count()
        DashboardMetric.objects.update_or_create(
            metric_type='new_customers_today',
            defaults={'value': {'count': new_today}}
        )
        
        # New customers this week
        new_week = Customer.objects.filter(
            created_at__gte=week_ago,
            is_active=True
        ).count()
        DashboardMetric.objects.update_or_create(
            metric_type='new_customers_week',
            defaults={'value': {'count': new_week}}
        )
        
        # New customers this month
        new_month = Customer.objects.filter(
            created_at__gte=month_ago,
            is_active=True
        ).count()
        DashboardMetric.objects.update_or_create(
            metric_type='new_customers_month',
            defaults={'value': {'count': new_month}}
        )
        
        # Active customers (with recent activity)
        active_customers = Customer.objects.filter(
            is_active=True,
            analytics_events__timestamp__gte=month_ago
        ).distinct().count()
        DashboardMetric.objects.update_or_create(
            metric_type='active_customers',
            defaults={'value': {'count': active_customers}}
        )
        
        # Top cities
        top_cities = Customer.objects.filter(is_active=True).values('city').annotate(
            count=Count('id')
        ).exclude(city__isnull=True).exclude(city='').order_by('-count')[:5]
        
        DashboardMetric.objects.update_or_create(
            metric_type='top_cities',
            defaults={'value': {'cities': list(top_cities)}}
        )
        
        # Engagement rate
        total_with_metrics = CustomerMetrics.objects.count()
        if total_with_metrics > 0:
            avg_engagement = CustomerMetrics.objects.aggregate(
                avg_score=Avg('engagement_score')
            )['avg_score'] or 0
        else:
            avg_engagement = 0
        
        DashboardMetric.objects.update_or_create(
            metric_type='engagement_rate',
            defaults={'value': {'rate': round(avg_engagement, 2)}}
        )
        
        # Average profile completeness
        if total_with_metrics > 0:
            avg_completeness = CustomerMetrics.objects.aggregate(
                avg_completeness=Avg('profile_completeness')
            )['avg_completeness'] or 0
        else:
            avg_completeness = 0
        
        DashboardMetric.objects.update_or_create(
            metric_type='avg_profile_completeness',
            defaults={'value': {'percentage': round(avg_completeness, 2)}}
        )
    
    @staticmethod
    def get_customer_trends(days=30):
        """Get customer acquisition trends for the specified number of days"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Generate daily counts
        daily_counts = []
        current_date = start_date
        
        while current_date <= end_date:
            count = Customer.objects.filter(
                created_at__date=current_date,
                is_active=True
            ).count()
            
            daily_counts.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
            current_date += timedelta(days=1)
        
        return daily_counts
    
    @staticmethod
    def get_engagement_trends(days=30):
        """Get engagement trends for the specified number of days"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        daily_engagement = []
        current_date = start_date
        
        while current_date <= end_date:
            count = AnalyticsEvent.objects.filter(
                timestamp__date=current_date
            ).count()
            
            daily_engagement.append({
                'date': current_date.strftime('%Y-%m-%d'),
                'count': count
            })
            current_date += timedelta(days=1)
        
        return daily_engagement
    
    @staticmethod
    def get_geographic_distribution():
        """Get customer distribution by city"""
        return Customer.objects.filter(is_active=True).values('city').annotate(
            count=Count('id')
        ).exclude(city__isnull=True).exclude(city='').order_by('-count')


def track_event(customer, event_type, user=None, metadata=None):
    """Helper function to track analytics events"""
    AnalyticsEvent.objects.create(
        customer=customer,
        event_type=event_type,
        user=user,
        metadata=metadata or {}
    )
    
    # Update customer metrics
    AnalyticsCalculator.calculate_customer_metrics(customer)