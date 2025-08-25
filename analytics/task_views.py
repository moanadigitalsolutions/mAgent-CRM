from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from datetime import timedelta, datetime
import json

from customers.models import Customer
from .models import (
    WorkflowTemplate, WorkflowAction, WorkflowExecution, Task, 
    Reminder, AnalyticsEvent
)
from .task_automation import WorkflowEngine, TaskManager


@login_required
def task_dashboard(request):
    """Task automation dashboard"""
    # Get user's assigned tasks
    assigned_tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')[:10]
    
    # Get recent workflow executions
    recent_executions = WorkflowExecution.objects.order_by('-started_at')[:10]
    
    # Get overdue tasks
    overdue_tasks = TaskManager.get_overdue_tasks()[:5]
    
    # Get tasks due soon
    upcoming_tasks = TaskManager.get_tasks_due_soon()[:5]
    
    # Task statistics
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='completed').count()
    overdue_count = TaskManager.get_overdue_tasks().count()
    
    # Workflow statistics
    active_workflows = WorkflowTemplate.objects.filter(is_active=True).count()
    total_executions = WorkflowExecution.objects.count()
    successful_executions = WorkflowExecution.objects.filter(status='completed').count()
    
    context = {
        'assigned_tasks': assigned_tasks,
        'recent_executions': recent_executions,
        'overdue_tasks': overdue_tasks,
        'upcoming_tasks': upcoming_tasks,
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'overdue_count': overdue_count,
        'active_workflows': active_workflows,
        'total_executions': total_executions,
        'successful_executions': successful_executions,
        'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
        'success_rate': round((successful_executions / total_executions * 100) if total_executions > 0 else 0, 1),
    }
    
    return render(request, 'analytics/task_dashboard.html', context)


@login_required
def workflow_list(request):
    """List all workflow templates"""
    workflows = WorkflowTemplate.objects.annotate(
        execution_count=Count('workflowexecution'),
        success_count=Count('workflowexecution', filter=Q(workflowexecution__status='completed'))
    ).order_by('-created_at')
    
    paginator = Paginator(workflows, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'workflows': page_obj.object_list,
    }
    
    return render(request, 'analytics/workflow_list.html', context)


@login_required
def workflow_detail(request, pk):
    """Workflow template detail view"""
    workflow = get_object_or_404(WorkflowTemplate, pk=pk)
    
    # Get workflow actions
    actions = workflow.actions.all().order_by('action_order')
    
    # Get recent executions
    executions = workflow.workflowexecution_set.order_by('-started_at')[:20]
    
    # Execution statistics
    total_executions = workflow.workflowexecution_set.count()
    successful_executions = workflow.workflowexecution_set.filter(status='completed').count()
    failed_executions = workflow.workflowexecution_set.filter(status='failed').count()
    
    context = {
        'workflow': workflow,
        'actions': actions,
        'executions': executions,
        'total_executions': total_executions,
        'successful_executions': successful_executions,
        'failed_executions': failed_executions,
        'success_rate': round((successful_executions / total_executions * 100) if total_executions > 0 else 0, 1),
    }
    
    return render(request, 'analytics/workflow_detail.html', context)


@login_required
def workflow_create(request):
    """Create new workflow template"""
    if request.method == 'POST':
        form = WorkflowTemplateForm(request.POST)
        if form.is_valid():
            workflow = form.save(commit=False)
            workflow.created_by = request.user
            workflow.save()
            messages.success(request, f'Workflow "{workflow.name}" created successfully!')
            return redirect('analytics:workflow_detail', pk=workflow.pk)
    else:
        form = WorkflowTemplateForm()
    
    context = {
        'form': form,
        'title': 'Create Workflow'
    }
    
    return render(request, 'analytics/workflow_form.html', context)


@login_required
def workflow_edit(request, pk):
    """Edit workflow template"""
    workflow = get_object_or_404(WorkflowTemplate, pk=pk)
    
    if request.method == 'POST':
        form = WorkflowTemplateForm(request.POST, instance=workflow)
        if form.is_valid():
            form.save()
            messages.success(request, f'Workflow "{workflow.name}" updated successfully!')
            return redirect('analytics:workflow_detail', pk=workflow.pk)
    else:
        form = WorkflowTemplateForm(instance=workflow)
    
    context = {
        'form': form,
        'workflow': workflow,
        'title': 'Edit Workflow'
    }
    
    return render(request, 'analytics/workflow_form.html', context)


@login_required
def workflow_toggle_active(request, pk):
    """Toggle workflow active status"""
    workflow = get_object_or_404(WorkflowTemplate, pk=pk)
    workflow.is_active = not workflow.is_active
    workflow.save()
    
    status = 'activated' if workflow.is_active else 'deactivated'
    messages.success(request, f'Workflow "{workflow.name}" {status}!')
    
    return redirect('analytics:workflow_detail', pk=workflow.pk)


