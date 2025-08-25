from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from customers.models import Customer
from decimal import Decimal
import uuid
import json


class AnalyticsEvent(models.Model):
    """Track various events and interactions with customers"""
    EVENT_TYPES = [
        ('created', 'Customer Created'),
        ('updated', 'Customer Updated'),
        ('viewed', 'Customer Viewed'),
        ('note_added', 'Note Added'),
        ('file_uploaded', 'File Uploaded'),
        ('email_sent', 'Email Sent'),
        ('call_made', 'Call Made'),
        ('meeting_scheduled', 'Meeting Scheduled'),
        ('task_completed', 'Task Completed'),
        ('quote_duplicated', 'Quote Duplicated'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='analytics_events')
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES)
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', 'timestamp']),
            models.Index(fields=['event_type', 'timestamp']),
            models.Index(fields=['user', 'timestamp']),
        ]
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.customer.first_name} {self.customer.last_name} - {self.get_event_type_display()}"


class CustomerMetrics(models.Model):
    """Store calculated metrics for customers"""
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='metrics')
    
    # Engagement metrics
    total_interactions = models.IntegerField(default=0)
    last_interaction_date = models.DateTimeField(null=True, blank=True)
    notes_count = models.IntegerField(default=0)
    files_count = models.IntegerField(default=0)
    
    # Scoring metrics
    engagement_score = models.FloatField(default=0.0)
    profile_completeness = models.FloatField(default=0.0)
    lead_score = models.FloatField(default=0.0)
    
    # Timestamps
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['engagement_score']),
            models.Index(fields=['lead_score']),
            models.Index(fields=['last_interaction_date']),
        ]
    
    def __str__(self):
        return f"Metrics for {self.customer.first_name} {self.customer.last_name}"


class DashboardMetric(models.Model):
    """Store dashboard metrics and calculations"""
    METRIC_TYPES = [
        ('total_customers', 'Total Customers'),
        ('new_customers_today', 'New Customers Today'),
        ('new_customers_week', 'New Customers This Week'),
        ('new_customers_month', 'New Customers This Month'),
        ('active_customers', 'Active Customers'),
        ('top_cities', 'Top Cities'),
        ('engagement_rate', 'Engagement Rate'),
        ('avg_profile_completeness', 'Average Profile Completeness'),
    ]
    
    metric_type = models.CharField(max_length=50, choices=METRIC_TYPES, unique=True)
    value = models.JSONField(default=dict)  # Store metric value and metadata
    calculated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['metric_type', 'calculated_at']),
        ]
    
    def __str__(self):
        return f"{self.get_metric_type_display()}: {self.value}"


class Report(models.Model):
    """Saved custom reports"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Report configuration
    report_type = models.CharField(max_length=50, default='customer_list')
    filters = models.JSONField(default=dict)  # Store filter criteria
    fields = models.JSONField(default=list)   # Store selected fields
    grouping = models.JSONField(default=dict) # Store grouping options
    
    # Sharing and scheduling
    is_public = models.BooleanField(default=False)
    is_scheduled = models.BooleanField(default=False)
    schedule_frequency = models.CharField(max_length=20, blank=True)  # daily, weekly, monthly
    last_generated = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['is_scheduled', 'schedule_frequency']),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} by {self.created_by.username}"


class ReportExecution(models.Model):
    """Track report execution history"""
    report = models.ForeignKey(Report, on_delete=models.CASCADE, related_name='executions')
    executed_by = models.ForeignKey(User, on_delete=models.CASCADE)
    executed_at = models.DateTimeField(auto_now_add=True)
    
    # Execution details
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], default='pending')
    
    records_count = models.IntegerField(null=True, blank=True)
    file_path = models.CharField(max_length=500, blank=True)  # Path to generated file
    error_message = models.TextField(blank=True)
    execution_time = models.FloatField(null=True, blank=True)  # Seconds
    
    class Meta:
        indexes = [
            models.Index(fields=['report', 'executed_at']),
            models.Index(fields=['status', 'executed_at']),
        ]
        ordering = ['-executed_at']
    
    def __str__(self):
        return f"{self.report.name} - {self.executed_at.strftime('%Y-%m-%d %H:%M')}"


class EmailTemplate(models.Model):
    """Email templates for automation"""
    name = models.CharField(max_length=200)
    subject = models.CharField(max_length=300)
    content = models.TextField()
    html_content = models.TextField(blank=True)
    
    # Template variables
    available_variables = models.JSONField(default=list)  # List of available variables
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class EmailSequence(models.Model):
    """Email automation sequences"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Trigger conditions
    trigger_type = models.CharField(max_length=50, choices=[
        ('customer_created', 'New Customer Created'),
        ('note_added', 'Note Added'),
        ('file_uploaded', 'File Uploaded'),
        ('manual', 'Manual Trigger'),
    ], default='manual')
    
    class Meta:
        ordering = ['name']
    
    def __str__(self):
        return self.name


