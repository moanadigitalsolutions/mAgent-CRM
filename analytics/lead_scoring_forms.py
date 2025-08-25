from django import forms
from django.contrib.auth.models import User
from .models import LeadScoringRule, LeadScoringConfig
import json


class LeadScoringRuleForm(forms.ModelForm):
    """Form for creating and editing lead scoring rules"""
    
    condition_config_text = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 10, 'class': 'form-control'}),
        help_text="JSON configuration for rule conditions",
        required=False
    )
    
    class Meta:
        model = LeadScoringRule
        fields = [
            'name', 'description', 'rule_type', 'score_value', 'is_multiplier',
            'is_active', 'priority', 'condition_config_text'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'rule_type': forms.Select(attrs={'class': 'form-select'}),
            'score_value': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_multiplier': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'priority': forms.NumberInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Populate condition_config_text with JSON if editing
        if self.instance and self.instance.pk and self.instance.condition_config:
            self.fields['condition_config_text'].initial = json.dumps(
                self.instance.condition_config, indent=2
            )
        
        # Add helpful placeholders based on rule type
        self.fields['condition_config_text'].widget.attrs['placeholder'] = self._get_config_placeholder()
    
    def _get_config_placeholder(self):
        """Get placeholder text based on rule type"""
        return '''Example configurations:

Customer Attribute:
{
  "field_name": "email",
  "condition": "not_empty"
}

Interaction Count:
{
  "days_back": 30,
  "min_interactions": 5,
  "interaction_types": ["page_view", "form_submit"]
}

Email Engagement:
{
  "days_back": 30,
  "min_opens": 2,
  "min_clicks": 1,
  "engagement_rate_threshold": 50
}

Geographic Location:
{
  "cities": ["Auckland", "Wellington"],
  "suburbs": ["Ponsonby", "Mount Eden"]
}

Tag Presence:
{
  "required_tags": ["VIP", "Premium"],
  "condition": "any"
}'''
    
    def clean_condition_config_text(self):
        """Validate and parse JSON configuration"""
        config_text = self.cleaned_data.get('condition_config_text', '').strip()
        
        if not config_text:
            return {}
        
        try:
            config = json.loads(config_text)
            if not isinstance(config, dict):
                raise forms.ValidationError("Configuration must be a JSON object")
            return config
        except json.JSONDecodeError as e:
            raise forms.ValidationError(f"Invalid JSON: {e}")
    
    def save(self, commit=True):
        """Save the form and update condition_config"""
        instance = super().save(commit=False)
        instance.condition_config = self.cleaned_data.get('condition_config_text', {})
        
        if commit:
            instance.save()
        
        return instance


class LeadScoringConfigForm(forms.ModelForm):
    """Form for lead scoring configuration"""
    
    class Meta:
        model = LeadScoringConfig
        fields = [
            'min_score', 'max_score', 'cold_threshold', 'warm_threshold',
            'hot_threshold', 'auto_calculation_enabled', 'calculation_frequency',
            'enable_score_decay', 'decay_rate_percent', 'decay_frequency_days',
            'notify_on_tier_change', 'notify_on_qualified_lead'
        ]
        widgets = {
            'min_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_score': forms.NumberInput(attrs={'class': 'form-control'}),
            'cold_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'warm_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'hot_threshold': forms.NumberInput(attrs={'class': 'form-control'}),
            'auto_calculation_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'calculation_frequency': forms.Select(attrs={'class': 'form-select'}),
            'enable_score_decay': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'decay_rate_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.1'}),
            'decay_frequency_days': forms.NumberInput(attrs={'class': 'form-control'}),
            'notify_on_tier_change': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'notify_on_qualified_lead': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class BulkScoreCalculationForm(forms.Form):
    """Form for triggering bulk score calculations"""
    
    calculation_type = forms.ChoiceField(
        choices=[
            ('all', 'All Customers'),
            ('tier', 'Specific Tier'),
            ('recent', 'Recently Updated'),
            ('custom', 'Custom Selection'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    tier_filter = forms.ChoiceField(
        choices=[
            ('cold', 'Cold'),
            ('warm', 'Warm'),
            ('hot', 'Hot'),
            ('qualified', 'Qualified'),
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    days_back = forms.IntegerField(
        min_value=1,
        max_value=365,
        initial=30,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    customer_ids = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
        help_text="Enter customer IDs separated by commas (for custom selection)",
        required=False
    )
    
    force_recalculate = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    def clean_customer_ids(self):
        """Parse and validate customer IDs"""
        customer_ids_text = self.cleaned_data.get('customer_ids', '').strip()
        
        if not customer_ids_text:
            return []
        
        try:
            ids = [int(id_str.strip()) for id_str in customer_ids_text.split(',') if id_str.strip()]
            return ids
        except ValueError:
            raise forms.ValidationError("Please enter valid customer IDs separated by commas")


class ScoreAdjustmentForm(forms.Form):
    """Form for manually adjusting customer scores"""
    
    adjustment_type = forms.ChoiceField(
        choices=[
            ('add', 'Add Points'),
            ('subtract', 'Subtract Points'),
            ('set', 'Set Score'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    score_value = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    
    reason = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Reason for manual score adjustment"
    )
    
    apply_to_all = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Apply this adjustment to all selected customers"
    )


class ScoreRuleTestForm(forms.Form):
    """Form for testing scoring rules against customers"""
    
    rule = forms.ModelChoiceField(
        queryset=LeadScoringRule.objects.filter(is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    test_all_customers = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Test against all customers (uncheck to select specific customers)"
    )
    
    customer_ids = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        help_text="Enter customer IDs separated by commas",
        required=False
    )
    
    def clean_customer_ids(self):
        """Parse and validate customer IDs"""
        customer_ids_text = self.cleaned_data.get('customer_ids', '').strip()
        
        if not customer_ids_text:
            return []
        
        try:
            ids = [int(id_str.strip()) for id_str in customer_ids_text.split(',') if id_str.strip()]
            return ids
        except ValueError:
            raise forms.ValidationError("Please enter valid customer IDs separated by commas")


class LeadScoringReportForm(forms.Form):
    """Form for generating lead scoring reports"""
    
    report_type = forms.ChoiceField(
        choices=[
            ('overview', 'Score Overview'),
            ('tier_distribution', 'Tier Distribution'),
            ('score_changes', 'Recent Score Changes'),
            ('rule_performance', 'Rule Performance'),
            ('top_performers', 'Top Scoring Customers'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    date_range = forms.ChoiceField(
        choices=[
            ('7', 'Last 7 Days'),
            ('30', 'Last 30 Days'),
            ('90', 'Last 90 Days'),
            ('365', 'Last Year'),
            ('custom', 'Custom Range'),
        ],
        initial='30',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    
    tier_filter = forms.MultipleChoiceField(
        choices=[
            ('cold', 'Cold'),
            ('warm', 'Warm'),
            ('hot', 'Hot'),
            ('qualified', 'Qualified'),
        ],
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )
    
    limit = forms.IntegerField(
        min_value=10,
        max_value=1000,
        initial=50,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Maximum number of results to display"
    )