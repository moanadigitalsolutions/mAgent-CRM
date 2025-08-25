#!/usr/bin/env python
"""
Sample data creation script for task automation system
Creates sample workflows, tasks, and executions to demonstrate the system
"""

import os
import sys
import django
from datetime import datetime, timedelta
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'magent.settings')
django.setup()

from django.contrib.auth.models import User
from customers.models import Customer, Tag
from analytics.models import (
    WorkflowTemplate, WorkflowAction, WorkflowExecution, 
    Task, Reminder, AnalyticsEvent
)
from analytics.task_automation import WorkflowEngine


def create_sample_workflows():
    """Create sample workflow templates"""
    print("Creating sample workflow templates...")
    
    # Get admin user
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("No admin user found. Creating admin user...")
        admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='admin123'
        )
    
    # Workflow 1: New Customer Onboarding
    onboarding_workflow, created = WorkflowTemplate.objects.get_or_create(
        name="New Customer Onboarding",
        defaults={
            'description': 'Automated onboarding sequence for new customers',
            'trigger_type': 'customer_created',
            'is_active': True,
            'created_by': admin_user,
            'is_repeatable': False,
            'max_executions': 1
        }
    )
    
    if created:
        # Add actions to onboarding workflow
        WorkflowAction.objects.create(
            workflow=onboarding_workflow,
            action_type='create_task',
            action_order=1,
            action_config={
                'title': 'Welcome Call Scheduled',
                'description': 'Schedule a welcome call with the new customer',
                'priority': 'high',
                'due_in_days': 1
            }
        )
        
        WorkflowAction.objects.create(
            workflow=onboarding_workflow,
            action_type='send_email',
            action_order=2,
            action_config={
                'subject': 'Welcome to our CRM!',
                'message': 'Thank you for joining us. We will be in touch soon!'
            },
            delay_hours=2
        )
        
        WorkflowAction.objects.create(
            workflow=onboarding_workflow,
            action_type='assign_tag',
            action_order=3,
            action_config={
                'tags': ['new-customer', 'onboarding']
            },
            delay_days=1
        )
        
        WorkflowAction.objects.create(
            workflow=onboarding_workflow,
            action_type='create_reminder',
            action_order=4,
            action_config={
                'title': 'Follow up on onboarding',
                'description': 'Check how onboarding process is going',
                'remind_in_days': 7
            },
            delay_days=7
        )
    
    # Workflow 2: Follow-up Sequence
    followup_workflow, created = WorkflowTemplate.objects.get_or_create(
        name="Customer Follow-up Sequence",
        defaults={
            'description': 'Follow-up sequence after customer interaction',
            'trigger_type': 'note_added',
            'is_active': True,
            'created_by': admin_user,
            'is_repeatable': True,
            'trigger_conditions': {
                'note_type': ['meeting', 'call', 'demo']
            }
        }
    )
    
    if created:
        WorkflowAction.objects.create(
            workflow=followup_workflow,
            action_type='create_task',
            action_order=1,
            action_config={
                'title': 'Send follow-up email',
                'description': 'Send follow-up email based on the interaction',
                'priority': 'medium',
                'due_in_days': 2
            },
            delay_days=1
        )
        
        WorkflowAction.objects.create(
            workflow=followup_workflow,
            action_type='add_note',
            action_order=2,
            action_config={
                'content': 'Automated follow-up sequence triggered',
                'note_type': 'system',
                'is_important': False
            }
        )
    
    # Workflow 3: High-Value Customer Care
    vip_workflow, created = WorkflowTemplate.objects.get_or_create(
        name="VIP Customer Care",
        defaults={
            'description': 'Special care workflow for VIP customers',
            'trigger_type': 'manual',
            'is_active': True,
            'created_by': admin_user,
            'trigger_conditions': {
                'customer_tags': ['vip', 'high-value']
            }
        }
    )
    
    if created:
        WorkflowAction.objects.create(
            workflow=vip_workflow,
            action_type='create_task',
            action_order=1,
            action_config={
                'title': 'VIP Customer Check-in',
                'description': 'Personal check-in call with VIP customer',
                'priority': 'urgent',
                'due_in_days': 1
            }
        )
        
        WorkflowAction.objects.create(
            workflow=vip_workflow,
            action_type='send_notification',
            action_order=2,
            action_config={
                'title': 'VIP Customer Activity',
                'message': 'VIP customer workflow has been triggered'
            }
        )
        
        WorkflowAction.objects.create(
            workflow=vip_workflow,
            action_type='create_reminder',
            action_order=3,
            action_config={
                'title': 'VIP Customer Monthly Review',
                'description': 'Schedule monthly business review',
                'remind_in_days': 30
            }
        )
    
    print(f"Created/verified {WorkflowTemplate.objects.count()} workflow templates")
    return [onboarding_workflow, followup_workflow, vip_workflow]


