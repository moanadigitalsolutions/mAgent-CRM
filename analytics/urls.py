from django.urls import path
from . import views
from . import simple_task_views as task_views
from . import lead_scoring_views as scoring_views
from . import quote_job_views as quote_views

app_name = 'analytics'

urlpatterns = [
    # Dashboard
    path('', views.AnalyticsDashboardView.as_view(), name='dashboard'),
    path('api/data/', views.AnalyticsAPIView.as_view(), name='api_data'),
    
    # Customer analytics
    path('customer/<int:customer_id>/', views.CustomerAnalyticsView.as_view(), name='customer_analytics'),
    
    # Reports
    path('reports/', views.ReportsListView.as_view(), name='reports_list'),
    path('reports/builder/', views.ReportBuilderView.as_view(), name='report_builder'),
    
    # Email automation
    path('email/templates/', views.EmailTemplatesView.as_view(), name='email_templates'),
    path('email/sequences/', views.EmailSequencesView.as_view(), name='email_sequences'),
    
    # Email automation API
    path('api/templates/', views.EmailTemplateAPIView.as_view(), name='template_api'),
    path('api/templates/<int:template_id>/', views.EmailTemplateAPIView.as_view(), name='template_api_detail'),
    path('api/templates/create/', views.EmailTemplateCreateView.as_view(), name='template_create'),
    path('api/sequences/create/', views.EmailSequenceCreateView.as_view(), name='sequence_create'),
    path('api/email/test/', views.SendTestEmailView.as_view(), name='send_test_email'),
    path('api/sequences/trigger/', views.TriggerSequenceView.as_view(), name='trigger_sequence'),
    path('api/email/stats/', views.EmailStatsView.as_view(), name='email_stats'),
    
    # Task Automation URLs
    path('tasks/', task_views.task_dashboard, name='task_dashboard'),
    path('tasks/list/', task_views.task_list, name='task_list'),
    path('tasks/create/', task_views.task_create, name='task_create'),
    path('tasks/<int:pk>/', task_views.task_detail, name='task_detail'),
    path('tasks/<int:pk>/complete/', task_views.task_complete, name='task_complete'),
    path('tasks/analytics/', task_views.task_analytics, name='task_analytics'),
    
    # Workflow Management URLs
    path('workflows/', task_views.workflow_list, name='workflow_list'),
    path('workflows/create/', task_views.workflow_create, name='workflow_create'),
    path('workflows/<int:pk>/', task_views.workflow_detail, name='workflow_detail'),
    path('workflows/<int:pk>/edit/', task_views.workflow_edit, name='workflow_edit'),
    path('workflows/<int:pk>/toggle/', task_views.workflow_toggle_active, name='workflow_toggle_active'),
    path('workflows/<int:pk>/execute/', task_views.workflow_execute_manual, name='workflow_execute_manual'),
    
    # Workflow Action URLs
    path('workflows/<int:workflow_pk>/actions/create/', task_views.workflow_action_create, name='workflow_action_create'),
    
    # Workflow Execution URLs
    path('executions/<int:pk>/', task_views.workflow_execution_detail, name='workflow_execution_detail'),
    
    # Reminder URLs
    path('reminders/', task_views.reminder_list, name='reminder_list'),
    path('reminders/create/', task_views.reminder_create, name='reminder_create'),
    
    # AJAX URLs
    path('ajax/task-status-update/', task_views.task_status_update, name='task_status_update'),
    path('ajax/workflow-analytics/', task_views.workflow_analytics_data, name='workflow_analytics_data'),
    
    # Lead Scoring URLs
    path('lead-scoring/', scoring_views.lead_scoring_dashboard, name='lead_scoring_dashboard'),
    path('lead-scoring/rules/', scoring_views.scoring_rules_list, name='scoring_rules_list'),
    path('lead-scoring/rules/create/', scoring_views.create_scoring_rule, name='create_scoring_rule'),
    path('lead-scoring/rules/<int:rule_id>/edit/', scoring_views.edit_scoring_rule, name='edit_scoring_rule'),
    path('lead-scoring/rules/<int:rule_id>/delete/', scoring_views.delete_scoring_rule, name='delete_scoring_rule'),
    path('lead-scoring/rules/<int:rule_id>/toggle/', scoring_views.toggle_rule_status, name='toggle_rule_status'),
    path('lead-scoring/configuration/', scoring_views.scoring_configuration, name='scoring_configuration'),
    path('lead-scoring/bulk-calculation/', scoring_views.bulk_score_calculation, name='bulk_score_calculation'),
    path('lead-scoring/customers/', scoring_views.customer_scores_list, name='customer_scores_list'),
    path('lead-scoring/customers/<int:customer_id>/', scoring_views.customer_score_detail, name='customer_score_detail'),
    path('lead-scoring/customers/<int:customer_id>/recalculate/', scoring_views.recalculate_customer_score, name='recalculate_customer_score'),
    path('lead-scoring/logs/', scoring_views.calculation_logs, name='calculation_logs'),
    path('lead-scoring/logs/<int:log_id>/', scoring_views.calculation_log_detail, name='calculation_log_detail'),
    path('lead-scoring/test-rule/', scoring_views.test_scoring_rule, name='test_scoring_rule'),
    path('lead-scoring/reports/', scoring_views.scoring_reports, name='scoring_reports'),
    path('lead-scoring/export/', scoring_views.export_customer_scores, name='export_customer_scores'),
    
    # Lead Scoring AJAX URLs
    path('ajax/score-breakdown/<int:customer_id>/', scoring_views.ajax_score_breakdown, name='ajax_score_breakdown'),
    
    # Quote & Job Management URLs
    path('quotes-jobs/', quote_views.quote_job_dashboard, name='quote_job_dashboard'),
    
    # Quote URLs
    path('quotes/', quote_views.quote_list, name='quote_list'),
    path('quotes/create/', quote_views.quote_create, name='quote_create'),
    path('quotes/<int:quote_id>/', quote_views.quote_detail, name='quote_detail'),
    path('quotes/<int:quote_id>/edit/', quote_views.quote_edit, name='quote_edit'),
    path('quotes/<int:quote_id>/send/', quote_views.quote_send, name='quote_send'),
    path('quotes/<int:quote_id>/pdf/', quote_views.quote_pdf, name='quote_pdf'),
    path('quotes/<int:quote_id>/job/', quote_views.job_create_from_quote, name='job_create_from_quote'),
    path('quotes/<int:quote_id>/invoice/', quote_views.quote_generate_invoice, name='quote_generate_invoice'),
    path('quotes/<int:quote_id>/respond/', quote_views.quote_respond, name='quote_respond'),
    path('quotes/<int:quote_id>/convert-to-job/', quote_views.quote_convert_to_job, name='quote_convert_to_job'),
    path('quotes/<int:quote_id>/duplicate/', quote_views.quote_duplicate, name='quote_duplicate'),
    
    # Job URLs
    path('jobs/', quote_views.job_list, name='job_list'),
    path('jobs/create/', quote_views.job_create, name='job_create'),
    path('jobs/<int:job_id>/', quote_views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/update-status/', quote_views.job_update_status, name='job_update_status'),
    path('jobs/<int:job_id>/add-update/', quote_views.job_add_update, name='job_add_update'),
    
    # Email Processing
    path('process-email/', quote_views.process_email, name='process_email'),
    
    # API Endpoints
    path('api/quote-stats/', quote_views.quote_stats_api, name='quote_stats_api'),
    path('api/job-stats/', quote_views.job_stats_api, name='job_stats_api'),
    
    # Webhook
    path('webhook/email-received/', quote_views.webhook_email_received, name='webhook_email_received'),
]