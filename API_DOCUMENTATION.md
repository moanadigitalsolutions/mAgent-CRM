# 🔌 mAgent CRM - API Documentation

## Overview

mAgent CRM provides a comprehensive set of internal APIs and endpoints for managing customers, analytics, and automation features. This documentation covers all available endpoints and their usage.

## 🚀 Quick Start

### Base URL
```
http://127.0.0.1:8000/
```

### Authentication
Currently, mAgent CRM uses Django's built-in session authentication. All API calls require user authentication through the web interface.

## 📋 Customer Management API

### Customer Endpoints

#### List Customers
```http
GET /customers/
```
**Description**: Retrieve a paginated list of all customers

**Parameters**:
- `search` (optional): Search term for customer names or email
- `city` (optional): Filter by city
- `ordering` (optional): Sort order (`first_name`, `last_name`, `created_at`)

**Response**:
```json
{
  "customers": [
    {
      "id": 1,
      "first_name": "John",
      "last_name": "Smith",
      "email": "john.smith@example.com",
      "mobile": "0211234567",
      "city": "Auckland",
      "created_at": "2025-08-29T10:00:00Z"
    }
  ],
  "pagination": {
    "total": 100,
    "page": 1,
    "per_page": 20
  }
}
```

#### Get Customer Details
```http
GET /customers/{id}/
```
**Description**: Retrieve detailed information for a specific customer

**Response**:
```json
{
  "id": 1,
  "first_name": "John",
  "last_name": "Smith",
  "email": "john.smith@example.com",
  "mobile": "0211234567",
  "street_address": "123 Main St",
  "suburb": "Central",
  "city": "Auckland",
  "postcode": "1010",
  "is_active": true,
  "created_at": "2025-08-29T10:00:00Z",
  "updated_at": "2025-08-29T10:00:00Z",
  "custom_fields": {
    "company_size": "Small",
    "industry": "Technology"
  },
  "files": [
    {
      "id": 1,
      "name": "contract.pdf",
      "size": 1024000,
      "uploaded_at": "2025-08-29T10:00:00Z"
    }
  ]
}
```

#### Create Customer
```http
POST /customers/add/
```
**Description**: Create a new customer

**Request Body**:
```json
{
  "first_name": "Jane",
  "last_name": "Doe",
  "email": "jane.doe@example.com",
  "mobile": "0212345678",
  "street_address": "456 Queen St",
  "suburb": "CBD",
  "city": "Auckland",
  "postcode": "1010"
}
```

#### Update Customer
```http
POST /customers/{id}/edit/
```
**Description**: Update an existing customer

#### Delete Customer
```http
POST /customers/{id}/delete/
```
**Description**: Soft delete a customer (marks as inactive)

### Customer Utility Endpoints

#### Update Field (AJAX)
```http
POST /customers/{id}/update-field/
```
**Description**: Update a single customer field via AJAX

**Request Body**:
```json
{
  "field": "first_name",
  "value": "Jonathan"
}
```

#### Upload Files
```http
POST /customers/{id}/upload-files/
```
**Description**: Upload files for a customer

**Content-Type**: `multipart/form-data`

#### Validation Endpoints
```http
POST /validate/email/
POST /validate/mobile/
POST /validate/postcode/
```
**Description**: Validate specific field formats

## 🔍 Duplicate Detection API

### Duplicate Detection Endpoints

#### Get Duplicate Summary
```http
GET /customers/duplicates/
```
**Description**: Get all duplicate groups with confidence scores

**Response**:
```json
{
  "duplicate_groups": [
    {
      "group_id": 1,
      "primary_customer": {
        "id": 30,
        "name": "John Smith",
        "email": "john.smith@example.com"
      },
      "duplicates": [
        {
          "id": 31,
          "name": "Jon Smith",
          "confidence": 67.3,
          "match_reasons": ["Same mobile number", "Very similar name"]
        }
      ],
      "max_confidence": 67.3,
      "group_size": 2
    }
  ],
  "total_groups": 2,
  "total_duplicates": 6
}
```

#### Check Customer Duplicates
```http
GET /customers/{id}/check-duplicates/
```
**Description**: Check for duplicates of a specific customer

**Response**:
```json
{
  "customer_id": 30,
  "duplicates": [
    {
      "id": 31,
      "name": "Jon Smith",
      "confidence": 67.3,
      "match_reasons": ["Same mobile number", "Very similar name"]
    }
  ]
}
```

#### Merge Preview
```http
GET /customers/merge/{primary_id}/{duplicate_id}/preview/
```
**Description**: Preview what a merge operation would do

#### Perform Merge
```http
POST /customers/merge/{primary_id}/{duplicate_id}/perform/
```
**Description**: Execute a customer merge operation

#### Ignore Duplicate
```http
POST /customers/{id}/ignore-duplicate/
```
**Description**: Mark a potential duplicate as not a duplicate

### Merge History
```http
GET /customers/merge/history/
```
**Description**: Get history of all merge operations

## 📊 Analytics API

### Analytics Dashboard
```http
GET /analytics/
```
**Description**: Get analytics dashboard data

