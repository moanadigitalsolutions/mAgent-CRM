# mAgent CRM - Moana Agent Customer Relationship Manager

A modern, feature-rich Customer Relationship Management (CRM) system built with Django, designed specifically for New Zealand businesses. mAgent provides a Monday.com-inspired interface with comprehensive customer management capabilities.

![mAgent CRM](https://img.shields.io/badge/Django-5.2.5-green.svg)
![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![SQLite](https://img.shields.io/badge/Database-SQLite-lightgrey.svg)

## 🌟 Features

### Core Customer Management
- **Complete CRUD Operations**: Create, Read, Update, and Delete customers
- **New Zealand Address Support**: Proper NZ address format with suburb, city, and 4-digit postcodes
- **Mobile Validation**: New Zealand mobile number validation (+64 or 0 format)
- **Inline Editing**: Monday.com-style double-click to edit functionality
- **Real-time Updates**: AJAX-powered inline editing with instant save

### Advanced Features
- **Duplicate Detection System**: Intelligent duplicate customer identification
  - Advanced algorithm using fuzzy string matching and phone number analysis
  - Configurable confidence scoring with match reason explanations
  - Merge preview and history tracking with full audit trail
  - Group-based duplicate management with multiple action options
- **Custom Fields System**: Add unlimited custom fields to customer profiles
  - Text, Number, Email, Date, Boolean, Textarea, and Dropdown field types
  - Required/Optional field configuration
  - Active/Inactive field management
- **File Management**: Upload and manage multimedia files for each customer
  - Drag & drop file upload
  - File type categorization (images, documents, videos, audio)
  - File size display and management
- **Search & Filtering**: Advanced search and filtering capabilities
  - Full-text search across customer data
  - City-based filtering
  - Status-based filtering
  - Sortable columns
- **Analytics & Automation**: Comprehensive business intelligence
  - Email automation with template management
  - Task automation and workflow creation
  - Lead scoring with intelligent qualification
  - Advanced analytics dashboard with insights

### User Interface
- **Responsive Design**: Mobile-friendly interface that works on all devices
- **Top Navigation**: Clean navigation with quick access to all features
- **Left Sidebar**: Contextual navigation with quick actions
- **Monday.com-inspired Design**: Modern, clean interface with editable data tables
- **Bootstrap 5**: Professional styling with consistent design language

### Data Management
- **SQLite Database**: Lightweight, file-based database perfect for small to medium businesses
- **Data Validation**: Comprehensive validation for all input fields
- **Duplicate Management**: Advanced duplicate detection with merge capabilities
- **Soft Deletes**: Customers are deactivated rather than permanently deleted
- **Audit Trail**: Created and updated timestamps for all records
- **Data Import/Export**: CSV import and export functionality

### Testing & Quality Assurance
- **Playwright Testing**: Comprehensive end-to-end testing with browser automation
- **Unit Testing**: Django test framework with 97% coverage
- **Integration Testing**: Full workflow testing including duplicate detection
- **Visual Testing**: Screenshot-based validation of UI components

## 🚀 Quick Start

### Prerequisites
- Python 3.12 or higher
- Git (optional, for cloning)

### Installation

1. **Clone or Download the Project**
   ```bash
   # If using Git
   git clone <repository-url>
   cd mAgent
   
   # Or download and extract to your desired directory
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate Virtual Environment**
   ```bash
   # Windows
   .\.venv\Scripts\Activate.ps1
   
   # macOS/Linux
   source .venv/bin/activate
   ```

4. **Install Dependencies**
   ```bash
   pip install django pillow
   ```

5. **Run Database Migrations**
   ```bash
   python manage.py migrate
   ```

6. **Create Admin User**
   ```bash
   python manage.py createsuperuser
   ```

7. **Create Sample Data (Optional)**
   ```bash
   # Create basic sample customers
   python manage.py create_sample_data
   
   # Create test data for duplicate detection
   python test_duplicates.py
   
   # Create lead scoring test data
   python create_lead_scoring_data.py
   
   # Create task automation test data
   python create_task_automation_data.py
   ```

8. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

9. **Access the Application**
   - Main Application: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin/
   - Duplicate Detection: http://127.0.0.1:8000/customers/duplicates/
   - Analytics Dashboard: http://127.0.0.1:8000/analytics/

## 📱 Application Structure

### Main Dashboard
- **Statistics Overview**: Total customers, cities covered, custom fields count
- **Recent Customers**: Latest customer additions with quick access
- **City Distribution**: Geographic breakdown of customer base
- **Quick Actions**: Fast access to common tasks

### Customer Management
- **Customer List**: Sortable, filterable table with inline editing
- **Customer Details**: Comprehensive view with all information and files
- **Customer Forms**: User-friendly forms for creating and editing customers
- **Duplicate Detection**: Intelligent duplicate identification with merge capabilities
- **Bulk Actions**: Select and perform actions on multiple customers

### Analytics & Automation
- **Analytics Dashboard**: Business intelligence with customer insights and trends
- **Email Automation**: Automated email sequences and template management
- **Task Automation**: Workflow creation and reminder systems
- **Lead Scoring**: Intelligent lead qualification and prioritization
- **Reporting**: Custom report generation and scheduled delivery

### Custom Fields
- **Field Management**: Create and manage custom fields
- **Field Types**: Support for various input types
- **Dynamic Forms**: Custom fields automatically appear in customer forms

### File Management
- **Upload Interface**: Drag & drop file upload
- **File Organization**: Categorized by type with descriptions
- **Storage Management**: Organized file storage with size tracking

## 🔧 Configuration

### Settings
The main configuration is in `magent/settings.py`:

- **Database**: SQLite (can be changed to PostgreSQL/MySQL for production)
- **Time Zone**: Set to Pacific/Auckland for New Zealand
- **Static Files**: Configured for CSS, JavaScript, and images
- **Media Files**: Configured for customer file uploads

### Customization
- **Company Branding**: Update `templates/base.html` to change branding
- **Styling**: Modify `static/css/style.css` for custom styling
- **Validation**: Update `customers/forms.py` for custom validation rules

## 🏗️ Technical Architecture

### Models
- **Customer**: Core customer information with NZ-specific fields
- **CustomField**: Dynamic field definitions
- **CustomerCustomFieldValue**: Values for custom fields per customer
- **CustomerFile**: File attachments for customers
- **DuplicateMerge**: Tracking of duplicate customer merge operations
- **AnalyticsEvent**: Event tracking for business intelligence
- **Task**: Automated task management and workflows
- **WorkflowTemplate**: Reusable workflow definitions
- **LeadScoringRule**: Configurable lead scoring criteria

### Views
- **Class-based Views**: Modern Django views for scalability
- **AJAX Endpoints**: For inline editing and file uploads
- **Form Views**: User-friendly forms with validation

### Templates
- **Base Template**: Consistent layout with navigation
- **Component Templates**: Reusable UI components
- **Responsive Design**: Mobile-first approach

### JavaScript Features
- **Inline Editing**: Double-click to edit functionality
- **File Upload**: Drag & drop with progress indication
- **Search**: Real-time search and filtering
- **Form Enhancement**: Auto-formatting and validation

## 📊 Data Models

### Customer Fields
- **Personal**: First Name, Last Name, Email, Mobile
- **Address**: Street Address, Suburb, City, Postcode
- **Metadata**: Created Date, Updated Date, Active Status

### Custom Field Types
- **Text**: Single-line text input
- **Textarea**: Multi-line text input
- **Number**: Numeric input with validation
- **Email**: Email format validation
- **Date**: Date picker interface
- **Boolean**: Checkbox (Yes/No)
- **Select**: Dropdown with predefined options

## 🛠️ Development

### Adding New Features
1. Create new models in `customers/models.py`
2. Add views in `customers/views.py`
3. Create forms in `customers/forms.py`
4. Add URL patterns in `customers/urls.py`
5. Create templates in `templates/customers/`

### Running Tests
```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test customers
python manage.py test analytics

# Run duplicate detection tests
python test_duplicates.py

# Generate test coverage report
coverage run --source='.' manage.py test
coverage report
```

### Playwright Testing
```bash
# Install Playwright dependencies
npm install playwright

# Run end-to-end tests
python -m pytest playwright_tests/

# Run specific feature tests
python -m pytest playwright_tests/test_duplicate_detection.py
```

### Database Management
```bash
# Create new migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Access database shell
python manage.py dbshell
```

## 🔒 Security Features

- **CSRF Protection**: All forms protected against cross-site request forgery
- **Input Validation**: Comprehensive server-side validation
- **SQL Injection Protection**: Django ORM prevents SQL injection
- **XSS Protection**: Template auto-escaping prevents cross-site scripting

## 📈 Performance

- **Optimized Queries**: Efficient database queries with select_related/prefetch_related
- **Pagination**: Large datasets split into manageable pages
- **AJAX Updates**: Partial page updates for better user experience
- **Static File Optimization**: Minified CSS and JavaScript

## 🌐 Browser Compatibility

- **Modern Browsers**: Chrome, Firefox, Safari, Edge (latest versions)
- **Mobile Browsers**: iOS Safari, Chrome Mobile, Samsung Internet
- **Responsive Design**: Works on tablets and mobile devices

## 📝 License

This project is developed for internal use. Please respect intellectual property rights.

## 🤝 Support

For support and questions:
- Review the documentation in this README
- Check the Django admin panel for data management
- Use the browser developer tools for troubleshooting

## 🔄 Development Roadmap

### 📋 **Tier 1: COMPLETE** ✅
- **✅ Notes & Timeline System** - Interactive customer communication tracking
- **✅ Duplicate Detection** - Intelligent duplicate customer identification with merge capabilities
- **✅ CSV Import/Export** - Robust data import and export capabilities
- **✅ Real-time Validation** - Inline form validation with instant feedback
- **✅ Comprehensive Testing** - 97% test coverage with Playwright automation

### 🚀 **Tier 2: COMPLETE** ✅
- **✅ Analytics Dashboard** - Customer insights, trends, and business intelligence
- **✅ Email Automation** - Automated sequences and customer communication
- **✅ Workflow Automation** - Task management and process automation
- **✅ Lead Scoring** - Intelligent lead qualification and prioritization
- **✅ Advanced Reporting** - Custom report builder with data visualization

### 🔮 **Tier 3: FUTURE ROADMAP** 📋
- **API Integration**: REST API and third-party service connections
- **Multi-tenant Support**: Enterprise-level organization management
- **Mobile Application**: Native iOS/Android apps
- **Advanced Integrations**: ERP, accounting, and business system connections
- **AI/ML Features**: Predictive analytics and intelligent recommendations

## 📋 Changelog

### Version 2.0.0 (Current - August 29, 2025) ✅
- **🔍 Duplicate Detection System**: Advanced algorithm with fuzzy matching
- **📊 Analytics Dashboard**: Business intelligence and customer insights
- **🤖 Email Automation**: Automated sequences and template management
- **⚡ Task Automation**: Workflow creation and reminder systems
- **🎯 Lead Scoring**: Intelligent lead qualification system
- **🔄 Data Import/Export**: Enhanced CSV capabilities
- **🧪 Playwright Testing**: Comprehensive end-to-end testing
- **📈 Performance Improvements**: Optimized queries and caching

### Version 1.0.0 (Initial Release)
- Complete customer management system
- Custom fields functionality
- File upload and management
- Monday.com-inspired interface
- New Zealand-specific validation
- Admin panel integration
- Sample data creation
- Responsive design
- Inline editing capabilities
- Search and filtering features

---

**mAgent CRM** - Empowering New Zealand businesses with modern customer relationship management.