def create_sample_tasks():
    """Create sample tasks"""
    print("Creating sample tasks...")
    
    # Get users and customers
    users = list(User.objects.all()[:3])
    customers = list(Customer.objects.all()[:5])
    
    if not users or not customers:
        print("Need users and customers to create tasks. Run main sample data creation first.")
        return
    
    # Sample tasks with different statuses and priorities
    sample_tasks = [
        {
            'title': 'Welcome call for new customer',
            'description': 'Schedule and complete welcome call to introduce our services',
            'customer': customers[0],
            'assigned_to': users[0],
            'created_by': users[0],
            'priority': 'high',
            'status': 'pending',
            'due_date': timezone.now() + timedelta(days=1),
        },
        {
            'title': 'Follow up on demo request',
            'description': 'Customer requested a product demo, schedule and prepare',
            'customer': customers[1],
            'assigned_to': users[1] if len(users) > 1 else users[0],
            'created_by': users[0],
            'priority': 'medium',
            'status': 'in_progress',
            'due_date': timezone.now() + timedelta(days=3),
        },
        {
            'title': 'Prepare quarterly business review',
            'description': 'Prepare presentation and agenda for quarterly review meeting',
            'customer': customers[2],
            'assigned_to': users[0],
            'created_by': users[0],
            'priority': 'medium',
            'status': 'pending',
            'due_date': timezone.now() + timedelta(days=7),
        },
        {
            'title': 'Resolve billing inquiry',
            'description': 'Customer has questions about their recent invoice',
            'customer': customers[0],
            'assigned_to': users[1] if len(users) > 1 else users[0],
            'created_by': users[0],
            'priority': 'urgent',
            'status': 'pending',
            'due_date': timezone.now() + timedelta(hours=4),
        },
        {
            'title': 'Send product update email',
            'description': 'Send information about new features and updates',
            'customer': customers[3],
            'assigned_to': users[0],
            'created_by': users[0],
            'priority': 'low',
            'status': 'completed',
            'due_date': timezone.now() - timedelta(days=2),
            'completed_at': timezone.now() - timedelta(days=1),
        },
        {
            'title': 'Contract renewal discussion',
            'description': 'Discuss contract renewal options and pricing',
            'customer': customers[4],
            'assigned_to': users[2] if len(users) > 2 else users[0],
            'created_by': users[0],
            'priority': 'high',
            'status': 'pending',
            'due_date': timezone.now() + timedelta(days=14),
        },
        # Overdue task
        {
            'title': 'Update customer profile',
            'description': 'Update customer information based on recent conversation',
            'customer': customers[1],
            'assigned_to': users[0],
            'created_by': users[0],
            'priority': 'medium',
            'status': 'pending',
            'due_date': timezone.now() - timedelta(days=3),
        },
    ]
    
    created_count = 0
    for task_data in sample_tasks:
        task, created = Task.objects.get_or_create(
            title=task_data['title'],
            customer=task_data['customer'],
            defaults=task_data
        )
        if created:
            created_count += 1
            
            # Add some tags
            if 'welcome' in task.title.lower():
                task.tags = ['onboarding', 'welcome']
            elif 'demo' in task.title.lower():
                task.tags = ['demo', 'sales']
            elif 'billing' in task.title.lower():
                task.tags = ['billing', 'support']
            elif 'contract' in task.title.lower():
                task.tags = ['contract', 'renewal']
            else:
                task.tags = ['general']
            task.save()
    
    print(f"Created {created_count} new tasks")


