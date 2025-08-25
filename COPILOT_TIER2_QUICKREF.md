# 🤖 COPILOT QUICK REFERENCE - TIER 2 IMPLEMENTATION

## 🎯 **IMMEDIATE NEXT STEPS**

### **1. START HERE - Analytics Dashboard**
```bash
# Command to begin Tier 2 development
python manage.py startapp analytics
```

### **2. Core Files to Create First**
1. `analytics/models.py` - Analytics data models
2. `analytics/views.py` - Dashboard views
3. `templates/analytics/dashboard.html` - Main dashboard
4. `static/js/analytics-charts.js` - Chart functionality

### **3. Key Dependencies to Install**
```bash
pip install django-rest-framework
pip install celery[redis]
pip install reportlab
pip install openpyxl
pip install python-decouple
```

---

## 🔧 **DEVELOPMENT COMMANDS**

### **Model Creation Pattern**
```python
# For each new feature, create models following this pattern:
class AnalyticsEvent(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=50)
    timestamp = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict)
    
    class Meta:
        indexes = [
            models.Index(fields=['customer', 'timestamp']),
            models.Index(fields=['event_type']),
        ]
```

### **View Creation Pattern**
```python
# Use CBVs with mixins for consistency
class AnalyticsDashboardView(LoginRequiredMixin, TemplateView):
    template_name = 'analytics/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['metrics'] = self.get_analytics_data()
        return context
```

### **URL Pattern**
```python
# Add to main urls.py
path('analytics/', include('analytics.urls')),

# Create analytics/urls.py
urlpatterns = [
    path('', AnalyticsDashboardView.as_view(), name='analytics_dashboard'),
    path('api/data/', AnalyticsAPIView.as_view(), name='analytics_api'),
]
```

---

## 📊 **FEATURE IMPLEMENTATION ORDER**

### **Week 1-2: Analytics Foundation**
1. **Day 1-2**: Analytics models and basic dashboard
2. **Day 3-4**: Chart integration (Chart.js)
3. **Day 5-7**: Customer metrics and trends
4. **Day 8-10**: Performance optimization

### **Week 3-4: Automation Features**
1. **Day 11-14**: Email automation system
2. **Day 15-17**: Task automation
3. **Day 18-20**: Lead scoring
4. **Day 21**: Integration testing

### **Week 5-6: Advanced Features**
1. **Day 22-24**: API framework
2. **Day 25-27**: Third-party integrations
3. **Day 28-30**: RBAC enhancements

---

## 🧪 **TESTING COMMANDS**

### **Test Each Feature**
```bash
# Run specific test modules
python manage.py test analytics
python manage.py test customers.tests.test_automation
python manage.py test api

# Coverage reporting
coverage run --source='.' manage.py test
coverage report
coverage html
```

### **Performance Testing**
```bash
# Django debug toolbar for query optimization
pip install django-debug-toolbar

# Database query analysis
python manage.py shell
>>> from django.db import connection
>>> print(connection.queries)
```

---

## 🚀 **DEPLOYMENT COMMANDS**

### **Heroku Preparation**
```bash
# Update requirements.txt
pip freeze > requirements.txt

# Create/update Procfile
echo "web: gunicorn magent.wsgi" > Procfile
echo "worker: celery -A magent worker -l info" >> Procfile

# Add Redis addon (if using Celery)
heroku addons:create heroku-redis:mini --app magent-crm
```

### **Database Migrations**
```bash
# Create migrations
python manage.py makemigrations analytics
python manage.py makemigrations customers

# Test migrations locally
python manage.py migrate

# Deploy to Heroku
git add .
git commit -m "feat(tier2): implement [feature_name]"
git push heroku main
```

---

## 🎨 **UI/UX GUIDELINES**

### **Dashboard Card Template**
```html
<div class="col-md-3 mb-3">
    <div class="card analytics-card">
        <div class="card-body">
            <h5 class="card-title">{{ metric_name }}</h5>
            <h2 class="metric-value">{{ metric_value }}</h2>
            <span class="metric-change {{ change_class }}">
                {{ change_percentage }}%
            </span>
        </div>
    </div>
</div>
```

### **Chart Container Template**
```html
<div class="chart-container">
    <canvas id="{{ chart_id }}" width="400" height="200"></canvas>
</div>
```

### **CSS Classes to Maintain**
- `.analytics-card` - Dashboard metric cards
- `.chart-container` - Chart wrapper
- `.metric-value` - Large metric numbers
- `.metric-change` - Percentage changes
- `.trend-up/.trend-down` - Trend indicators

---

## 🔐 **SECURITY CHECKLIST**

### **API Security**
- [ ] Authentication required for all endpoints
- [ ] Rate limiting implemented
- [ ] Input validation on all data
- [ ] CSRF protection for forms
- [ ] Secure file uploads

### **Data Protection**
- [ ] Sensitive data encrypted
- [ ] User permissions verified
- [ ] Audit logging implemented
- [ ] SQL injection prevention
- [ ] XSS protection

---

## 📚 **DOCUMENTATION REQUIREMENTS**

### **Code Documentation**
```python
def calculate_customer_lifetime_value(customer_id: int) -> float:
    """
    Calculate the lifetime value for a specific customer.
    
    Args:
        customer_id (int): The ID of the customer
        
    Returns:
        float: The calculated lifetime value
        
    Raises:
        Customer.DoesNotExist: If customer not found
        ValueError: If calculation cannot be performed
    """
    pass
```

### **API Documentation**
- Use Django REST Framework auto-documentation
- Include example requests/responses
- Document authentication requirements
- Provide error code references

---

## 🎯 **SUCCESS METRICS**

### **Performance Targets**
- Dashboard load: < 2 seconds
- API response: < 500ms
- Report generation: < 30 seconds
- Email delivery: < 5 minutes

### **Quality Targets**
- Test coverage: ≥ 95%
- Security scan: Zero critical issues
- Accessibility: WCAG 2.1 AA compliance
- Mobile responsive: All devices

---

## 🚨 **TROUBLESHOOTING**

### **Common Issues**
1. **Slow dashboard**: Add database indexes
2. **Memory errors**: Implement pagination
3. **Email failures**: Check SMTP configuration
4. **Chart not loading**: Verify JavaScript dependencies

### **Debug Commands**
```bash
# Django shell debugging
python manage.py shell
>>> from customers.models import Customer
>>> Customer.objects.count()

# Log analysis
heroku logs --tail --app magent-crm

# Database inspection
python manage.py dbshell
```

---

**🎯 COPILOT REMINDER**: Always maintain consistency with existing Tier 1 code style, follow the established patterns, and ensure comprehensive testing for all new features.

**📋 CURRENT STATUS**: Ready to begin Tier 2 implementation with complete specifications and development guidelines.