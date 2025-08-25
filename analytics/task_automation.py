from django.utils import timezone
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.conf import settings
from datetime import timedelta
import logging
from typing import Dict, List, Optional, Any, Union

from customers.models import Customer, CustomerNote, Tag
from .models import (
    WorkflowTemplate, WorkflowAction, WorkflowExecution, ActionExecution,
    Task, Reminder, AnalyticsEvent, EmailTemplate
)
from .email_automation import EmailAutomationEngine

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Core workflow automation engine"""
    
    @staticmethod
    def trigger_workflows(trigger_type: str, customer: Customer, user: User, context: Optional[Dict[str, Any]] = None):
        """Trigger all active workflows for a given trigger type"""
        context = context or {}
        
        # Get active workflows for this trigger type
        workflows = WorkflowTemplate.objects.filter(
            trigger_type=trigger_type,
            is_active=True
        )
        
        triggered_executions = []
        
        for workflow in workflows:
            try:
                # Check if workflow should be triggered based on conditions
                if WorkflowEngine._should_trigger_workflow(workflow, customer, context):
                    execution = WorkflowEngine.start_workflow_execution(workflow, customer, user, context)
                    triggered_executions.append(execution)
            except Exception as e:
                logger.error(f"Error triggering workflow {workflow.name}: {e}")
        
        return triggered_executions
    
    @staticmethod
    def _should_trigger_workflow(workflow: WorkflowTemplate, customer: Customer, context: Dict[str, Any]) -> bool:
        """Check if workflow should be triggered based on conditions"""
        conditions = workflow.trigger_conditions
        
        if not conditions:
            return True  # No conditions means always trigger
        
        try:
            # Check customer conditions
            if 'customer_city' in conditions:
                if customer.city not in conditions['customer_city']:
                    return False
            
            if 'customer_tags' in conditions:
                customer_tags = [tag.name for tag in customer.tags.all()]
                required_tags = conditions['customer_tags']
                if not any(tag in customer_tags for tag in required_tags):
                    return False
            
            # Check context conditions
            if 'note_type' in conditions and 'note_type' in context:
                if context['note_type'] not in conditions['note_type']:
                    return False
            
            # Check execution limits
            if workflow.max_executions:
                execution_count = WorkflowExecution.objects.filter(
                    workflow=workflow,
                    customer=customer,
                    status__in=['completed', 'running']
                ).count()
                
                if execution_count >= workflow.max_executions:
                    return False
            
            return True
        
        except Exception as e:
            logger.error(f"Error checking workflow conditions for {workflow.name}: {e}")
            return False
    
    @staticmethod
    def start_workflow_execution(workflow: WorkflowTemplate, customer: Customer, user: User, context: Optional[Dict[str, Any]] = None) -> WorkflowExecution:
        """Start execution of a workflow"""
        context = context or {}
        
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            customer=customer,
            triggered_by=user,
            status='pending',
            context_data=context,
            execution_log=[{
                'timestamp': timezone.now().isoformat(),
                'action': 'workflow_started',
                'message': f'Workflow {workflow.name} started for {customer.first_name} {customer.last_name}'
            }]
        )
        
        # Start executing actions
        WorkflowEngine._execute_next_action(execution)
        
        # Track analytics event
        AnalyticsEvent.objects.create(
            customer=customer,
            event_type='workflow_triggered',
            user=user,
            metadata={
                'workflow_id': workflow.pk,
                'workflow_name': workflow.name,
                'trigger_type': workflow.trigger_type,
                'execution_id': execution.pk
            }
        )
        
        return execution
    
    @staticmethod
    def _execute_next_action(execution: WorkflowExecution):
        """Execute the next action in the workflow"""
        if execution.status not in ['pending', 'running']:
            return
        
        # Get the next action to execute
        actions = WorkflowAction.objects.filter(
            workflow=execution.workflow,
            action_order__gte=execution.current_action
        ).order_by('action_order')
        
        if not actions.exists():
            # Workflow completed
            execution.status = 'completed'
            execution.completed_at = timezone.now()
            execution.execution_log.append({
                'timestamp': timezone.now().isoformat(),
                'action': 'workflow_completed',
                'message': 'All workflow actions completed successfully'
            })
            execution.save()
            return

        action = actions.first()
        if action is None:
            return
            
        execution.status = 'running'
        execution.current_action = action.action_order
        execution.save()
        
        # Execute the action
        WorkflowEngine._execute_action(execution, action)
    
    @staticmethod
    def _execute_action(execution: WorkflowExecution, action: WorkflowAction):
        """Execute a specific workflow action"""
        action_execution = ActionExecution.objects.create(
            workflow_execution=execution,
            action=action,
            status='running'
        )
        
        try:
            result = None
            
            if action.action_type == 'create_task':
                result = WorkflowEngine._execute_create_task(execution, action)
            elif action.action_type == 'send_email':
                result = WorkflowEngine._execute_send_email(execution, action)
            elif action.action_type == 'add_note':
                result = WorkflowEngine._execute_add_note(execution, action)
            elif action.action_type == 'update_customer':
                result = WorkflowEngine._execute_update_customer(execution, action)
            elif action.action_type == 'send_notification':
                result = WorkflowEngine._execute_send_notification(execution, action)
            elif action.action_type == 'create_reminder':
                result = WorkflowEngine._execute_create_reminder(execution, action)
            elif action.action_type == 'assign_tag':
                result = WorkflowEngine._execute_assign_tag(execution, action)
            elif action.action_type == 'remove_tag':
                result = WorkflowEngine._execute_remove_tag(execution, action)
            elif action.action_type == 'wait':
                result = WorkflowEngine._execute_wait(execution, action)
            else:
                raise ValueError(f"Unknown action type: {action.action_type}")
            
            # Mark action as completed
            action_execution.status = 'completed'
            action_execution.completed_at = timezone.now()
            action_execution.result_data = result or {}
            action_execution.save()
            
            # Log success
            execution.execution_log.append({
                'timestamp': timezone.now().isoformat(),
                'action': action.action_type,
                'message': f'Action {action.action_type} completed successfully',
                'result': result
            })
            execution.save()
            
            # Continue to next action (after delay if specified)
            if action.delay_days or action.delay_hours or action.delay_minutes:
                WorkflowEngine._schedule_next_action(execution, action)
            else:
                execution.current_action += 1
                execution.save()
                WorkflowEngine._execute_next_action(execution)
        
        except Exception as e:
            # Mark action as failed
            action_execution.status = 'failed'
            action_execution.error_message = str(e)
            action_execution.completed_at = timezone.now()
            action_execution.save()
            
            # Log error
            execution.execution_log.append({
                'timestamp': timezone.now().isoformat(),
                'action': action.action_type,
                'message': f'Action {action.action_type} failed: {str(e)}',
                'error': str(e)
            })
            execution.status = 'failed'
            execution.error_message = str(e)
            execution.save()
            
            logger.error(f"Workflow action failed: {e}")
    
    @staticmethod
    def _execute_create_task(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute create task action"""
        config = action.action_config
        
        task = Task.objects.create(
            title=config.get('title', 'Automated Task'),
            description=config.get('description', ''),
            customer=execution.customer,
            created_by=execution.triggered_by,
            assigned_to_id=config.get('assigned_to_id') if config.get('assigned_to_id') else None,
            priority=config.get('priority', 'medium'),
            due_date=timezone.now() + timedelta(days=config.get('due_in_days', 7)),
            workflow_execution=execution,
            is_automated=True,
            tags=config.get('tags', []),
            metadata=config.get('metadata', {})
        )
        
        return {
            'task_id': task.pk,
            'task_title': task.title
        }
    
    @staticmethod
    def _execute_send_email(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute send email action"""
        config = action.action_config
        template_id = config.get('template_id')
        
        if template_id:
            template = EmailTemplate.objects.get(pk=template_id)
            delivery = EmailAutomationEngine.send_template_email(
                customer=execution.customer,
                template=template,
                sent_by=execution.triggered_by
            )
            
            return {
                'delivery_id': delivery.pk,
                'template_name': template.name
            }
        else:
            # Send custom email
            subject = config.get('subject', 'Automated Email')
            message = config.get('message', '')
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[execution.customer.email],
                fail_silently=False
            )
            
            return {
                'subject': subject,
                'recipient': execution.customer.email
            }
    
    @staticmethod
    def _execute_add_note(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute add note action"""
        config = action.action_config
        
        note = CustomerNote.objects.create(
            customer=execution.customer,
            note=config.get('content', 'Automated note'),
            note_type=config.get('note_type', 'general'),
            is_important=config.get('is_important', False),
            created_by=execution.triggered_by
        )
        
        return {
            'note_id': note.pk,
            'note_content': note.note[:50] + '...' if len(note.note) > 50 else note.note
        }
    
    @staticmethod
    def _execute_update_customer(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute update customer action"""
        config = action.action_config
        customer = execution.customer
        
        updated_fields = []
        
        for field_name, field_value in config.get('updates', {}).items():
            if hasattr(customer, field_name):
                setattr(customer, field_name, field_value)
                updated_fields.append(field_name)
        
        if updated_fields:
            customer.save()
        
        return {
            'updated_fields': updated_fields
        }
    
    @staticmethod
    def _execute_send_notification(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute send notification action"""
        config = action.action_config
        
        # In a real app, this would send notifications via email, SMS, or push notifications
        # For now, we'll create a task as a notification
        notification_task = Task.objects.create(
            title=f"Notification: {config.get('title', 'System Notification')}",
            description=config.get('message', ''),
            customer=execution.customer,
            created_by=execution.triggered_by,
            assigned_to_id=config.get('notify_user_id') if config.get('notify_user_id') else execution.triggered_by.pk,
            priority='high',
            workflow_execution=execution,
            is_automated=True
        )
        
        return {
            'notification_task_id': notification_task.pk,
            'notification_title': notification_task.title
        }
    
    @staticmethod
    def _execute_create_reminder(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute create reminder action"""
        config = action.action_config
        
        remind_at = timezone.now() + timedelta(
            days=config.get('remind_in_days', 1),
            hours=config.get('remind_in_hours', 0)
        )
        
        reminder = Reminder.objects.create(
            title=config.get('title', 'Automated Reminder'),
            description=config.get('description', ''),
            customer=execution.customer,
            user_id=config.get('user_id', execution.triggered_by.pk),
            remind_at=remind_at,
            workflow_execution=execution
        )
        
        return {
            'reminder_id': reminder.pk,
            'remind_at': remind_at.isoformat()
        }
    
    @staticmethod
    def _execute_assign_tag(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute assign tag action"""
        config = action.action_config
        tag_names = config.get('tags', [])
        
        assigned_tags = []
        for tag_name in tag_names:
            tag, created = Tag.objects.get_or_create(name=tag_name)
            execution.customer.tags.add(tag)
            assigned_tags.append(tag_name)
        
        return {
            'assigned_tags': assigned_tags
        }
    
    @staticmethod
    def _execute_remove_tag(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute remove tag action"""
        config = action.action_config
        tag_names = config.get('tags', [])
        
        removed_tags = []
        for tag_name in tag_names:
            try:
                tag = Tag.objects.get(name=tag_name)
                execution.customer.tags.remove(tag)
                removed_tags.append(tag_name)
            except Tag.DoesNotExist:
                pass
        
        return {
            'removed_tags': removed_tags
        }
    
    @staticmethod
    def _execute_wait(execution: WorkflowExecution, action: WorkflowAction) -> Dict[str, Any]:
        """Execute wait/delay action"""
        # For immediate execution, we just continue
        # In production, this would schedule the next action
        return {
            'wait_completed': True,
            'delay_days': action.delay_days,
            'delay_hours': action.delay_hours,
            'delay_minutes': action.delay_minutes
        }
    
    @staticmethod
    def _schedule_next_action(execution: WorkflowExecution, action: WorkflowAction):
        """Schedule the next action after a delay"""
        # In production, this would use Celery or another task queue
        # For now, we'll just continue immediately
        execution.current_action += 1
        execution.save()
        WorkflowEngine._execute_next_action(execution)


class TaskManager:
    """Task management utilities"""
    
    @staticmethod
    def create_task(customer: Customer, title: str, description: str = '', 
                   assigned_to: Optional[User] = None, created_by: Optional[User] = None, 
                   priority: str = 'medium', due_date: Optional[timezone.datetime] = None) -> Task:
        """Create a new task"""
        task = Task.objects.create(
            title=title,
            description=description,
            customer=customer,
            assigned_to=assigned_to,
            created_by=created_by or assigned_to,
            priority=priority,
            due_date=due_date
        )
        
        # Track analytics event
        if created_by:
            AnalyticsEvent.objects.create(
                customer=customer,
                event_type='task_created',
                user=created_by,
                metadata={
                    'task_id': task.pk,
                    'task_title': task.title,
                    'priority': task.priority,
                    'assigned_to': assigned_to.username if assigned_to else None
                }
            )
        
        return task
    
    @staticmethod
    def complete_task(task: Task, completed_by: User) -> Task:
        """Mark a task as completed"""
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        
        # Track analytics event
        AnalyticsEvent.objects.create(
            customer=task.customer,
            event_type='task_completed',
            user=completed_by,
            metadata={
                'task_id': task.pk,
                'task_title': task.title,
                'completion_time': task.completed_at.isoformat() if task.completed_at is not None else None
            }
        )
        
        # Trigger workflows for task completion
        WorkflowEngine.trigger_workflows(
            trigger_type='task_completed',
            customer=task.customer,
            user=completed_by,
            context={
                'task_id': task.pk,
                'task_title': task.title,
                'task_priority': task.priority
            }
        )
        
        return task
    
    @staticmethod
    def get_overdue_tasks():
        """Get all overdue tasks"""
        return Task.objects.filter(
            due_date__lt=timezone.now(),
            status__in=['pending', 'in_progress']
        )
    
    @staticmethod
    def get_tasks_due_soon(days: int = 3):
        """Get tasks due within specified days"""
        due_date_threshold = timezone.now() + timedelta(days=days)
        return Task.objects.filter(
            due_date__lte=due_date_threshold,
            due_date__gte=timezone.now(),
            status__in=['pending', 'in_progress']
        )


class ReminderManager:
    """Reminder management utilities"""
    
    @staticmethod
    def process_pending_reminders():
        """Process and send pending reminders"""
        pending_reminders = Reminder.objects.filter(
            remind_at__lte=timezone.now(),
            is_sent=False
        )
        
        processed_count = 0
        
        for reminder in pending_reminders:
            try:
                # Send reminder notification (email, SMS, etc.)
                ReminderManager._send_reminder_notification(reminder)
                
                # Mark as sent
                reminder.is_sent = True
                reminder.sent_at = timezone.now()
                reminder.save()
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Failed to send reminder {reminder.pk}: {e}")
        
        return processed_count
    
    @staticmethod
    def _send_reminder_notification(reminder: Reminder):
        """Send reminder notification"""
        subject = f"Reminder: {reminder.title}"
        message = f"""
        This is a reminder notification:
        
        {reminder.title}
        
        {reminder.description}
        
        Customer: {reminder.customer.first_name if reminder.customer else 'N/A'} {reminder.customer.last_name if reminder.customer else ''} ({reminder.customer.email if reminder.customer else 'N/A'})
        Task: {reminder.task.title if reminder.task else 'N/A'}
        """
        
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reminder.user.email],
            fail_silently=False
        )


# Utility functions for triggering workflows

def trigger_workflow_on_customer_created(customer: Customer, created_by: User):
    """Trigger workflows when a new customer is created"""
    WorkflowEngine.trigger_workflows(
        trigger_type='customer_created',
        customer=customer,
        user=created_by
    )


def trigger_workflow_on_note_added(customer: Customer, added_by: User, note_type: Optional[str] = None):
    """Trigger workflows when a note is added"""
    WorkflowEngine.trigger_workflows(
        trigger_type='note_added',
        customer=customer,
        user=added_by,
        context={'note_type': note_type} if note_type else {}
    )


def trigger_workflow_on_file_uploaded(customer: Customer, uploaded_by: User):
    """Trigger workflows when a file is uploaded"""
    WorkflowEngine.trigger_workflows(
        trigger_type='file_uploaded',
        customer=customer,
        user=uploaded_by
    )