def create_sample_reminders():
    """Create sample reminders"""
    print("Creating sample reminders...")
    
    users = list(User.objects.all()[:2])
    customers = list(Customer.objects.all()[:3])
    
    if not users or not customers:
        print("Need users and customers to create reminders.")
        return
    
    sample_reminders = [
        {
            'title': 'Follow up on proposal',
            'description': 'Check if customer has reviewed the proposal sent last week',
            'customer': customers[0],
            'user': users[0],
            'remind_at': timezone.now() + timedelta(days=2),
        },
        {
            'title': 'Quarterly check-in call',
            'description': 'Schedule quarterly business review call',
            'customer': customers[1],
            'user': users[0],
            'remind_at': timezone.now() + timedelta(days=30),
        },
        {
            'title': 'Contract expiration reminder',
            'description': 'Customer contract expires in 60 days, start renewal process',
            'customer': customers[2],
            'user': users[1] if len(users) > 1 else users[0],
            'remind_at': timezone.now() + timedelta(days=60),
        },
    ]
    
    created_count = 0
    for reminder_data in sample_reminders:
        reminder, created = Reminder.objects.get_or_create(
            title=reminder_data['title'],
            customer=reminder_data['customer'],
            defaults=reminder_data
        )
        if created:
            created_count += 1
    
    print(f"Created {created_count} new reminders")


def create_sample_workflow_executions():
    """Create sample workflow executions"""
    print("Creating sample workflow executions...")
    
    workflows = list(WorkflowTemplate.objects.all())
    customers = list(Customer.objects.all()[:3])
    users = list(User.objects.all()[:1])
    
    if not workflows or not customers or not users:
        print("Need workflows, customers, and users to create executions.")
        return
    
    created_count = 0
    
    # Create a few successful executions
    for i, customer in enumerate(customers[:2]):
        workflow = workflows[i % len(workflows)]
        
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            customer=customer,
            triggered_by=users[0],
            status='completed',
            started_at=timezone.now() - timedelta(days=i+1),
            completed_at=timezone.now() - timedelta(days=i),
            context_data={'test': True},
            execution_log=[
                {
                    'timestamp': (timezone.now() - timedelta(days=i+1)).isoformat(),
                    'action': 'workflow_started',
                    'message': f'Workflow {workflow.name} started for {customer.first_name} {customer.last_name}'
                },
                {
                    'timestamp': (timezone.now() - timedelta(days=i)).isoformat(),
                    'action': 'workflow_completed',
                    'message': 'All workflow actions completed successfully'
                }
            ]
        )
        created_count += 1
        
        # Create some action executions
        from analytics.models import ActionExecution, WorkflowAction
        actions = WorkflowAction.objects.filter(workflow=workflow)
        for action in actions:
            ActionExecution.objects.create(
                workflow_execution=execution,
                action=action,
                status='completed',
                started_at=execution.started_at + timedelta(minutes=action.action_order * 30),
                completed_at=execution.started_at + timedelta(minutes=action.action_order * 30 + 15),
                result_data={'success': True}
            )
    
    # Create one failed execution
    if len(customers) > 2:
        workflow = workflows[0]
        execution = WorkflowExecution.objects.create(
            workflow=workflow,
            customer=customers[2],
            triggered_by=users[0],
            status='failed',
            started_at=timezone.now() - timedelta(hours=6),
            context_data={'test': True},
            error_message='Email sending failed',
            execution_log=[
                {
                    'timestamp': (timezone.now() - timedelta(hours=6)).isoformat(),
                    'action': 'workflow_started',
                    'message': f'Workflow {workflow.name} started for {customers[2].first_name} {customers[2].last_name}'
                },
                {
                    'timestamp': (timezone.now() - timedelta(hours=5)).isoformat(),
                    'action': 'send_email',
                    'message': 'Email sending failed: SMTP server error',
                    'error': 'SMTP server error'
                }
            ]
        )
        created_count += 1
    
    print(f"Created {created_count} workflow executions")


