from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Count, Sum, Avg, Q
from datetime import timedelta, datetime
from typing import Dict, List, Optional, Any
import logging
import uuid

from customers.models import Customer, CustomerNote, Tag
from .models import (
    LeadScoringRule, CustomerScore, ScoreHistory, ScoreCalculationLog, 
    LeadScoringConfig, AnalyticsEvent, EmailDelivery, Task
)
from .task_automation import WorkflowEngine

logger = logging.getLogger(__name__)


class LeadScoringEngine:
    """Core engine for calculating and managing lead scores"""
    
    @staticmethod
    def calculate_customer_score(customer: Customer, user: Optional[User] = None, 
                               force_recalculate: bool = False) -> CustomerScore:
        """Calculate lead score for a single customer"""
        
        # Get or create customer score record
        customer_score, created = CustomerScore.objects.get_or_create(
            customer=customer,
            defaults={'current_score': 0}
        )
        
        # Skip if recently calculated and not forcing
        if not force_recalculate and not created and customer_score.last_calculated:
            time_diff = timezone.now() - customer_score.last_calculated
            if time_diff < timedelta(minutes=5):  # Don't recalculate within 5 minutes
                return customer_score
        
        # Store previous score for comparison
        previous_score = customer_score.current_score
        previous_tier = customer_score.score_tier
        
        # Get active scoring rules
        rules = LeadScoringRule.objects.filter(is_active=True).order_by('-priority', 'name')
        
        # Calculate new score
        new_score = 0
        score_breakdown = {}
        
        for rule in rules:
            try:
                rule_score = LeadScoringEngine._evaluate_rule(customer, rule)
                
                if rule_score != 0:
                    if rule.is_multiplier:
                        new_score = int(new_score * (rule_score / 100))
                    else:
                        new_score += rule_score
                    
                    score_breakdown[rule.name] = {
                        'rule_id': rule.pk,
                        'score_contribution': rule_score,
                        'rule_type': rule.rule_type,
                        'is_multiplier': rule.is_multiplier
                    }
            
            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name} for customer {customer.pk}: {e}")
                continue
        
        # Apply score limits from configuration
        config = LeadScoringConfig.get_config()
        new_score = max(config.min_score, min(config.max_score, new_score))
        
        # Update customer score
        customer_score.previous_score = previous_score
        customer_score.current_score = new_score
        customer_score.score_change = new_score - previous_score
        customer_score.score_breakdown = score_breakdown
        customer_score.calculation_count += 1
        
        if customer_score.score_change != 0:
            customer_score.last_change_date = timezone.now()
        
        # Update tier
        customer_score.update_score_tier()
        customer_score.save()
        
        # Create history record if score changed
        if new_score != previous_score or customer_score.score_tier != previous_tier:
            ScoreHistory.objects.create(
                customer_score=customer_score,
                old_score=previous_score,
                new_score=new_score,
                score_change=new_score - previous_score,
                old_tier=previous_tier,
                new_tier=customer_score.score_tier,
                change_reason=f"Score recalculation using {len(rules)} rules",
                changed_by=user
            )
            
            # Trigger tier change workflows if tier changed
            if customer_score.score_tier != previous_tier:
                LeadScoringEngine._trigger_tier_change_workflows(customer, customer_score, user)
        
        return customer_score
    
    @staticmethod
    def _evaluate_rule(customer: Customer, rule: LeadScoringRule) -> int:
        """Evaluate a single scoring rule for a customer"""
        try:
            config = rule.condition_config
            
            if rule.rule_type == 'customer_attribute':
                return LeadScoringEngine._evaluate_customer_attribute_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'interaction_count':
                return LeadScoringEngine._evaluate_interaction_count_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'email_engagement':
                return LeadScoringEngine._evaluate_email_engagement_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'task_completion':
                return LeadScoringEngine._evaluate_task_completion_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'file_uploads':
                return LeadScoringEngine._evaluate_file_uploads_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'note_frequency':
                return LeadScoringEngine._evaluate_note_frequency_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'time_since_creation':
                return LeadScoringEngine._evaluate_time_since_creation_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'geographic_location':
                return LeadScoringEngine._evaluate_geographic_location_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'tag_presence':
                return LeadScoringEngine._evaluate_tag_presence_rule(customer, config, rule.score_value)
            
            elif rule.rule_type == 'custom_field':
                return LeadScoringEngine._evaluate_custom_field_rule(customer, config, rule.score_value)
            
            else:
                logger.warning(f"Unknown rule type: {rule.rule_type}")
                return 0
        
        except Exception as e:
            logger.error(f"Error evaluating rule {rule.name}: {e}")
            return 0
    
    @staticmethod
    def _evaluate_customer_attribute_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate customer attribute rules"""
        field_name = config.get('field_name')
        expected_value = config.get('expected_value')
        condition = config.get('condition', 'equals')  # equals, contains, greater_than, less_than
        
        if not field_name or not hasattr(customer, field_name):
            return 0
        
        actual_value = getattr(customer, field_name)
        
        if condition == 'equals':
            return score_value if str(actual_value) == str(expected_value) else 0
        elif condition == 'contains' and isinstance(actual_value, str) and expected_value:
            return score_value if str(expected_value).lower() in actual_value.lower() else 0
        elif condition == 'not_empty':
            return score_value if actual_value else 0
        elif condition == 'is_empty':
            return score_value if not actual_value else 0
        
        return 0
    
    @staticmethod
    def _evaluate_interaction_count_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate interaction count rules"""
        days_back = config.get('days_back', 30)
        min_interactions = config.get('min_interactions', 1)
        max_interactions = config.get('max_interactions')
        interaction_types = config.get('interaction_types', [])
        
        since_date = timezone.now() - timedelta(days=days_back)
        
        # Count analytics events as interactions
        query = AnalyticsEvent.objects.filter(customer=customer, timestamp__gte=since_date)
        
        if interaction_types:
            query = query.filter(event_type__in=interaction_types)
        
        interaction_count = query.count()
        
        # Check if count meets criteria
        if interaction_count >= min_interactions:
            if max_interactions is None or interaction_count <= max_interactions:
                # Scale score based on interaction count if specified
                if config.get('scale_by_count', False):
                    return min(score_value * interaction_count, config.get('max_scaled_score', score_value * 10))
                return score_value
        
        return 0
    
    @staticmethod
    def _evaluate_email_engagement_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate email engagement rules"""
        days_back = config.get('days_back', 30)
        min_opens = config.get('min_opens', 0)
        min_clicks = config.get('min_clicks', 0)
        engagement_rate_threshold = config.get('engagement_rate_threshold')
        
        since_date = timezone.now() - timedelta(days=days_back)
        
        # Get email deliveries
        deliveries = EmailDelivery.objects.filter(customer=customer, sent_at__gte=since_date)
        
        if not deliveries.exists():
            return 0
        
        total_emails = deliveries.count()
        opened_emails = deliveries.filter(status__in=['opened', 'clicked']).count()
        clicked_emails = deliveries.filter(status='clicked').count()
        
        # Calculate engagement rate
        engagement_rate = (opened_emails / total_emails * 100) if total_emails > 0 else 0
        
        # Check criteria
        score = 0
        if opened_emails >= min_opens:
            score += score_value // 2
        
        if clicked_emails >= min_clicks:
            score += score_value // 2
        
        if engagement_rate_threshold and engagement_rate >= engagement_rate_threshold:
            score += score_value
        
        return score
    
    @staticmethod
    def _evaluate_task_completion_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate task completion rules"""
        days_back = config.get('days_back', 30)
        min_completed_tasks = config.get('min_completed_tasks', 1)
        task_priorities = config.get('task_priorities', [])
        
        since_date = timezone.now() - timedelta(days=days_back)
        
        # Count completed tasks
        query = Task.objects.filter(
            customer=customer,
            status='completed',
            completed_at__gte=since_date
        )
        
        if task_priorities:
            query = query.filter(priority__in=task_priorities)
        
        completed_count = query.count()
        
        if completed_count >= min_completed_tasks:
            if config.get('scale_by_count', False):
                return min(score_value * completed_count, config.get('max_scaled_score', score_value * 5))
            return score_value
        
        return 0
    
    @staticmethod
    def _evaluate_file_uploads_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate file uploads rules"""
        days_back = config.get('days_back', 30)
        min_uploads = config.get('min_uploads', 1)
        
        since_date = timezone.now() - timedelta(days=days_back)
        
        # Count file upload events
        upload_count = AnalyticsEvent.objects.filter(
            customer=customer,
            event_type='file_uploaded',
            timestamp__gte=since_date
        ).count()
        
        if upload_count >= min_uploads:
            return score_value
        
        return 0
    
    @staticmethod
    def _evaluate_note_frequency_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate note frequency rules"""
        days_back = config.get('days_back', 30)
        min_notes = config.get('min_notes', 1)
        note_types = config.get('note_types', [])
        
        since_date = timezone.now() - timedelta(days=days_back)
        
        # Count customer notes
        query = CustomerNote.objects.filter(customer=customer, created_at__gte=since_date)
        
        if note_types:
            query = query.filter(note_type__in=note_types)
        
        note_count = query.count()
        
        if note_count >= min_notes:
            return score_value
        
        return 0
    
    @staticmethod
    def _evaluate_time_since_creation_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate time since creation rules"""
        days_threshold = config.get('days_threshold', 30)
        condition = config.get('condition', 'older_than')  # older_than, newer_than
        
        days_since_creation = (timezone.now() - customer.created_at).days
        
        if condition == 'older_than' and days_since_creation >= days_threshold:
            return score_value
        elif condition == 'newer_than' and days_since_creation <= days_threshold:
            return score_value
        
        return 0
    
    @staticmethod
    def _evaluate_geographic_location_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate geographic location rules"""
        target_cities = config.get('cities', [])
        target_suburbs = config.get('suburbs', [])  # New Zealand uses suburbs
        
        if target_cities and customer.city and customer.city.lower() in [city.lower() for city in target_cities]:
            return score_value
        
        if target_suburbs and customer.suburb and customer.suburb.lower() in [suburb.lower() for suburb in target_suburbs]:
            return score_value
        
        return 0
    
    @staticmethod
    def _evaluate_tag_presence_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate tag presence rules"""
        required_tags = config.get('required_tags', [])
        excluded_tags = config.get('excluded_tags', [])
        condition = config.get('condition', 'any')  # any, all
        
        customer_tags = [tag.name.lower() for tag in customer.tags.all()]
        
        # Check required tags
        if required_tags:
            required_tags_lower = [tag.lower() for tag in required_tags]
            
            if condition == 'any':
                has_required = any(tag in customer_tags for tag in required_tags_lower)
            else:  # all
                has_required = all(tag in customer_tags for tag in required_tags_lower)
            
            if not has_required:
                return 0
        
        # Check excluded tags
        if excluded_tags:
            excluded_tags_lower = [tag.lower() for tag in excluded_tags]
            has_excluded = any(tag in customer_tags for tag in excluded_tags_lower)
            
            if has_excluded:
                return 0
        
        return score_value
    
    @staticmethod
    def _evaluate_custom_field_rule(customer: Customer, config: Dict, score_value: int) -> int:
        """Evaluate custom field rules (for future extensibility)"""
        # This would be implemented based on custom field system
        # For now, return 0
        return 0
    
    @staticmethod
    def _trigger_tier_change_workflows(customer: Customer, customer_score: CustomerScore, user: Optional[User]):
        """Trigger workflows when a customer's score tier changes"""
        if user:
            try:
                # Trigger tier change workflow
                WorkflowEngine.trigger_workflows(
                    trigger_type='score_tier_changed',
                    customer=customer,
                    user=user,
                    context={
                        'new_tier': customer_score.score_tier,
                        'new_score': customer_score.current_score,
                        'previous_tier': customer_score.previous_score,
                        'score_change': customer_score.score_change
                    }
                )
                
                # Trigger qualified lead workflow if applicable
                if customer_score.score_tier == 'qualified':
                    WorkflowEngine.trigger_workflows(
                        trigger_type='qualified_lead',
                        customer=customer,
                        user=user,
                        context={
                            'score': customer_score.current_score,
                            'tier': customer_score.score_tier
                        }
                    )
            except Exception as e:
                logger.error(f"Error triggering tier change workflows: {e}")
    
    @staticmethod
    def bulk_calculate_scores(customer_ids: Optional[List[int]] = None, 
                            user: Optional[User] = None) -> ScoreCalculationLog:
        """Calculate scores for multiple customers"""
        calculation_id = uuid.uuid4()
        
        # Create calculation log
        calc_log = ScoreCalculationLog.objects.create(
            calculation_id=calculation_id,
            calculation_type='full_recalc' if customer_ids is None else 'bulk_update',
            triggered_by=user
        )
        
        try:
            # Get customers to process
            if customer_ids:
                customers = Customer.objects.filter(id__in=customer_ids)
            else:
                customers = Customer.objects.all()
            
            customers_processed = 0
            scores_changed = 0
            tier_changes = 0
            
            # Process each customer
            for customer in customers:
                try:
                    old_score = getattr(customer, 'lead_score', None)
                    old_score_value = old_score.current_score if old_score else 0
                    old_tier = old_score.score_tier if old_score else 'cold'
                    
                    # Calculate new score
                    customer_score = LeadScoringEngine.calculate_customer_score(
                        customer=customer,
                        user=user,
                        force_recalculate=True
                    )
                    
                    customers_processed += 1
                    
                    if customer_score.current_score != old_score_value:
                        scores_changed += 1
                    
                    if customer_score.score_tier != old_tier:
                        tier_changes += 1
                
                except Exception as e:
                    logger.error(f"Error calculating score for customer {customer.pk}: {e}")
                    continue
            
            # Update calculation log
            calc_log.status = 'completed'
            calc_log.completed_at = timezone.now()
            calc_log.customers_processed = customers_processed
            calc_log.scores_changed = scores_changed
            calc_log.tier_changes = tier_changes
            calc_log.execution_time_seconds = (
                calc_log.completed_at - calc_log.started_at
            ).total_seconds() if calc_log.completed_at and calc_log.started_at else 0
            calc_log.save()
            
        except Exception as e:
            calc_log.status = 'failed'
            calc_log.error_message = str(e)
            calc_log.completed_at = timezone.now()
            calc_log.save()
            logger.error(f"Bulk score calculation failed: {e}")
        
        return calc_log
    
    @staticmethod
    def apply_score_decay():
        """Apply score decay based on configuration"""
        config = LeadScoringConfig.get_config()
        
        if not config.enable_score_decay:
            return
        
        # Check if decay should be applied
        if config.last_decay_applied:
            days_since_decay = (timezone.now() - config.last_decay_applied).days
            if days_since_decay < config.decay_frequency_days:
                return
        
        # Apply decay to all customer scores
        decay_factor = 1 - (config.decay_rate_percent / 100)
        
        customer_scores = CustomerScore.objects.all()
        for customer_score in customer_scores:
            old_score = customer_score.current_score
            new_score = int(old_score * decay_factor)
            
            if new_score != old_score:
                customer_score.previous_score = old_score
                customer_score.current_score = new_score
                customer_score.score_change = new_score - old_score
                customer_score.last_change_date = timezone.now()
                customer_score.update_score_tier()
                customer_score.save()
                
                # Create history record
                ScoreHistory.objects.create(
                    customer_score=customer_score,
                    old_score=old_score,
                    new_score=new_score,
                    score_change=new_score - old_score,
                    old_tier=customer_score.score_tier,  # This might have changed
                    new_tier=customer_score.score_tier,
                    change_reason=f"Score decay applied ({config.decay_rate_percent}%)"
                )
        
        # Update last decay date
        config.last_decay_applied = timezone.now()
        config.save()


# Utility functions for triggering score calculations

def trigger_score_calculation_on_event(customer: Customer, event_type: str, user: User):
    """Trigger score calculation when certain events occur"""
    try:
        # Only recalculate for events that might affect scoring
        scoring_events = [
            'customer_created', 'note_added', 'file_uploaded', 'email_opened',
            'email_clicked', 'task_completed', 'task_created'
        ]
        
        if event_type in scoring_events:
            LeadScoringEngine.calculate_customer_score(customer, user)
    
    except Exception as e:
        logger.error(f"Error triggering score calculation for {customer.pk}: {e}")


def get_top_scoring_customers(limit: int = 10, tier: Optional[str] = None):
    """Get top scoring customers"""
    query = CustomerScore.objects.select_related('customer').order_by('-current_score')
    
    if tier:
        query = query.filter(score_tier=tier)
    
    return query[:limit]


def get_recent_score_changes(days: int = 7, limit: int = 20):
    """Get recent score changes"""
    since_date = timezone.now() - timedelta(days=days)
    
    return ScoreHistory.objects.select_related(
        'customer_score__customer'
    ).filter(
        changed_at__gte=since_date
    ).order_by('-changed_at')[:limit]