class EmailSequenceStep(models.Model):
    """Individual steps in an email sequence"""
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE, related_name='steps')
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE)
    step_number = models.IntegerField()
    delay_days = models.IntegerField(default=0)  # Days to wait before sending
    delay_hours = models.IntegerField(default=0)  # Additional hours to wait
    
    class Meta:
        ordering = ['sequence', 'step_number']
        unique_together = ['sequence', 'step_number']
    
    def __str__(self):
        return f"{self.sequence.name} - Step {self.step_number}"


class EmailDelivery(models.Model):
    """Track email delivery and engagement"""
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    template = models.ForeignKey(EmailTemplate, on_delete=models.CASCADE, null=True, blank=True)
    sequence = models.ForeignKey(EmailSequence, on_delete=models.CASCADE, null=True, blank=True)
    sequence_step = models.ForeignKey(EmailSequenceStep, on_delete=models.CASCADE, null=True, blank=True)
    
    # Email details
    subject = models.CharField(max_length=300)
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Delivery status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('bounced', 'Bounced'),
        ('failed', 'Failed'),
    ], default='pending')
    
    # Engagement tracking
    opened_at = models.DateTimeField(null=True, blank=True)
    clicked_at = models.DateTimeField(null=True, blank=True)
    open_count = models.IntegerField(default=0)
    click_count = models.IntegerField(default=0)
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', 'sent_at']),
            models.Index(fields=['status', 'sent_at']),
            models.Index(fields=['template', 'sent_at']),
        ]
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"Email to {self.customer.first_name} {self.customer.last_name} - {self.subject}"


# Task Automation Models