def create_sample_analytics_events():
    """Create sample analytics events for task automation"""
    print("Creating sample analytics events...")
    
    users = list(User.objects.all()[:2])
    customers = list(Customer.objects.all()[:3])
    tasks = list(Task.objects.filter(status='completed')[:2])
    
    if not users or not customers:
        print("Need users and customers to create analytics events.")
        return
    
    created_count = 0
    
    # Task creation events
    for customer in customers:
        event, created = AnalyticsEvent.objects.get_or_create(
            customer=customer,
            event_type='task_created',
            user=users[0],
            timestamp=timezone.now() - timedelta(days=2),
            defaults={
                'metadata': {
                    'task_title': 'Sample Task',
                    'priority': 'medium'
                }
            }
        )
        if created:
            created_count += 1
    
    # Task completion events
    for task in tasks:
        event, created = AnalyticsEvent.objects.get_or_create(
            customer=task.customer,
            event_type='task_completed',
            user=users[0],
            timestamp=timezone.now() - timedelta(days=1),
            defaults={
                'metadata': {
                    'task_id': task.pk,
                    'task_title': task.title,
                    'completion_time': task.completed_at.isoformat() if task.completed_at else None
                }
            }
        )
        if created:
            created_count += 1
    
    # Workflow triggered events
    workflows = list(WorkflowTemplate.objects.all()[:2])
    for workflow in workflows:
        for customer in customers[:2]:
            event, created = AnalyticsEvent.objects.get_or_create(
                customer=customer,
                event_type='workflow_triggered',
                user=users[0],
                timestamp=timezone.now() - timedelta(hours=12),
                defaults={
                    'metadata': {
                        'workflow_id': workflow.pk,
                        'workflow_name': workflow.name,
                        'trigger_type': workflow.trigger_type
                    }
                }
            )
            if created:
                created_count += 1
    
    print(f"Created {created_count} analytics events")


def main():
    """Main function to create all sample data"""
    print("Creating sample data for task automation system...")
    print("=" * 50)
    
    try:
        workflows = create_sample_workflows()
        create_sample_tasks()
        create_sample_reminders()
        create_sample_workflow_executions()
        create_sample_analytics_events()
        
        print("=" * 50)
        print("Sample data creation completed successfully!")
        print("\nSummary:")
        print(f"- Workflow Templates: {WorkflowTemplate.objects.count()}")
        print(f"- Workflow Actions: {WorkflowAction.objects.count()}")
        print(f"- Tasks: {Task.objects.count()}")
        print(f"- Workflow Executions: {WorkflowExecution.objects.count()}")
        print(f"- Reminders: {Reminder.objects.count()}")
        print(f"- Analytics Events: {AnalyticsEvent.objects.count()}")
        
        print(f"\nYou can now visit:")
        print("- Task Dashboard: http://127.0.0.1:8000/analytics/tasks/")
        print("- Workflow List: http://127.0.0.1:8000/analytics/workflows/")
        print("- Task List: http://127.0.0.1:8000/analytics/tasks/list/")
        print("- Task Analytics: http://127.0.0.1:8000/analytics/tasks/analytics/")
        
    except Exception as e:
        print(f"Error creating sample data: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()