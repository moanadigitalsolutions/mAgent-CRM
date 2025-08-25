from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.db.models import Q, Count
from datetime import timedelta

from customers.models import Customer
from .models import WorkflowTemplate, WorkflowExecution, Task, Reminder
from .task_automation import TaskManager


@login_required
def task_dashboard(request):
    """Simple task automation dashboard"""
    # Get user's assigned tasks
    assigned_tasks = Task.objects.filter(assigned_to=request.user).order_by('-created_at')[:10]
    
    # Get recent workflow executions
    recent_executions = WorkflowExecution.objects.order_by('-started_at')[:10]
    
    # Get overdue tasks
    overdue_tasks = Task.objects.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).order_by('due_date')[:5]
    
    # Get tasks due soon
    due_soon = timezone.now() + timedelta(days=3)
    upcoming_tasks = Task.objects.filter(
        due_date__lte=due_soon,
        due_date__gte=timezone.now(),
        status__in=['pending', 'in_progress']
    ).order_by('due_date')[:5]
    
    # Task statistics
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='completed').count()
    overdue_count = Task.objects.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
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
def task_list(request):
    """List all tasks"""
    tasks = Task.objects.select_related('customer', 'assigned_to', 'created_by').order_by('-created_at')
    
    # Simple filtering
    status_filter = request.GET.get('status')
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    priority_filter = request.GET.get('priority')
    if priority_filter:
        tasks = tasks.filter(priority=priority_filter)
    
    paginator = Paginator(tasks, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'tasks': page_obj.object_list,
        'status_filter': status_filter,
        'priority_filter': priority_filter,
    }
    
    return render(request, 'analytics/task_list.html', context)


@login_required
def task_detail(request, pk):
    """Task detail view"""
    task = get_object_or_404(Task, pk=pk)
    
    context = {
        'task': task,
    }
    
    return render(request, 'analytics/task_detail.html', context)


