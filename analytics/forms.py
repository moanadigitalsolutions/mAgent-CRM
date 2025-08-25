from django import forms
from django.contrib.auth.models import User
from customers.models import Customer
from .models import WorkflowTemplate, WorkflowAction, Task, Reminder


class WorkflowTemplateForm(forms.ModelForm):
    """Form for creating/editing workflow templates"""
    
    class Meta:
        model = WorkflowTemplate
        fields = [
            'name', 'description', 'trigger_type', 'trigger_conditions',
            'is_repeatable', 'max_executions', 'is_active'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'trigger_conditions': forms.Textarea(attrs={
                'rows': 6,
                'placeholder': 'Enter JSON conditions, e.g., {"customer_city": ["New York", "Boston"]}'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['trigger_conditions'].help_text = (
            'JSON object with trigger conditions. Leave empty for no conditions.'
        )


class WorkflowActionForm(forms.ModelForm):
    """Form for creating/editing workflow actions"""
    
    class Meta:
        model = WorkflowAction
        fields = [
            'action_type', 'action_config', 'condition_logic',
            'delay_days', 'delay_hours', 'delay_minutes'
        ]
        widgets = {
            'action_config': forms.Textarea(attrs={
                'rows': 8,
                'placeholder': 'Enter JSON configuration for this action'
            }),
            'condition_logic': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Enter JSON conditions (optional)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['action_config'].help_text = (
            'JSON configuration for the action. Required format depends on action type.'
        )
        
        # Add help text for common action types
        action_help = {
            'create_task': 'Example: {"title": "Follow up", "description": "...", "priority": "high", "due_in_days": 7}',
            'send_email': 'Example: {"template_id": 1} or {"subject": "Hello", "message": "..."}',
            'add_note': 'Example: {"content": "Automated note", "note_type": "follow_up"}',
            'assign_tag': 'Example: {"tags": ["vip", "high-value"]}',
        }
        
        if self.instance and self.instance.action_type:
            help_text = action_help.get(self.instance.action_type, '')
            if help_text:
                self.fields['action_config'].help_text += f'\n\n{help_text}'


class TaskForm(forms.ModelForm):
    """Form for creating/editing tasks"""
    tags = forms.CharField(
        required=False,
        help_text="Comma-separated tags (e.g., urgent, follow-up, sales)",
        widget=forms.TextInput(attrs={'placeholder': 'urgent, follow-up, sales'})
    )
    
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'customer', 'assigned_to', 
            'priority', 'due_date', 'tags'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'due_date': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(is_active=True)
        self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')
        
        # Pre-populate tags if editing
        if self.instance and self.instance.pk:
            self.fields['tags'].initial = ', '.join(self.instance.tags or [])
    
    def clean_tags(self):
        """Process tags input"""
        tags = self.cleaned_data.get('tags', '')
        if tags:
            # Split by comma and clean up
            tag_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            return tag_list
        return []


class TaskFilterForm(forms.Form):
    """Form for filtering tasks"""
    STATUS_CHOICES = [
        ('', 'All Statuses'),
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    PRIORITY_CHOICES = [
        ('', 'All Priorities'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    status = forms.ChoiceField(choices=STATUS_CHOICES, required=False)
    priority = forms.ChoiceField(choices=PRIORITY_CHOICES, required=False)
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label="All Assignees"
    )
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        required=False,
        empty_label="All Customers"
    )
    overdue_only = forms.BooleanField(required=False, label="Overdue only")
    due_soon_only = forms.BooleanField(required=False, label="Due soon (next 3 days)")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Order customers by name
        self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')


class ReminderForm(forms.ModelForm):
    """Form for creating/editing reminders"""
    
    class Meta:
        model = Reminder
        fields = [
            'title', 'description', 'customer', 'task', 'remind_at'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'remind_at': forms.DateTimeInput(attrs={
                'type': 'datetime-local',
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')
        self.fields['task'].queryset = Task.objects.filter(
            status__in=['pending', 'in_progress']
        ).order_by('-created_at')
        self.fields['task'].required = False


class WorkflowExecutionForm(forms.Form):
    """Form for manually executing workflows"""
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all().order_by('first_name', 'last_name'),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].label = "Select Customer"