**Response**:
```json
{
  "customer_stats": {
    "total_customers": 150,
    "active_customers": 145,
    "new_this_month": 12
  },
  "geographic_distribution": {
    "Auckland": 65,
    "Wellington": 45,
    "Christchurch": 25,
    "Other": 15
  },
  "growth_trends": [
    {"month": "2025-06", "customers": 120},
    {"month": "2025-07", "customers": 135},
    {"month": "2025-08", "customers": 150}
  ]
}
```

### Email Automation
```http
GET /analytics/email-automation/
POST /analytics/email-automation/create/
GET /analytics/email-automation/{id}/
PUT /analytics/email-automation/{id}/edit/
DELETE /analytics/email-automation/{id}/delete/
```

### Task Automation
```http
GET /analytics/task-automation/
POST /analytics/task-automation/create/
GET /analytics/workflows/
POST /analytics/workflows/create/
```

### Lead Scoring
```http
GET /analytics/lead-scoring/
POST /analytics/lead-scoring/rules/create/
GET /analytics/lead-scoring/calculate/{customer_id}/
```

## 🔧 Custom Fields API

### Custom Field Management
```http
GET /custom-fields/
POST /custom-fields/add/
GET /custom-fields/{id}/edit/
POST /custom-fields/{id}/edit/
POST /custom-fields/{id}/delete/
```

**Custom Field Types**:
- `text`: Single-line text input
- `textarea`: Multi-line text input
- `number`: Numeric input
- `email`: Email format validation
- `date`: Date picker
- `boolean`: Checkbox (Yes/No)
- `select`: Dropdown with options

## 📤 Import/Export API

### CSV Import
```http
GET /customers/import/
POST /customers/import/upload/
```
**Description**: Import customers from CSV file

**CSV Format**:
```csv
first_name,last_name,email,mobile,street_address,suburb,city,postcode
John,Smith,john@example.com,0211234567,123 Main St,Central,Auckland,1010
```

### CSV Export
```http
GET /customers/export/
POST /customers/export/download/
```
**Description**: Export customers to CSV file

## 🔐 Security & Authentication

### CSRF Protection
All POST requests require CSRF tokens:
```javascript
// Get CSRF token from cookie
function getCookie(name) {
    // Implementation here
}

// Include in requests
headers: {
    'X-CSRFToken': getCookie('csrftoken')
}
```

### Permissions
- **Admin Access**: Full CRUD operations
- **Staff Access**: Read and limited update operations
- **User Access**: Read-only access to assigned customers

## 📝 Response Formats

### Success Response
```json
{
  "status": "success",
  "message": "Operation completed successfully",
  "data": { /* relevant data */ }
}
```

### Error Response
```json
{
  "status": "error",
  "message": "Error description",
  "errors": {
    "field_name": ["Specific error message"]
  }
}
```

### Validation Error
```json
{
  "status": "validation_error",
  "errors": {
    "email": ["Enter a valid email address"],
    "mobile": ["Enter a valid New Zealand mobile number"]
  }
}
```

## 🧪 Testing API Endpoints

### Using curl
```bash
# Get customers list
curl -H "Content-Type: application/json" \
     -b "sessionid=your-session-id" \
     http://127.0.0.1:8000/customers/

# Create customer
curl -X POST \
     -H "Content-Type: application/json" \
     -H "X-CSRFToken: your-csrf-token" \
     -b "sessionid=your-session-id" \
     -d '{"first_name":"Test","last_name":"User","email":"test@example.com"}' \
     http://127.0.0.1:8000/customers/add/
```

### Using JavaScript (from frontend)
```javascript
// Get customers
fetch('/customers/')
  .then(response => response.json())
  .then(data => console.log(data));

// Update customer field
fetch(`/customers/${customerId}/update-field/`, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'X-CSRFToken': getCsrfToken()
  },
  body: JSON.stringify({
    field: 'first_name',
    value: 'Updated Name'
  })
});
```

## 📊 Rate Limiting

Currently, there are no specific rate limits implemented. For production use, consider implementing:
- **Request rate limiting** (e.g., 100 requests per minute)
- **File upload size limits** (current: 10MB per file)
- **Bulk operation limits** (current: 1000 records per operation)

## 🔄 Pagination

List endpoints support pagination:
```http
GET /customers/?page=2&per_page=50
```

**Default**: 20 items per page
**Maximum**: 100 items per page

## 📋 Status Codes

- `200 OK`: Successful operation
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation errors
- `500 Internal Server Error`: Server error

## 🚀 Future API Enhancements

### Planned Features
- **REST API**: Full RESTful API with token authentication
- **GraphQL**: Flexible query interface
- **Webhooks**: Real-time event notifications
- **API Versioning**: Backward compatibility support
- **OpenAPI Spec**: Automated documentation generation

---

## 📞 Support

For API support:
1. Review endpoint documentation above
2. Check Django admin panel for data verification
3. Use browser developer tools for debugging
4. Examine response headers for additional information

**Note**: This documentation covers the current internal API structure. A dedicated REST API is planned for future releases.