@login_required
def workflow_action_create(request, workflow_pk):
    """Create new workflow action"""
    workflow = get_object_or_404(WorkflowTemplate, pk=workflow_pk)
    
    if request.method == 'POST':
        form = WorkflowActionForm(request.POST)
        if form.is_valid():
            action = form.save(commit=False)
            action.workflow = workflow
            
            # Set action order
            last_action = workflow.actions.order_by('-action_order').first()
            action.action_order = (last_action.action_order + 1) if last_action else 1
            
            action.save()
            messages.success(request, 'Action added to workflow!')
            return redirect('analytics:workflow_detail', pk=workflow.pk)
    else:
        form = WorkflowActionForm()
    
    context = {
        'form': form,
        'workflow': workflow,
        'title': 'Add Action'
    }
    
    return render(request, 'analytics/workflow_action_form.html', context)


@login_required
def workflow_execute_manual(request, pk):
    """Manually execute workflow for a customer"""
    workflow = get_object_or_404(WorkflowTemplate, pk=pk)
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        try:
            customer = Customer.objects.get(pk=customer_id)
            execution = WorkflowEngine.start_workflow_execution(
                workflow=workflow,
                customer=customer,
                user=request.user
            )
            messages.success(request, f'Workflow started for {customer.first_name} {customer.last_name}!')
            return redirect('analytics:workflow_execution_detail', pk=execution.pk)
        except Customer.DoesNotExist:
            messages.error(request, 'Customer not found!')
    
    # Get recent customers for selection
    customers = Customer.objects.order_by('-created_at')[:20]
    
    context = {
        'workflow': workflow,
        'customers': customers,
    }
    
    return render(request, 'analytics/workflow_execute_manual.html', context)


@login_required
def workflow_execution_detail(request, pk):
    """Workflow execution detail view"""
    execution = get_object_or_404(WorkflowExecution, pk=pk)
    
    # Get action executions
    action_executions = execution.action_executions.order_by('started_at')
    
    context = {
        'execution': execution,
        'action_executions': action_executions,
    }
    
    return render(request, 'analytics/workflow_execution_detail.html', context)


@login_required
def task_list(request):
    """List all tasks with filtering"""
    tasks = Task.objects.select_related('customer', 'assigned_to', 'created_by').order_by('-created_at')
    
    # Apply filters
    filter_form = TaskFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data.get('status'):
            tasks = tasks.filter(status=filter_form.cleaned_data['status'])
        
        if filter_form.cleaned_data.get('priority'):
            tasks = tasks.filter(priority=filter_form.cleaned_data['priority'])
        
        if filter_form.cleaned_data.get('assigned_to'):
            tasks = tasks.filter(assigned_to=filter_form.cleaned_data['assigned_to'])
        
        if filter_form.cleaned_data.get('customer'):
            tasks = tasks.filter(customer=filter_form.cleaned_data['customer'])
        
        if filter_form.cleaned_data.get('overdue_only'):
            tasks = tasks.filter(due_date__lt=timezone.now(), status__in=['pending', 'in_progress'])
        
        if filter_form.cleaned_data.get('due_soon_only'):
            due_soon = timezone.now() + timedelta(days=3)
            tasks = tasks.filter(due_date__lte=due_soon, due_date__gte=timezone.now())
    
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'tasks': page_obj.object_list,
        'filter_form': filter_form,
    }
    
    return render(request, 'analytics/task_list.html', context)


@login_required
def task_detail(request, pk):
    """Task detail view"""
    task = get_object_or_404(Task, pk=pk)
    
    # Get task comments
    comments = task.comments.order_by('-created_at')
    
    context = {
        'task': task,
        'comments': comments,
    }
    
    return render(request, 'analytics/task_detail.html', context)


@login_required
def task_create(request):
    """Create new task"""
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            task.save()
            
            # Save tags
            if form.cleaned_data.get('tags'):
                task.tags = form.cleaned_data['tags']
                task.save()
            
            messages.success(request, f'Task "{task.title}" created successfully!')
            return redirect('analytics:task_detail', pk=task.pk)
    else:
        form = TaskForm()
        
        # Pre-fill customer if provided
        customer_id = request.GET.get('customer')
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                form.fields['customer'].initial = customer
            except Customer.DoesNotExist:
                pass
    
    context = {
        'form': form,
        'title': 'Create Task'
    }
    
    return render(request, 'analytics/task_form.html', context)


@login_required
def task_edit(request, pk):
    """Edit task"""
    task = get_object_or_404(Task, pk=pk)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save()
            
            # Save tags
            if form.cleaned_data.get('tags'):
                task.tags = form.cleaned_data['tags']
                task.save()
            
            messages.success(request, f'Task "{task.title}" updated successfully!')
            return redirect('analytics:task_detail', pk=task.pk)
    else:
        form = TaskForm(instance=task)
        # Pre-fill tags
        form.fields['tags'].initial = task.tags
    
    context = {
        'form': form,
        'task': task,
        'title': 'Edit Task'
    }
    
    return render(request, 'analytics/task_form.html', context)