@login_required
def task_create(request):
    """Create new task (simple form)"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        customer_id = request.POST.get('customer_id')
        assigned_to_id = request.POST.get('assigned_to_id')
        priority = request.POST.get('priority', 'medium')
        due_date_str = request.POST.get('due_date')
        
        try:
            customer = Customer.objects.get(pk=customer_id)
            assigned_to = None
            if assigned_to_id:
                from django.contrib.auth.models import User
                assigned_to = User.objects.get(pk=assigned_to_id)
            
            due_date = None
            if due_date_str:
                from datetime import datetime
                due_date = datetime.fromisoformat(due_date_str.replace('Z', '+00:00'))
            
            task = Task.objects.create(
                title=title,
                description=description,
                customer=customer,
                assigned_to=assigned_to,
                created_by=request.user,
                priority=priority,
                due_date=due_date
            )
            
            messages.success(request, f'Task "{task.title}" created successfully!')
            return redirect('analytics:task_detail', pk=task.pk)
            
        except (Customer.DoesNotExist, ValueError) as e:
            messages.error(request, f'Error creating task: {str(e)}')
    
    # Get customers and users for form
    customers = Customer.objects.all().order_by('first_name', 'last_name')
    from django.contrib.auth.models import User
    users = User.objects.filter(is_active=True).order_by('first_name', 'last_name')
    
    context = {
        'customers': customers,
        'users': users,
    }
    
    return render(request, 'analytics/task_create.html', context)


@login_required
def task_complete(request, pk):
    """Mark task as completed"""
    task = get_object_or_404(Task, pk=pk)
    
    if task.status != 'completed':
        task.status = 'completed'
        task.completed_at = timezone.now()
        task.save()
        messages.success(request, f'Task "{task.title}" marked as completed!')
    else:
        messages.info(request, 'Task is already completed.')
    
    return redirect('analytics:task_detail', pk=task.pk)


@login_required
def workflow_list(request):
    """List all workflow templates"""
    workflows = WorkflowTemplate.objects.order_by('-created_at')
    
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
    
    # Get workflow actions using direct query
    from .models import WorkflowAction
    actions = WorkflowAction.objects.filter(workflow=workflow).order_by('action_order')
    
    # Get recent executions
    executions = WorkflowExecution.objects.filter(workflow=workflow).order_by('-started_at')[:20]
    
    # Execution statistics
    total_executions = WorkflowExecution.objects.filter(workflow=workflow).count()
    successful_executions = WorkflowExecution.objects.filter(workflow=workflow, status='completed').count()
    failed_executions = WorkflowExecution.objects.filter(workflow=workflow, status='failed').count()
    
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
    """Create new workflow template (simple form)"""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        trigger_type = request.POST.get('trigger_type', 'manual')
        is_active = request.POST.get('is_active') == 'on'
        
        workflow = WorkflowTemplate.objects.create(
            name=name,
            description=description,
            trigger_type=trigger_type,
            is_active=is_active,
            created_by=request.user
        )
        
        messages.success(request, f'Workflow "{workflow.name}" created successfully!')
        return redirect('analytics:workflow_detail', pk=workflow.pk)
    
    trigger_choices = WorkflowTemplate._meta.get_field('trigger_type').choices
    
    context = {
        'trigger_choices': trigger_choices,
    }
    
    return render(request, 'analytics/workflow_create.html', context)


@login_required
def workflow_edit(request, pk):
    """Edit workflow template"""
    workflow = get_object_or_404(WorkflowTemplate, pk=pk)
    
    if request.method == 'POST':
        workflow.name = request.POST.get('name', workflow.name)
        workflow.description = request.POST.get('description', workflow.description)
        workflow.trigger_type = request.POST.get('trigger_type', workflow.trigger_type)
        workflow.is_active = request.POST.get('is_active') == 'on'
        workflow.save()
        
        messages.success(request, f'Workflow "{workflow.name}" updated successfully!')
        return redirect('analytics:workflow_detail', pk=workflow.pk)
    
    trigger_choices = WorkflowTemplate._meta.get_field('trigger_type').choices
    
    context = {
        'workflow': workflow,
        'trigger_choices': trigger_choices,
    }
    
    return render(request, 'analytics/workflow_edit.html', context)


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
    """Create new workflow action (simple form)"""
    workflow = get_object_or_404(WorkflowTemplate, pk=workflow_pk)
    
    if request.method == 'POST':
        from .models import WorkflowAction
        import json
        
        action_type = request.POST.get('action_type')
        action_config_json = request.POST.get('action_config', '{}')
        
        try:
            action_config = json.loads(action_config_json)
        except json.JSONDecodeError:
            action_config = {}
        
        # Get next action order
        last_action = WorkflowAction.objects.filter(workflow=workflow).order_by('-action_order').first()
        action_order = (last_action.action_order + 1) if last_action else 1
        
        action = WorkflowAction.objects.create(
            workflow=workflow,
            action_type=action_type,
            action_order=action_order,
            action_config=action_config
        )
        
        messages.success(request, 'Action added to workflow!')
        return redirect('analytics:workflow_detail', pk=workflow.pk)
    
    from .models import WorkflowAction
    action_choices = WorkflowAction._meta.get_field('action_type').choices
    
    context = {
        'workflow': workflow,
        'action_choices': action_choices,
    }
    
    return render(request, 'analytics/workflow_action_create.html', context)


@login_required
def workflow_execute_manual(request, pk):
    """Manually execute workflow for a customer"""
    workflow = get_object_or_404(WorkflowTemplate, pk=pk)
    
    if request.method == 'POST':
        customer_id = request.POST.get('customer_id')
        try:
            customer = Customer.objects.get(pk=customer_id)
            from .task_automation import WorkflowEngine
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
    
    # Get action executions using direct query
    from .models import ActionExecution
    action_executions = ActionExecution.objects.filter(workflow_execution=execution).order_by('started_at')
    
    context = {
        'execution': execution,
        'action_executions': action_executions,
    }
    
    return render(request, 'analytics/workflow_execution_detail.html', context)


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
    """Create new reminder (simple form)"""
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description', '')
        customer_id = request.POST.get('customer_id')
        remind_at_str = request.POST.get('remind_at')
        
        try:
            customer = Customer.objects.get(pk=customer_id)
            from datetime import datetime
            remind_at = datetime.fromisoformat(remind_at_str.replace('Z', '+00:00'))
            
            reminder = Reminder.objects.create(
                title=title,
                description=description,
                customer=customer,
                user=request.user,
                remind_at=remind_at
            )
            
            messages.success(request, 'Reminder created successfully!')
            return redirect('analytics:reminder_list')
            
        except (Customer.DoesNotExist, ValueError) as e:
            messages.error(request, f'Error creating reminder: {str(e)}')
    
    customers = Customer.objects.all().order_by('first_name', 'last_name')
    
    context = {
        'customers': customers,
    }
    
    return render(request, 'analytics/reminder_create.html', context)


@login_required
def task_analytics(request):
    """Task analytics and reporting"""
    # Task completion analytics
    total_tasks = Task.objects.count()
    completed_tasks = Task.objects.filter(status='completed').count()
    pending_tasks = Task.objects.filter(status='pending').count()
    in_progress_tasks = Task.objects.filter(status='in_progress').count()
    
    # Overdue tasks
    overdue_tasks = Task.objects.filter(
        due_date__lt=timezone.now(),
        status__in=['pending', 'in_progress']
    ).count()
    
    # Task distribution by priority
    priority_stats = list(Task.objects.values('priority').annotate(count=Count('id')))
    
    # Task distribution by assigned user
    user_stats = list(Task.objects.values('assigned_to__username').annotate(
        count=Count('id')
    ).order_by('-count')[:10])
    
    context = {
        'total_tasks': total_tasks,
        'completed_tasks': completed_tasks,
        'pending_tasks': pending_tasks,
        'in_progress_tasks': in_progress_tasks,
        'overdue_tasks': overdue_tasks,
        'completion_rate': round((completed_tasks / total_tasks * 100) if total_tasks > 0 else 0, 1),
        'priority_stats': priority_stats,
        'user_stats': user_stats,
    }
    
    return render(request, 'analytics/task_analytics.html', context)


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
                task.status = 'completed'
                task.completed_at = timezone.now()
                task.save()
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
    workflows = WorkflowTemplate.objects.all()
    
    data = []
    for workflow in workflows:
        executions = WorkflowExecution.objects.filter(workflow=workflow)
        execution_count = executions.count()
        success_count = executions.filter(status='completed').count()
        failure_count = executions.filter(status='failed').count()
        
        success_rate = 0
        if execution_count > 0:
            success_rate = (success_count / execution_count) * 100
        
        data.append({
            'name': workflow.name,
            'executions': execution_count,
            'success_rate': round(success_rate, 1),
            'success_count': success_count,
            'failure_count': failure_count,
        })
    
    return JsonResponse({'workflows': data})