class WorkflowTemplate(models.Model):
    """Template for automated workflows"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Trigger configuration
    trigger_type = models.CharField(max_length=50, choices=[
        ('customer_created', 'New Customer Created'),
        ('note_added', 'Note Added'),
        ('file_uploaded', 'File Uploaded'),
        ('task_completed', 'Task Completed'),
        ('email_opened', 'Email Opened'),
        ('email_clicked', 'Email Clicked'),
        ('date_based', 'Date/Time Based'),
        ('manual', 'Manual Trigger'),
    ], default='manual')
    
    # Trigger conditions (JSON field for flexibility)
    trigger_conditions = models.JSONField(default=dict, blank=True)
    
    # Workflow settings
    is_repeatable = models.BooleanField(default=False)
    max_executions = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['trigger_type', 'is_active']),
            models.Index(fields=['created_by', 'created_at']),
        ]
    
    def __str__(self):
        return self.name


class WorkflowAction(models.Model):
    """Individual actions within a workflow"""
    workflow = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE, related_name='actions')
    
    ACTION_TYPES = [
        ('create_task', 'Create Task'),
        ('send_email', 'Send Email'),
        ('add_note', 'Add Note'),
        ('update_customer', 'Update Customer'),
        ('send_notification', 'Send Notification'),
        ('trigger_webhook', 'Trigger Webhook'),
        ('create_reminder', 'Create Reminder'),
        ('assign_tag', 'Assign Tag'),
        ('remove_tag', 'Remove Tag'),
        ('wait', 'Wait/Delay'),
    ]
    
    action_type = models.CharField(max_length=50, choices=ACTION_TYPES)
    action_order = models.IntegerField()
    
    # Action configuration (JSON field for flexibility)
    action_config = models.JSONField(default=dict)
    
    # Execution conditions
    condition_logic = models.JSONField(default=dict, blank=True)
    
    # Timing
    delay_days = models.IntegerField(default=0)
    delay_hours = models.IntegerField(default=0)
    delay_minutes = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['workflow', 'action_order']
        unique_together = ['workflow', 'action_order']
    
    def __str__(self):
        return f"{self.workflow.name} - {self.get_action_type_display()} (Step {self.action_order})"


class Task(models.Model):
    """Tasks that can be created automatically or manually"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='tasks')
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tasks')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks')
    
    # Status and priority
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Dates
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Automation tracking
    workflow_execution = models.ForeignKey('WorkflowExecution', on_delete=models.SET_NULL, null=True, blank=True)
    is_automated = models.BooleanField(default=False)
    
    # Additional metadata
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['due_date', 'status']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['is_automated', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.title} - {self.customer.first_name} {self.customer.last_name}"
    
    @property
    def is_overdue(self):
        if self.due_date and self.status not in ['completed', 'cancelled']:
            return timezone.now() > self.due_date
        return False


class WorkflowExecution(models.Model):
    """Track execution of workflow instances"""
    workflow = models.ForeignKey(WorkflowTemplate, on_delete=models.CASCADE)
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    triggered_by = models.ForeignKey(User, on_delete=models.CASCADE)
    
    # Execution tracking
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    current_action = models.IntegerField(default=1)
    
    # Results and context
    context_data = models.JSONField(default=dict, blank=True)
    execution_log = models.JSONField(default=list, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['workflow', 'status']),
            models.Index(fields=['customer', 'started_at']),
            models.Index(fields=['status', 'started_at']),
        ]
    
    def __str__(self):
        return f"{self.workflow.name} for {self.customer.first_name} {self.customer.last_name}"