@login_required
def task_complete(request, pk):
    """Mark task as completed"""
    task = get_object_or_404(Task, pk=pk)
    
    if task.status != 'completed':
        TaskManager.complete_task(task, request.user)
        messages.success(request, f'Task "{task.title}" marked as completed!')
    else:
        messages.info(request, 'Task is already completed.')
    
    return redirect('analytics:task_detail', pk=task.pk)


@login_required
def task_analytics(request):
    """Task analytics and reporting"""
    # Task completion analytics
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='completed').count()
    pending_tasks = Task.objects.filter(status='pending').count()
    in_progress_tasks = Task.objects.filter(status='in_progress').count()
    
    # Overdue tasks
    overdue_tasks = TaskManager.get_overdue_tasks().count()
    
    # Average completion time
    completed_with_times = Task.objects.filter(
        status='completed',
        completed_at__isnull=False
    )
    
    avg_completion_time = None
    if completed_with_times.exists():
        total_time = sum([
            (task.completed_at - task.created_at).total_seconds() 
            for task in completed_with_times
        ])
        avg_completion_time = total_time / completed_with_times.count() / 3600  # Convert to hours
    
    # Task distribution by priority
    priority_stats = Task.objects.values('priority').annotate(count=Count('id'))
    
    # Task distribution by assigned user
    user_stats = Task.objects.values('assigned_to__username').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    # Recent task trends (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_tasks = Task.objects.filter(created_at__gte=thirty_days_ago)
    
    # Daily task creation for charts
    task_creation_data = []
    for i in range(30):
        date = timezone.now().date() - timedelta(days=i)
        count = recent_tasks.filter(created_at__date=date).count()
        task_creation_data.append({
            'date': date.strftime('%Y-%m-%d'),
            'count': count
        })
    
    context = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
        'avg_completion_time': round(avg_completion_time, 1) if avg_completion_time else None,
        'priority_stats': list(priority_stats),
        'user_stats': list(user_stats),
        'task_creation_data': json.dumps(task_creation_data),
    }
    
    return render(request, 'analytics/task_analytics.html', context)


@login_required
def reminder_list(request):
    """List all reminders"""
    reminders = Reminder.objects.select_related('customer', 'user').order_by('-remind_at')
    
    # Filter options
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'pending':
        reminders = reminders.filter(is_sent=False, remind_at__lte=timezone.now())
    elif filter_type == 'upcoming':
        reminders = reminders.filter(is_sent=False, remind_at__gt=timezone.now())
    elif filter_type == 'sent':
        reminders = reminders.filter(is_sent=True)
    
    paginator = Paginator(reminders, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'reminders': page_obj.object_list,
        'filter_type': filter_type,
    }
    
    return render(request, 'analytics/reminder_list.html', context)


@login_required
def reminder_create(request):
    """Create new reminder"""
    if request.method == 'POST':
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = request.user
            reminder.save()
            messages.success(request, 'Reminder created successfully!')
            return redirect('analytics:reminder_list')
    else:
        form = ReminderForm()
        
        # Pre-fill customer and task if provided
        customer_id = request.GET.get('customer')
        task_id = request.GET.get('task')
        
        if customer_id:
            try:
                customer = Customer.objects.get(pk=customer_id)
                form.fields['customer'].initial = customer
            except Customer.DoesNotExist:
                pass
        
        if task_id:
            try:
                task = Task.objects.get(pk=task_id)
                form.fields['task'].initial = task
                if not customer_id:
                    form.fields['customer'].initial = task.customer
            except Task.DoesNotExist:
                pass
    
    context = {
        'form': form,
        'title': 'Create Reminder'
    }
    
    return render(request, 'analytics/reminder_form.html', context)


# AJAX Views

@login_required
def task_status_update(request):
    """AJAX view to update task status"""
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        new_status = request.POST.get('status')
        
        try:
            task = Task.objects.get(pk=task_id)
            
            if new_status == 'completed' and task.status != 'completed':
                TaskManager.complete_task(task, request.user)
            else:
                task.status = new_status
                task.save()
            
            return JsonResponse({'success': True, 'message': 'Task status updated!'})
        
        except Task.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Task not found!'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request!'})


@login_required
def workflow_analytics_data(request):
    """AJAX view to get workflow analytics data"""
    workflows = WorkflowTemplate.objects.annotate(
        execution_count=Count('workflowexecution'),
        success_count=Count('workflowexecution', filter=Q(workflowexecution__status='completed')),
        failure_count=Count('workflowexecution', filter=Q(workflowexecution__status='failed'))
    )
    
    data = []
    for workflow in workflows:
        success_rate = 0
        if workflow.execution_count > 0:
            success_rate = (workflow.success_count / workflow.execution_count) * 100
        
        data.append({
            'name': workflow.name,
            'executions': workflow.execution_count,
            'success_rate': round(success_rate, 1),
            'success_count': workflow.success_count,
            'failure_count': workflow.failure_count,
        })
    
    return JsonResponse({'workflows': data})