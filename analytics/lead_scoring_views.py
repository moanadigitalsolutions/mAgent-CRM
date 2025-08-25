from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.db.models import Count, Avg, Q, F
from django.core.paginator import Paginator
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from datetime import timedelta, datetime
import json
import csv

from customers.models import Customer
from .models import (
    LeadScoringRule, CustomerScore, ScoreHistory, ScoreCalculationLog,
    LeadScoringConfig
)
from .lead_scoring import LeadScoringEngine, get_top_scoring_customers, get_recent_score_changes
from .lead_scoring_forms import (
    LeadScoringRuleForm, LeadScoringConfigForm, BulkScoreCalculationForm,
    ScoreAdjustmentForm, ScoreRuleTestForm, LeadScoringReportForm
)


def is_admin_or_staff(user):
    """Check if user is admin or staff"""
    return user.is_staff or user.is_superuser


@login_required
def lead_scoring_dashboard(request):
    """Main dashboard for lead scoring system"""
    
    # Get scoring overview stats
    total_customers = Customer.objects.count()
    scored_customers = CustomerScore.objects.count()
    
    # Tier distribution
    tier_stats = CustomerScore.objects.values('score_tier').annotate(
        count=Count('id')
    ).order_by('score_tier')
    
    # Recent score changes
    recent_changes = get_recent_score_changes(days=7, limit=10)
    
    # Top scoring customers
    top_customers = get_top_scoring_customers(limit=10)
    
    # Active scoring rules
    active_rules = LeadScoringRule.objects.filter(is_active=True).count()
    
    # Recent calculation logs
    recent_calculations = ScoreCalculationLog.objects.order_by('-started_at')[:5]
    
    # Score distribution chart data
    score_ranges = {
        '0-20': CustomerScore.objects.filter(current_score__range=(0, 20)).count(),
        '21-40': CustomerScore.objects.filter(current_score__range=(21, 40)).count(),
        '41-60': CustomerScore.objects.filter(current_score__range=(41, 60)).count(),
        '61-80': CustomerScore.objects.filter(current_score__range=(61, 80)).count(),
        '81-100': CustomerScore.objects.filter(current_score__range=(81, 100)).count(),
    }
    
    context = {
        'total_customers': total_customers,
        'scored_customers': scored_customers,
        'tier_stats': tier_stats,
        'recent_changes': recent_changes,
        'top_customers': top_customers,
        'active_rules': active_rules,
        'recent_calculations': recent_calculations,
        'score_ranges': score_ranges,
        'scoring_coverage': (scored_customers / total_customers * 100) if total_customers > 0 else 0,
    }
    
    return render(request, 'analytics/lead_scoring/dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def scoring_rules_list(request):
    """List all scoring rules"""
    
    rules = LeadScoringRule.objects.all().order_by('-is_active', '-priority', 'name')
    
    # Add pagination
    paginator = Paginator(rules, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'rules': page_obj.object_list,
    }
    
    return render(request, 'analytics/lead_scoring/rules_list.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def create_scoring_rule(request):
    """Create a new scoring rule"""
    
    if request.method == 'POST':
        form = LeadScoringRuleForm(request.POST)
        if form.is_valid():
            rule = form.save()
            messages.success(request, f'Scoring rule "{rule.name}" created successfully!')
            return redirect('analytics:scoring_rules_list')
    else:
        form = LeadScoringRuleForm()
    
    context = {
        'form': form,
        'title': 'Create Scoring Rule',
        'submit_text': 'Create Rule',
    }
    
    return render(request, 'analytics/lead_scoring/rule_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def edit_scoring_rule(request, rule_id):
    """Edit an existing scoring rule"""
    
    rule = get_object_or_404(LeadScoringRule, id=rule_id)
    
    if request.method == 'POST':
        form = LeadScoringRuleForm(request.POST, instance=rule)
        if form.is_valid():
            rule = form.save()
            messages.success(request, f'Scoring rule "{rule.name}" updated successfully!')
            return redirect('analytics:scoring_rules_list')
    else:
        form = LeadScoringRuleForm(instance=rule)
    
    context = {
        'form': form,
        'rule': rule,
        'title': f'Edit Scoring Rule: {rule.name}',
        'submit_text': 'Update Rule',
    }
    
    return render(request, 'analytics/lead_scoring/rule_form.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def delete_scoring_rule(request, rule_id):
    """Delete a scoring rule"""
    
    rule = get_object_or_404(LeadScoringRule, id=rule_id)
    
    if request.method == 'POST':
        rule_name = rule.name
        rule.delete()
        messages.success(request, f'Scoring rule "{rule_name}" deleted successfully!')
        return redirect('analytics:scoring_rules_list')
    
    context = {
        'rule': rule,
    }
    
    return render(request, 'analytics/lead_scoring/rule_confirm_delete.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def toggle_rule_status(request, rule_id):
    """Toggle active status of a scoring rule"""
    
    rule = get_object_or_404(LeadScoringRule, id=rule_id)
    rule.is_active = not rule.is_active
    rule.save()
    
    status = "activated" if rule.is_active else "deactivated"
    messages.success(request, f'Scoring rule "{rule.name}" {status} successfully!')
    
    return redirect('analytics:scoring_rules_list')


@login_required
@user_passes_test(is_admin_or_staff)
def scoring_configuration(request):
    """Configure lead scoring settings"""
    
    config = LeadScoringConfig.get_config()
    
    if request.method == 'POST':
        form = LeadScoringConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Lead scoring configuration updated successfully!')
            return redirect('analytics:scoring_configuration')
    else:
        form = LeadScoringConfigForm(instance=config)
    
    context = {
        'form': form,
        'config': config,
    }
    
    return render(request, 'analytics/lead_scoring/configuration.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def bulk_score_calculation(request):
    """Trigger bulk score calculations"""
    
    if request.method == 'POST':
        form = BulkScoreCalculationForm(request.POST)
        if form.is_valid():
            calculation_type = form.cleaned_data['calculation_type']
            customer_ids = None
            
            if calculation_type == 'tier':
                tier = form.cleaned_data.get('tier_filter')
                if tier:
                    customer_scores = CustomerScore.objects.filter(score_tier=tier)
                    customer_ids = list(customer_scores.values_list('customer_id', flat=True))
            
            elif calculation_type == 'recent':
                days_back = form.cleaned_data.get('days_back', 30)
                since_date = timezone.now() - timedelta(days=days_back)
                customers = Customer.objects.filter(updated_at__gte=since_date)
                customer_ids = list(customers.values_list('id', flat=True))
            
            elif calculation_type == 'custom':
                customer_ids = form.cleaned_data.get('customer_ids', [])
            
            # Trigger calculation
            calc_log = LeadScoringEngine.bulk_calculate_scores(
                customer_ids=customer_ids,
                user=request.user
            )
            
            messages.success(
                request,
                f'Bulk score calculation started. Calculation ID: {calc_log.calculation_id}'
            )
            return redirect('analytics:lead_scoring_dashboard')
    
    else:
        form = BulkScoreCalculationForm()
    
    context = {
        'form': form,
    }
    
    return render(request, 'analytics/lead_scoring/bulk_calculation.html', context)


@login_required
def customer_scores_list(request):
    """List all customer scores with filtering and sorting"""
    
    # Get filter parameters
    tier_filter = request.GET.get('tier')
    sort_by = request.GET.get('sort', '-current_score')
    search = request.GET.get('search', '').strip()
    
    # Base queryset
    scores = CustomerScore.objects.select_related('customer').all()
    
    # Apply filters
    if tier_filter:
        scores = scores.filter(score_tier=tier_filter)
    
    if search:
        scores = scores.filter(
            Q(customer__first_name__icontains=search) |
            Q(customer__last_name__icontains=search) |
            Q(customer__email__icontains=search)
        )
    
    # Apply sorting
    valid_sorts = [
        'current_score', '-current_score',
        'score_change', '-score_change',
        'last_calculated', '-last_calculated',
        'customer__first_name', '-customer__first_name'
    ]
    
    if sort_by in valid_sorts:
        scores = scores.order_by(sort_by)
    else:
        scores = scores.order_by('-current_score')
    
    # Pagination
    paginator = Paginator(scores, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get tier choices for filter
    tier_choices = CustomerScore.SCORE_TIERS
    
    context = {
        'page_obj': page_obj,
        'scores': page_obj.object_list,
        'tier_choices': tier_choices,
        'current_tier': tier_filter,
        'current_sort': sort_by,
        'search_query': search,
    }
    
    return render(request, 'analytics/lead_scoring/customer_scores.html', context)


@login_required
def customer_score_detail(request, customer_id):
    """Detailed view of a customer's scoring information"""
    
    customer = get_object_or_404(Customer, id=customer_id)
    
    try:
        customer_score = CustomerScore.objects.get(customer=customer)
    except CustomerScore.DoesNotExist:
        # Calculate score if it doesn't exist
        customer_score = LeadScoringEngine.calculate_customer_score(customer, request.user)
    
    # Get score history
    score_history = ScoreHistory.objects.filter(
        customer_score=customer_score
    ).order_by('-changed_at')[:20]
    
    # Get active rules for reference
    active_rules = LeadScoringRule.objects.filter(is_active=True)
    
    # Manual adjustment form
    adjustment_form = ScoreAdjustmentForm()
    
    context = {
        'customer': customer,
        'customer_score': customer_score,
        'score_history': score_history,
        'active_rules': active_rules,
        'adjustment_form': adjustment_form,
        'score_breakdown': customer_score.score_breakdown,
    }
    
    return render(request, 'analytics/lead_scoring/customer_detail.html', context)


@login_required
@require_http_methods(["POST"])
def recalculate_customer_score(request, customer_id):
    """Recalculate score for a specific customer"""
    
    customer = get_object_or_404(Customer, id=customer_id)
    
    try:
        customer_score = LeadScoringEngine.calculate_customer_score(
            customer=customer,
            user=request.user,
            force_recalculate=True
        )
        
        messages.success(
            request,
            f'Score recalculated for {customer.full_name}. New score: {customer_score.current_score}'
        )
    except Exception as e:
        messages.error(request, f'Error recalculating score: {e}')
    
    return redirect('analytics:customer_score_detail', customer_id=customer_id)


@login_required
@user_passes_test(is_admin_or_staff)
def calculation_logs(request):
    """List calculation logs"""
    
    logs = ScoreCalculationLog.objects.all().order_by('-started_at')
    
    # Pagination
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'logs': page_obj.object_list,
    }
    
    return render(request, 'analytics/lead_scoring/calculation_logs.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def calculation_log_detail(request, log_id):
    """Detailed view of a calculation log"""
    
    log = get_object_or_404(ScoreCalculationLog, id=log_id)
    
    context = {
        'log': log,
    }
    
    return render(request, 'analytics/lead_scoring/calculation_log_detail.html', context)


@login_required
@user_passes_test(is_admin_or_staff)
def test_scoring_rule(request):
    """Test a scoring rule against customers"""
    
    results = []
    
    if request.method == 'POST':
        form = ScoreRuleTestForm(request.POST)
        if form.is_valid():
            rule = form.cleaned_data['rule']
            test_all = form.cleaned_data['test_all_customers']
            customer_ids = form.cleaned_data.get('customer_ids', [])
            
            # Get customers to test
            if test_all:
                customers = Customer.objects.all()[:50]  # Limit for testing
            else:
                customers = Customer.objects.filter(id__in=customer_ids)
            
            # Test rule against each customer
            from .lead_scoring import LeadScoringEngine
            
            for customer in customers:
                try:
                    score = LeadScoringEngine._evaluate_rule(customer, rule)
                    results.append({
                        'customer': customer,
                        'score': score,
                        'matched': score > 0,
                    })
                except Exception as e:
                    results.append({
                        'customer': customer,
                        'score': 0,
                        'matched': False,
                        'error': str(e),
                    })
    
    else:
        form = ScoreRuleTestForm()
    
    context = {
        'form': form,
        'results': results,
    }
    
    return render(request, 'analytics/lead_scoring/test_rule.html', context)


@login_required
def scoring_reports(request):
    """Generate lead scoring reports"""
    
    report_data = {}
    
    if request.method == 'POST':
        form = LeadScoringReportForm(request.POST)
        if form.is_valid():
            report_type = form.cleaned_data['report_type']
            date_range = form.cleaned_data['date_range']
            
            # Calculate date range
            if date_range == 'custom':
                start_date = form.cleaned_data.get('start_date')
                end_date = form.cleaned_data.get('end_date')
            else:
                days = int(date_range)
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=days)
            
            # Generate report based on type
            if report_type == 'overview':
                report_data = _generate_overview_report(start_date, end_date)
            elif report_type == 'tier_distribution':
                report_data = _generate_tier_distribution_report(start_date, end_date)
            elif report_type == 'score_changes':
                report_data = _generate_score_changes_report(start_date, end_date)
            elif report_type == 'rule_performance':
                report_data = _generate_rule_performance_report(start_date, end_date)
            elif report_type == 'top_performers':
                limit = form.cleaned_data.get('limit', 50)
                report_data = _generate_top_performers_report(limit)
    
    else:
        form = LeadScoringReportForm()
    
    context = {
        'form': form,
        'report_data': report_data,
    }
    
    return render(request, 'analytics/lead_scoring/reports.html', context)


# Report generation helper functions

def _generate_overview_report(start_date, end_date):
    """Generate overview report"""
    return {
        'total_customers': Customer.objects.count(),
        'scored_customers': CustomerScore.objects.count(),
        'avg_score': CustomerScore.objects.aggregate(Avg('current_score'))['current_score__avg'] or 0,
        'tier_counts': CustomerScore.objects.values('score_tier').annotate(count=Count('id')),
        'recent_changes': ScoreHistory.objects.filter(
            changed_at__date__range=(start_date, end_date)
        ).count(),
    }


def _generate_tier_distribution_report(start_date, end_date):
    """Generate tier distribution report"""
    return {
        'tier_distribution': CustomerScore.objects.values('score_tier').annotate(count=Count('id')),
        'tier_changes': ScoreHistory.objects.filter(
            changed_at__date__range=(start_date, end_date)
        ).exclude(old_tier=F('new_tier')).values('new_tier').annotate(count=Count('id')),
    }


def _generate_score_changes_report(start_date, end_date):
    """Generate score changes report"""
    return {
        'score_changes': ScoreHistory.objects.filter(
            changed_at__date__range=(start_date, end_date)
        ).select_related('customer_score__customer').order_by('-changed_at')[:100],
        'total_changes': ScoreHistory.objects.filter(
            changed_at__date__range=(start_date, end_date)
        ).count(),
    }


def _generate_rule_performance_report(start_date, end_date):
    """Generate rule performance report"""
    # This would need more complex logic to track rule performance
    # For now, return basic rule stats
    return {
        'active_rules': LeadScoringRule.objects.filter(is_active=True),
        'inactive_rules': LeadScoringRule.objects.filter(is_active=False),
    }


def _generate_top_performers_report(limit):
    """Generate top performers report"""
    return {
        'top_customers': CustomerScore.objects.select_related('customer').order_by('-current_score')[:limit],
        'top_improvers': ScoreHistory.objects.filter(
            changed_at__gte=timezone.now() - timedelta(days=30)
        ).select_related('customer_score__customer').order_by('-score_change')[:limit],
    }


# AJAX endpoints

@login_required
def ajax_score_breakdown(request, customer_id):
    """AJAX endpoint for score breakdown details"""
    
    customer = get_object_or_404(Customer, id=customer_id)
    
    try:
        customer_score = CustomerScore.objects.get(customer=customer)
        breakdown = customer_score.score_breakdown or {}
        
        return JsonResponse({
            'success': True,
            'current_score': customer_score.current_score,
            'score_tier': customer_score.score_tier,
            'breakdown': breakdown,
        })
    
    except CustomerScore.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Customer score not found'
        })


@login_required
def export_customer_scores(request):
    """Export customer scores to CSV"""
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customer_scores.csv"'
    
    writer = csv.writer(response)
    writer.writerow([
        'Customer ID', 'Customer Name', 'Email', 'Current Score',
        'Score Tier', 'Score Change', 'Last Calculated'
    ])
    
    scores = CustomerScore.objects.select_related('customer').all()
    
    for score in scores:
        writer.writerow([
            score.customer.pk,
            score.customer.full_name,
            score.customer.email,
            score.current_score,
            score.score_tier,
            score.score_change,
            score.last_calculated.strftime('%Y-%m-%d %H:%M') if score.last_calculated else '',
        ])
    
    return response