class ActionExecution(models.Model):
    """Track individual action executions within workflows"""
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.CASCADE, related_name='action_executions')
    action = models.ForeignKey(WorkflowAction, on_delete=models.CASCADE)
    
    # Execution details
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('skipped', 'Skipped'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Results
    result_data = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['workflow_execution', 'action__action_order']
        unique_together = ['workflow_execution', 'action']
    
    def __str__(self):
        return f"{self.action.get_action_type_display()} - {self.workflow_execution}"


class TaskComment(models.Model):
    """Comments on tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Comment on {self.task.title} by {self.author.username}"


class Reminder(models.Model):
    """Reminders for tasks or follow-ups"""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    
    # Target
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='reminders', null=True, blank=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='reminders', null=True, blank=True)
    
    # Assignment
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reminders')
    
    # Timing
    remind_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Status
    is_sent = models.BooleanField(default=False)
    sent_at = models.DateTimeField(null=True, blank=True)
    
    # Automation
    workflow_execution = models.ForeignKey(WorkflowExecution, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['remind_at']
        indexes = [
            models.Index(fields=['user', 'is_sent', 'remind_at']),
            models.Index(fields=['customer', 'remind_at']),
            models.Index(fields=['task', 'remind_at']),
        ]
    
    def __str__(self):
        return f"Reminder: {self.title} for {self.user.username}"


# Lead Scoring Models

class LeadScoringRule(models.Model):
    """Configurable rules for lead scoring"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # Rule configuration
    RULE_TYPES = [
        ('customer_attribute', 'Customer Attribute'),
        ('interaction_count', 'Interaction Count'),
        ('email_engagement', 'Email Engagement'),
        ('task_completion', 'Task Completion'),
        ('file_uploads', 'File Uploads'),
        ('note_frequency', 'Note Frequency'),
        ('time_since_creation', 'Time Since Creation'),
        ('geographic_location', 'Geographic Location'),
        ('tag_presence', 'Tag Presence'),
        ('custom_field', 'Custom Field Value'),
    ]
    
    rule_type = models.CharField(max_length=50, choices=RULE_TYPES)
    condition_config = models.JSONField(default=dict)  # Flexible condition configuration
    
    # Scoring
    score_value = models.IntegerField(help_text="Points to add/subtract when condition is met")
    is_multiplier = models.BooleanField(default=False, help_text="If true, multiply existing score by this value")
    max_score_contribution = models.IntegerField(null=True, blank=True, help_text="Maximum score this rule can contribute")
    
    # Frequency and limits
    evaluation_frequency = models.CharField(max_length=20, choices=[
        ('realtime', 'Real-time (on events)'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
    ], default='realtime')
    
    priority = models.IntegerField(default=0, help_text="Higher priority rules are evaluated first")
    
    class Meta:
        ordering = ['-priority', 'name']
        indexes = [
            models.Index(fields=['rule_type', 'is_active']),
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['evaluation_frequency', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.score_value} points)"


class CustomerScore(models.Model):
    """Customer lead scores with history tracking"""
    customer = models.OneToOneField(Customer, on_delete=models.CASCADE, related_name='lead_score')
    current_score = models.IntegerField(default=0)
    
    # Score categorization
    SCORE_TIERS = [
        ('cold', 'Cold Lead (0-25)'),
        ('warm', 'Warm Lead (26-50)'),
        ('hot', 'Hot Lead (51-75)'),
        ('qualified', 'Qualified Lead (76-100)'),
    ]
    
    score_tier = models.CharField(max_length=20, choices=SCORE_TIERS, default='cold')
    
    # Tracking
    last_calculated = models.DateTimeField(auto_now=True)
    calculation_count = models.IntegerField(default=0)
    
    # Score breakdown
    score_breakdown = models.JSONField(default=dict, help_text="Breakdown of score by rule")
    
    # Historical tracking
    previous_score = models.IntegerField(default=0)
    score_change = models.IntegerField(default=0)
    last_change_date = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-current_score']
        indexes = [
            models.Index(fields=['current_score', 'score_tier']),
            models.Index(fields=['last_calculated']),
            models.Index(fields=['score_tier', 'current_score']),
        ]
    
    def __str__(self):
        return f"{self.customer.first_name} {self.customer.last_name}: {self.current_score} ({self.score_tier})"
    
    def update_score_tier(self):
        """Update the score tier based on current score"""
        if self.current_score <= 25:
            self.score_tier = 'cold'
        elif self.current_score <= 50:
            self.score_tier = 'warm'
        elif self.current_score <= 75:
            self.score_tier = 'hot'
        else:
            self.score_tier = 'qualified'
    
    def get_score_color(self):
        """Get color for score display"""
        colors = {
            'cold': '#6c757d',      # Gray
            'warm': '#ffc107',      # Yellow
            'hot': '#fd7e14',       # Orange
            'qualified': '#28a745', # Green
        }
        return colors.get(self.score_tier, '#6c757d')


class ScoreHistory(models.Model):
    """Historical tracking of score changes"""
    customer_score = models.ForeignKey(CustomerScore, on_delete=models.CASCADE, related_name='history')
    
    # Score change details
    old_score = models.IntegerField()
    new_score = models.IntegerField()
    score_change = models.IntegerField()
    old_tier = models.CharField(max_length=20)
    new_tier = models.CharField(max_length=20)
    
    # Change metadata
    change_reason = models.CharField(max_length=200, blank=True)
    triggered_by_rule = models.ForeignKey(LeadScoringRule, on_delete=models.SET_NULL, null=True, blank=True)
    triggered_by_event = models.ForeignKey(AnalyticsEvent, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Tracking
    changed_at = models.DateTimeField(auto_now_add=True)
    changed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional context
    context_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-changed_at']
        indexes = [
            models.Index(fields=['customer_score', 'changed_at']),
            models.Index(fields=['triggered_by_rule', 'changed_at']),
            models.Index(fields=['new_tier', 'changed_at']),
        ]
    
    def __str__(self):
        return f"{self.customer_score.customer.first_name} {self.customer_score.customer.last_name}: {self.old_score} → {self.new_score}"


class ScoreCalculationLog(models.Model):
    """Log of score calculation runs for debugging and monitoring"""
    calculation_id = models.UUIDField(default=uuid.uuid4, unique=True)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Calculation details
    calculation_type = models.CharField(max_length=20, choices=[
        ('full_recalc', 'Full Recalculation'),
        ('incremental', 'Incremental Update'),
        ('single_customer', 'Single Customer'),
        ('rule_change', 'Rule Change Impact'),
    ], default='incremental')
    
    triggered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    customers_processed = models.IntegerField(default=0)
    rules_applied = models.IntegerField(default=0)
    
    # Results
    STATUS_CHOICES = [
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    error_message = models.TextField(blank=True)
    
    # Performance metrics
    execution_time_seconds = models.FloatField(null=True, blank=True)
    scores_changed = models.IntegerField(default=0)
    tier_changes = models.IntegerField(default=0)
    
    # Detailed results
    results_summary = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['calculation_type', 'started_at']),
            models.Index(fields=['status', 'started_at']),
            models.Index(fields=['triggered_by', 'started_at']),
        ]
    
    def __str__(self):
        return f"Score Calculation {self.calculation_id} - {self.status}"


class LeadScoringConfig(models.Model):
    """Global configuration for lead scoring system"""
    # Score ranges
    min_score = models.IntegerField(default=0)
    max_score = models.IntegerField(default=100)
    
    # Tier thresholds
    cold_threshold = models.IntegerField(default=25)
    warm_threshold = models.IntegerField(default=50)
    hot_threshold = models.IntegerField(default=75)
    
    # Calculation settings
    auto_calculation_enabled = models.BooleanField(default=True)
    calculation_frequency = models.CharField(max_length=20, choices=[
        ('realtime', 'Real-time'),
        ('hourly', 'Hourly'),
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
    ], default='realtime')
    
    # Score decay
    enable_score_decay = models.BooleanField(default=False)
    decay_rate_percent = models.FloatField(default=5.0, help_text="Percentage to decay scores per period")
    decay_frequency_days = models.IntegerField(default=30, help_text="Days between decay applications")
    last_decay_applied = models.DateTimeField(null=True, blank=True)
    
    # Notifications
    notify_on_tier_change = models.BooleanField(default=True)
    notify_on_qualified_lead = models.BooleanField(default=True)
    notification_recipients = models.JSONField(default=list, blank=True)
    
    # System settings
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    updated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = "Lead Scoring Configuration"
        verbose_name_plural = "Lead Scoring Configuration"
    
    def __str__(self):
        return f"Lead Scoring Config (Updated: {self.updated_at.strftime('%Y-%m-%d')})"
    
    @classmethod
    def get_config(cls):
        """Get or create the singleton configuration"""
        config, created = cls.objects.get_or_create(id=1)
        return config


# Quote and Job Management Models

class QuoteRequest(models.Model):
    """Handle quote requests from customers"""
    
    STATUS_CHOICES = [
        ('received', 'Received'),
        ('reviewing', 'Under Review'),
        ('quoted', 'Quote Sent'),
        ('accepted', 'Quote Accepted'),
        ('declined', 'Quote Declined'),
        ('expired', 'Quote Expired'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    SERVICE_TYPES = [
        ('consultation', 'Consultation'),
        ('project', 'Project Work'),
        ('maintenance', 'Maintenance'),
        ('repair', 'Repair'),
        ('installation', 'Installation'),
        ('custom', 'Custom Service'),
        ('other', 'Other'),
    ]
    
    # Basic Information
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='quote_requests')
    reference_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Request Details
    title = models.CharField(max_length=200, help_text="Brief description of the request")
    description = models.TextField(help_text="Detailed description of what's needed")
    service_type = models.CharField(max_length=50, choices=SERVICE_TYPES, default='other')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Status and Timeline
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='received')
    requested_date = models.DateTimeField(auto_now_add=True)
    quote_due_date = models.DateTimeField(null=True, blank=True)
    quote_valid_until = models.DateTimeField(null=True, blank=True)
    
    # Quote Information
    estimated_cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_quote_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quote_notes = models.TextField(blank=True)
    
    # Communication
    original_email_subject = models.CharField(max_length=300, blank=True)
    original_email_body = models.TextField(blank=True)
    auto_response_sent = models.BooleanField(default=False)
    quote_email_sent = models.BooleanField(default=False)
    
    # Assignment and Tracking
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_quotes')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_quotes')
    
    # Metadata
    source = models.CharField(max_length=50, default='email', help_text="How this request was received")
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    quote_sent_at = models.DateTimeField(null=True, blank=True)
    response_received_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['service_type', 'priority']),
            models.Index(fields=['assigned_to', 'status']),
        ]
    
    def __str__(self):
        return f"Quote #{self.reference_number} - {self.customer.full_name} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.reference_number:
            self.reference_number = self.generate_reference_number()
        super().save(*args, **kwargs)
    
    def generate_reference_number(self):
        """Generate unique reference number for quote"""
        import random
        import string
        from django.utils import timezone
        
        date_part = timezone.now().strftime('%Y%m')
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"QT{date_part}{random_part}"
    
    @property
    def is_overdue(self):
        """Check if quote is overdue"""
        if self.quote_due_date and timezone.now() > self.quote_due_date:
            return True
        return False
    
    @property
    def days_since_request(self):
        """Calculate days since request was made"""
        return (timezone.now() - self.requested_date).days


