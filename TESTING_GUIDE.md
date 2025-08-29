# 🧪 Testing Documentation - mAgent CRM

## Overview

This document provides comprehensive information about testing the mAgent CRM system, including unit tests, integration tests, and end-to-end testing with Playwright.

## 🎯 Testing Strategy

### Testing Pyramid
1. **Unit Tests**: Individual component testing
2. **Integration Tests**: Feature workflow testing  
3. **End-to-End Tests**: Full user journey testing
4. **Visual Tests**: UI component validation

### Test Coverage Goals
- **Minimum**: 90% code coverage
- **Current**: 97% code coverage
- **Target Areas**: Models, Views, Forms, Utils

## 🔧 Test Setup

### Prerequisites
```bash
# Install testing dependencies
pip install coverage pytest-django
pip install playwright pytest-playwright

# Initialize Playwright
playwright install
```

### Configuration Files
- **pytest.ini**: Pytest configuration
- **.coveragerc**: Coverage reporting configuration
- **conftest.py**: Shared test fixtures

## 📋 Unit Testing

### Django Test Framework

#### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test customers
python manage.py test analytics

# Run with verbose output
python manage.py test --verbosity=2

# Run specific test class
python manage.py test customers.tests.CustomerModelTest

# Run specific test method
python manage.py test customers.tests.CustomerModelTest.test_customer_creation
```

#### Test Coverage
```bash
# Generate coverage report
coverage run --source='.' manage.py test
coverage report

# Generate HTML coverage report
coverage html
# View report at htmlcov/index.html
```

### Test Organization

#### Customer App Tests (`customers/tests.py`)
- **Model Tests**: Customer, CustomField, DuplicateMerge models
- **View Tests**: CRUD operations, duplicate detection
- **Form Tests**: Validation, custom field handling
- **Utility Tests**: Duplicate detection algorithms

#### Analytics App Tests (`analytics/tests.py`)
- **Model Tests**: AnalyticsEvent, Task, WorkflowTemplate
- **View Tests**: Dashboard, reporting, automation
- **Email Tests**: Template rendering, sending
- **Workflow Tests**: Task automation, lead scoring

## 🤖 End-to-End Testing with Playwright

### VS Code Playwright Integration

#### Setup
The project includes comprehensive Playwright testing using VS Code's built-in Playwright tools:

1. **Browser Management**: Automated browser control
2. **User Interaction**: Click, type, navigate actions
3. **Visual Validation**: Screenshot-based testing
4. **Network Monitoring**: Request/response analysis

#### Test Execution
```bash
# Playwright tests are executed through VS Code Playwright tools
# Test results and screenshots are stored in .playwright-mcp/
```

### Test Scenarios

#### Duplicate Detection Testing
**Test File**: Automated via VS Code Playwright tools

**Scenarios Covered**:
1. **Data Setup**: Create test customers with intentional duplicates
2. **Detection Accuracy**: Verify correct duplicate identification
3. **User Interface**: Test all interactive elements
4. **Navigation**: Verify links and page transitions
5. **Action Buttons**: Test all duplicate management actions

**Test Results**:
- ✅ Duplicate groups correctly identified (2 groups, 6 duplicates)
- ✅ Confidence scoring working (40.0% and 67.3%)
- ✅ Match reasons accurately displayed
- ✅ All navigation links functional
- ✅ Modal dialogs working correctly

#### Screenshots Captured
- `duplicate_detection_overview.png`: Main duplicate detection interface
- `merge_history_page.png`: Merge history dashboard
- `customer_list_with_duplicates.png`: Customer list showing test data

### Customer Management Testing
1. **Customer CRUD**: Create, read, update, delete operations
2. **Inline Editing**: Double-click editing functionality
3. **File Upload**: Drag & drop file management
4. **Search & Filter**: Advanced filtering capabilities
5. **Custom Fields**: Dynamic field creation and usage

### Analytics Testing
1. **Dashboard Loading**: Analytics dashboard functionality
2. **Chart Rendering**: Data visualization components
3. **Report Generation**: Custom report creation
4. **Email Automation**: Template and sequence testing
5. **Workflow Automation**: Task creation and execution

## 📊 Test Data Management

### Sample Data Scripts

#### Basic Sample Data
```bash
python manage.py create_sample_data
# Creates 20 sample customers with various data
```

#### Duplicate Detection Test Data
```bash
python test_duplicates.py
# Creates specific customers for duplicate testing:
# - John Smith & Jon Smith (same phone)
# - Sarah Johnson & Sara Johnston (same phone + similar names)
# - Mike Brown & Michael Brown (same phone + similar names)
```

#### Lead Scoring Test Data
```bash
python create_lead_scoring_data.py
# Creates customers with various lead scoring attributes
```

#### Task Automation Test Data
```bash
python create_task_automation_data.py
# Creates workflow templates and automated tasks
```

#### Quote/Job Test Data
```bash
python create_quote_job_data.py
# Creates sample quotes and job requests
```

### Test Database Management

#### Separate Test Database
Django automatically creates a separate test database (`test_db.sqlite3`) for testing.

#### Database Reset
```bash
# Reset test database
python manage.py flush --database=test

