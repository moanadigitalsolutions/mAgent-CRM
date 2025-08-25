from django.contrib import admin
from .models import (
    AnalyticsEvent, CustomerMetrics, DashboardMetric, Report, ReportExecution,
    EmailTemplate, EmailSequence, EmailSequenceStep, EmailDelivery
)


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    list_display = ['customer', 'event_type', 'timestamp', 'user']
    list_filter = ['event_type', 'timestamp', 'user']
    search_fields = ['customer__first_name', 'customer__last_name', 'customer__email']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'


@admin.register(CustomerMetrics)
class CustomerMetricsAdmin(admin.ModelAdmin):
    list_display = ['customer', 'engagement_score', 'lead_score', 'total_interactions', 'calculated_at']
    list_filter = ['calculated_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'customer__email']
    readonly_fields = ['calculated_at']


@admin.register(DashboardMetric)
class DashboardMetricAdmin(admin.ModelAdmin):
    list_display = ['metric_type', 'calculated_at']
    list_filter = ['metric_type', 'calculated_at']
    readonly_fields = ['calculated_at']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['name', 'report_type', 'created_by', 'created_at', 'is_scheduled']
    list_filter = ['report_type', 'is_scheduled', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ReportExecution)
class ReportExecutionAdmin(admin.ModelAdmin):
    list_display = ['report', 'executed_by', 'executed_at', 'status', 'records_count']
    list_filter = ['status', 'executed_at']
    readonly_fields = ['executed_at']


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'created_by', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'subject']
    readonly_fields = ['created_at', 'updated_at']


class EmailSequenceStepInline(admin.TabularInline):
    model = EmailSequenceStep
    extra = 1


@admin.register(EmailSequence)
class EmailSequenceAdmin(admin.ModelAdmin):
    list_display = ['name', 'trigger_type', 'is_active', 'created_by', 'created_at']
    list_filter = ['trigger_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    inlines = [EmailSequenceStepInline]


@admin.register(EmailDelivery)
class EmailDeliveryAdmin(admin.ModelAdmin):
    list_display = ['customer', 'subject', 'status', 'sent_at', 'opened_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['customer__first_name', 'customer__last_name', 'subject']
    readonly_fields = ['sent_at', 'opened_at', 'clicked_at']
