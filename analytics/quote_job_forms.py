from django import forms
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal

from .models import QuoteRequest, Job, JobUpdate, EmailAutoResponse
from customers.models import Customer


class QuoteRequestForm(forms.ModelForm):
    """Form for creating and editing quote requests"""
    
    class Meta:
        model = QuoteRequest
        fields = [
            'customer', 'title', 'description', 'service_type', 'priority',
            'source', 'assigned_to', 'quote_due_date'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Brief description of the request'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Detailed requirements and specifications'}),
            'service_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'quote_due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'source': forms.Select(attrs={'class': 'form-control'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter assigned_to to only show staff members
        self.fields['assigned_to'].queryset = User.objects.filter(is_staff=True, is_active=True)
        self.fields['assigned_to'].empty_label = "Select team member"
        
        # Make customer field searchable
        self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')


class QuoteResponseForm(forms.ModelForm):
    """Form for responding to quote requests"""
    
    quote_amount = forms.DecimalField(
        max_digits=10, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    
    response_notes = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Include details about the quote, timeline, terms, etc.'})
    )
    
    class Meta:
        model = QuoteRequest
        fields = ['quote_amount', 'response_notes']
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.final_quote_amount = self.cleaned_data['quote_amount']
        instance.notes = self.cleaned_data['response_notes']
        instance.status = 'quoted'
        instance.quote_sent_at = timezone.now()
        
        if commit:
            instance.save()
        return instance


class JobForm(forms.ModelForm):
    """Form for creating and editing jobs"""
    
    class Meta:
        model = Job
        fields = [
            'customer', 'title', 'description', 'service_type', 'priority',
            'quoted_amount', 'start_date', 'due_date', 'assigned_to',
            'send_progress_updates', 'send_completion_notification', 
            'update_frequency'
        ]
        widgets = {
            'customer': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4}),
            'service_type': forms.Select(attrs={'class': 'form-control'}),
            'priority': forms.Select(attrs={'class': 'form-control'}),
            'quoted_amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'start_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'due_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'send_progress_updates': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'send_completion_notification': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'update_frequency': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['assigned_to'].queryset = User.objects.filter(is_staff=True, is_active=True)
        self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')


class JobUpdateForm(forms.ModelForm):
    """Form for adding job updates"""
    
    class Meta:
        model = JobUpdate
        fields = [
            'update_type', 'title', 'description', 'hours_worked',
            'percentage_complete', 'customer_notified'
        ]
        widgets = {
            'update_type': forms.Select(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'hours_worked': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'percentage_complete': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'customer_notified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class JobStatusUpdateForm(forms.Form):
    """Simple form for updating job status"""
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('in_progress', 'In Progress'),
        ('on_hold', 'On Hold'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional notes about status change'})
    )


class EmailAutoResponseForm(forms.ModelForm):
    """Form for creating and editing auto-response templates"""
    
    class Meta:
        model = EmailAutoResponse
        fields = [
            'name', 'trigger_type', 'service_types', 'subject_template',
            'body_template', 'delay_minutes', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'trigger_type': forms.Select(attrs={'class': 'form-control'}),
            'service_types': forms.CheckboxSelectMultiple(),
            'subject_template': forms.TextInput(attrs={'class': 'form-control'}),
            'body_template': forms.Textarea(attrs={'class': 'form-control', 'rows': 8}),
            'delay_minutes': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class QuoteFilterForm(forms.Form):
    """Form for filtering quote requests"""
    
    STATUS_CHOICES = [('', 'All Statuses')] + QuoteRequest.STATUS_CHOICES
    PRIORITY_CHOICES = [('', 'All Priorities')] + QuoteRequest.PRIORITY_CHOICES
    SERVICE_CHOICES = [('', 'All Services'), ('consultation', 'Consultation'), ('project', 'Project Work'), ('maintenance', 'Maintenance'), ('repair', 'Repair'), ('installation', 'Installation'), ('custom', 'Custom Service'), ('other', 'Other')]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    service_type = forms.ChoiceField(
        choices=SERVICE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True, is_active=True),
        required=False,
        empty_label="All Team Members",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )


class JobFilterForm(forms.Form):
    """Form for filtering jobs"""
    
    STATUS_CHOICES = [('', 'All Statuses')] + Job.STATUS_CHOICES
    PRIORITY_CHOICES = [('', 'All Priorities')] + Job.PRIORITY_CHOICES
    SERVICE_CHOICES = [('', 'All Services'), ('consultation', 'Consultation'), ('project', 'Project Work'), ('maintenance', 'Maintenance'), ('repair', 'Repair'), ('installation', 'Installation'), ('custom', 'Custom Service'), ('other', 'Other')]
    
    status = forms.ChoiceField(
        choices=STATUS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    service_type = forms.ChoiceField(
        choices=SERVICE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    assigned_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True, is_active=True),
        required=False,
        empty_label="All Team Members",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    overdue_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class BulkActionForm(forms.Form):
    """Form for performing bulk actions on quotes/jobs"""
    
    ACTION_CHOICES = [
        ('', 'Select Action'),
        ('assign', 'Assign to Team Member'),
        ('change_status', 'Change Status'),
        ('change_priority', 'Change Priority'),
        ('delete', 'Delete Selected'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    # These fields will be shown/hidden based on action selection
    assign_to = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True, is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    new_status = forms.ChoiceField(
        choices=[],  # Will be populated in __init__ based on model
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    new_priority = forms.ChoiceField(
        choices=[],  # Will be populated in __init__ based on model
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    selected_items = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def __init__(self, model_type='quote', *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if model_type == 'quote':
            self.fields['new_status'].choices = QuoteRequest.STATUS_CHOICES
            self.fields['new_priority'].choices = QuoteRequest.PRIORITY_CHOICES
        elif model_type == 'job':
            self.fields['new_status'].choices = Job.STATUS_CHOICES
            self.fields['new_priority'].choices = Job.PRIORITY_CHOICES


class EmailProcessingForm(forms.Form):
    """Form for manually processing emails as quote requests"""
    
    sender_email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    body = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6})
    )
    
    force_create_quote = forms.BooleanField(
        required=False,
        help_text="Create quote request even if detection confidence is low",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )


class CustomerCommunicationForm(forms.Form):
    """Form for sending custom messages to customers"""
    
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    template = forms.ModelChoiceField(
        queryset=EmailAutoResponse.objects.filter(is_active=True),
        required=False,
        empty_label="Select template (optional)",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    
    message = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 6})
    )
    
    send_copy_to_self = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['customer'].queryset = Customer.objects.all().order_by('first_name', 'last_name')


class QuickStatsForm(forms.Form):
    """Form for customizing dashboard quick stats"""
    
    METRIC_CHOICES = [
        ('quotes_pending', 'Pending Quotes'),
        ('quotes_this_week', 'Quotes This Week'),
        ('jobs_active', 'Active Jobs'),
        ('jobs_overdue', 'Overdue Jobs'),
        ('revenue_this_month', 'Revenue This Month'),
        ('avg_response_time', 'Average Response Time'),
    ]
    
    metrics = forms.MultipleChoiceField(
        choices=METRIC_CHOICES,
        widget=forms.CheckboxSelectMultiple(),
        initial=['quotes_pending', 'jobs_active', 'revenue_this_month']
    )
    
    date_range = forms.ChoiceField(
        choices=[
            ('7', 'Last 7 days'),
            ('30', 'Last 30 days'),
            ('90', 'Last 3 months'),
            ('365', 'Last year'),
        ],
        initial='30',
        widget=forms.Select(attrs={'class': 'form-control'})
    )