# Recreate test data
python manage.py migrate --database=test
python test_duplicates.py
```

## 🔍 Performance Testing

### Database Query Optimization
```python
# Test query efficiency
from django.test.utils import override_settings
from django.db import connection

def test_query_count(self):
    with self.assertNumQueries(expected_queries):
        # Test code here
        pass
```

### Load Testing
```bash
# Install locust for load testing
pip install locust

# Run load tests
locust -f tests/load_tests.py --host=http://127.0.0.1:8000
```

## 🐛 Debugging Tests

### Test Debugging Tips

#### Verbose Output
```bash
python manage.py test --verbosity=2 --debug-mode
```

#### Isolated Test Runs
```bash
# Run single test with debugging
python manage.py test customers.tests.DuplicateDetectionTest.test_fuzzy_matching --verbosity=2
```

#### Database Inspection
```python
# In test methods, inspect database state
def test_something(self):
    # Test logic here
    
    # Debug: Print all customers
    for customer in Customer.objects.all():
        print(f"Customer: {customer.full_name} - {customer.email}")
```

### Common Testing Issues

1. **Database State**: Tests affecting each other
   ```python
   # Use setUp and tearDown methods
   def setUp(self):
       self.customer = Customer.objects.create(...)
   
   def tearDown(self):
       Customer.objects.all().delete()
   ```

2. **Time-sensitive Tests**: Tests failing due to timing
   ```python
   # Use freezegun for time-based tests
   from freezegun import freeze_time
   
   @freeze_time("2025-08-29")
   def test_time_sensitive_feature(self):
       # Test code here
       pass
   ```

3. **File Upload Tests**: Testing file handling
   ```python
   from django.core.files.uploadedfile import SimpleUploadedFile
   
   def test_file_upload(self):
       file = SimpleUploadedFile("test.txt", b"file content")
       # Test file upload functionality
   ```

## 📈 Continuous Integration

### GitHub Actions Integration
```yaml
# .github/workflows/tests.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.12
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install coverage
      - name: Run tests
        run: |
          coverage run --source='.' manage.py test
          coverage report --fail-under=90
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Set up hooks
pre-commit install

# Hooks run automatically on commit:
# - Run tests
# - Check code style
# - Verify coverage
```

## 📋 Test Checklists

### Before Release Checklist
- [ ] All unit tests passing
- [ ] Coverage above 90%
- [ ] End-to-end tests passing
- [ ] Performance tests within acceptable limits
- [ ] Sample data scripts working
- [ ] Documentation updated

### Feature Testing Checklist
- [ ] Unit tests for new models
- [ ] Integration tests for new views
- [ ] Form validation tests
- [ ] Edge case handling
- [ ] Error condition testing
- [ ] Playwright testing for UI changes

### Duplicate Detection Specific Tests
- [ ] Algorithm accuracy testing
- [ ] Performance with large datasets
- [ ] UI interaction testing
- [ ] Merge operation validation
- [ ] History tracking verification

## 🔧 Test Maintenance

### Regular Maintenance Tasks
1. **Update Test Data**: Keep sample data current and realistic
2. **Review Coverage**: Identify and test uncovered code paths
3. **Performance Monitoring**: Ensure tests run efficiently
4. **Documentation Updates**: Keep testing docs current

### Test Refactoring
- **Remove Duplicate Code**: Use fixtures and helper methods
- **Improve Readability**: Clear test names and documentation
- **Optimize Performance**: Reduce unnecessary database calls

---

## 📞 Support

For testing support:
1. Review this documentation
2. Check individual test files for examples
3. Use Django's built-in test debugging tools
4. Examine Playwright test results and screenshots

**Remember**: Good tests are the foundation of reliable software. Invest time in writing comprehensive, maintainable tests.