class Job(models.Model):
    """Track jobs/projects from quote to completion"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending Start'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('review', 'Under Review'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    # Basic Information
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='jobs')
    quote_request = models.OneToOneField(QuoteRequest, on_delete=models.SET_NULL, null=True, blank=True, related_name='job')
    job_number = models.CharField(max_length=20, unique=True, blank=True)
    
    # Job Details
    title = models.CharField(max_length=200)
    description = models.TextField()
    service_type = models.CharField(max_length=50, choices=QuoteRequest.SERVICE_TYPES, default='other')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    
    # Status and Timeline
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    start_date = models.DateTimeField(null=True, blank=True)
    due_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    estimated_hours = models.FloatField(null=True, blank=True)
    actual_hours = models.FloatField(null=True, blank=True)
    
    # Financial
    quoted_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    final_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    invoiced_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    
    # Assignment
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_jobs')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_jobs')
    
    # Communication Settings
    send_progress_updates = models.BooleanField(default=True)
    send_completion_notification = models.BooleanField(default=True)
    update_frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('milestone', 'At Milestones'),
        ('manual', 'Manual Only'),
    ], default='weekly')
    
    # Metadata
    notes = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['customer', 'status']),
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['assigned_to', 'status']),
            models.Index(fields=['service_type', 'priority']),
        ]
    
    def __str__(self):
        return f"Job #{self.job_number} - {self.customer.full_name} - {self.title}"
    
    def save(self, *args, **kwargs):
        if not self.job_number:
            self.job_number = self.generate_job_number()
        super().save(*args, **kwargs)
    
    def generate_job_number(self):
        """Generate unique job number"""
        import random
        import string
        from django.utils import timezone
        
        date_part = timezone.now().strftime('%Y%m')
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"JB{date_part}{random_part}"
    
    @property
    def is_overdue(self):
        """Check if job is overdue"""
        if self.due_date and self.status not in ['completed', 'cancelled'] and timezone.now() > self.due_date:
            return True
        return False
    
    @property
    def progress_percentage(self):
        """Calculate job progress based on time elapsed"""
        if not self.start_date or self.status == 'completed':
            return 100 if self.status == 'completed' else 0
        
        if not self.due_date:
            return 50  # Default progress if no due date
        
        total_duration = (self.due_date - self.start_date).total_seconds()
        elapsed_duration = (timezone.now() - self.start_date).total_seconds()
        
        if total_duration <= 0:
            return 100
        
        progress = min((elapsed_duration / total_duration) * 100, 100)
        return max(progress, 0)


class JobUpdate(models.Model):
    """Track progress updates for jobs"""
    
    UPDATE_TYPES = [
        ('progress', 'Progress Update'),
        ('milestone', 'Milestone Reached'),
        ('issue', 'Issue/Problem'),
        ('completion', 'Job Completed'),
        ('on_hold', 'Job On Hold'),
        ('cancelled', 'Job Cancelled'),
    ]
    
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='updates')
    update_type = models.CharField(max_length=20, choices=UPDATE_TYPES, default='progress')
    title = models.CharField(max_length=200)
    description = models.TextField()
    
    # Progress tracking
    hours_worked = models.FloatField(null=True, blank=True)
    percentage_complete = models.IntegerField(null=True, blank=True, help_text="0-100%")
    
    # Communication
    customer_notified = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='job_updates')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['job', 'created_at']),
            models.Index(fields=['update_type', 'created_at']),
        ]
    
    def __str__(self):
        return f"Update for {self.job.job_number}: {self.title}"


class EmailAutoResponse(models.Model):
    """Automated email responses for different scenarios"""
    
    TRIGGER_TYPES = [
        ('quote_request', 'Quote Request Received'),
        ('quote_sent', 'Quote Sent to Customer'),
        ('quote_accepted', 'Quote Accepted'),
        ('job_started', 'Job Started'),
        ('job_progress', 'Job Progress Update'),
        ('job_completed', 'Job Completed'),
        ('job_delayed', 'Job Delayed'),
        ('follow_up', 'Follow-up Required'),
    ]
    
    name = models.CharField(max_length=100)
    trigger_type = models.CharField(max_length=50, choices=TRIGGER_TYPES)
    subject_template = models.CharField(max_length=300)
    body_template = models.TextField()
    
    # Conditions
    service_types = models.JSONField(default=list, blank=True, help_text="Service types this applies to")
    conditions = models.JSONField(default=dict, blank=True, help_text="Additional conditions")
    
    # Settings
    is_active = models.BooleanField(default=True)
    delay_minutes = models.IntegerField(default=0, help_text="Delay before sending (0 = immediate)")
    send_to_customer = models.BooleanField(default=True)
    send_to_team = models.BooleanField(default=False)
    team_recipients = models.JSONField(default=list, blank=True)
    
    # Metadata
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['trigger_type', 'name']
        indexes = [
            models.Index(fields=['trigger_type', 'is_active']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.trigger_type})"
    
    def render_template(self, template_text, context):
        """Render template with context variables"""
        from django.template import Template, Context
        template = Template(template_text)
        return template.render(Context(context))
    
    def get_email_content(self, quote_request=None, job=None, customer=None):
        """Generate email content with proper context"""
        if customer:
            main_customer = customer
        elif quote_request:
            main_customer = quote_request.customer
        elif job:
            main_customer = job.customer
        else:
            main_customer = None
            
        context = {
            'customer': main_customer,
            'quote_request': quote_request,
            'job': job,
            'company_name': 'mAgent CRM',  # Could be configurable
            'date': timezone.now().strftime('%B %d, %Y'),
        }
        
        subject = self.render_template(self.subject_template, context)
        body = self.render_template(self.body_template, context)
        
        return subject, body
