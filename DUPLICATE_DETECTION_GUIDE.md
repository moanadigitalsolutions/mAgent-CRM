# 🔍 Duplicate Detection System - User Guide

## Overview

The mAgent CRM Duplicate Detection System is an advanced feature that automatically identifies potential duplicate customer records using sophisticated algorithms and provides tools for managing them effectively.

## 🌟 Key Features

### Intelligent Detection Algorithm
- **Fuzzy String Matching**: Uses advanced algorithms to detect similar names
- **Phone Number Analysis**: Identifies same phone numbers in different formats
- **Email Comparison**: Detects similar email patterns
- **Address Matching**: Compares location data for proximity

### Confidence Scoring
- **Percentage-based Scoring**: Each potential duplicate gets a confidence score
- **Match Reasons**: Clear explanations of why records are considered duplicates
- **Prioritization**: Higher confidence matches are shown first

### Comprehensive Management Tools
- **Group-based View**: Related duplicates are grouped together
- **Merge Preview**: See exactly what will happen before merging
- **Merge History**: Complete audit trail of all merge operations
- **Flexible Actions**: Multiple options for handling each duplicate group

## 🚀 Getting Started

### Accessing Duplicate Detection

1. **From Main Navigation**: Click "Duplicates" in the top navigation bar
2. **From Sidebar**: Click "Duplicate Detection" in the left sidebar
3. **Direct URL**: Navigate to `/customers/duplicates/`

### Understanding the Dashboard

The duplicate detection dashboard shows:
- **Total Groups**: Number of duplicate groups found
- **Total Duplicates**: Total number of duplicate records
- **Groups to Review**: Number of unprocessed groups

## 📊 Using the Duplicate Detection Interface

### Duplicate Groups

Each group shows:
- **Primary Record**: The record that will be kept (usually the oldest)
- **Potential Duplicates**: Records that might be duplicates
- **Confidence Score**: Percentage indicating likelihood of being a duplicate
- **Match Reasons**: Specific reasons for the match (same phone, similar name, etc.)

### Available Actions

For each duplicate group, you can:

1. **📋 Review Group**: Examine the details of each record
2. **🔄 Merge Records**: Combine duplicate records into one
3. **❌ Ignore Group**: Mark the group as not duplicates
4. **🔍 Compare Records**: Side-by-side comparison of records

## 🔄 Merge Process

### Step 1: Merge Preview
- Review which record will be the primary (kept) record
- See which data will be preserved or combined
- Understand what will happen to associated files and notes

### Step 2: Perform Merge
- Primary record is updated with best data from all duplicates
- Duplicate records are marked as merged (not deleted)
- All files and notes are transferred to the primary record
- A merge record is created for audit purposes

### Step 3: Verification
- Verify the merged record has all expected data
- Check that files and custom fields were preserved
- Review the merge history for accuracy

## 📈 Merge History

### Accessing Merge History
- Click "Merge History" from the duplicate detection page
- View at `/customers/merge/history/`

### History Information
- **Date and Time**: When the merge was performed
- **Records Involved**: Which customers were merged
- **Performed By**: User who executed the merge
- **Action Taken**: What action was performed (merge, ignore, etc.)

## ⚙️ Configuration and Customization

### Algorithm Settings

The duplicate detection algorithm can be fine-tuned by modifying `customers/utils.py`:

```python
# Confidence thresholds
PHONE_MATCH_SCORE = 40  # Points for exact phone match
NAME_SIMILARITY_THRESHOLD = 0.8  # Minimum similarity for names
EMAIL_SIMILARITY_THRESHOLD = 0.7  # Minimum similarity for emails
```

### Adding Custom Detection Rules

You can add custom duplicate detection rules:

```python
def custom_duplicate_check(customer1, customer2):
    """Custom logic for duplicate detection"""
    # Add your custom logic here
    return confidence_score, match_reasons
```

## 🧪 Testing Duplicate Detection

### Creating Test Data

Use the provided script to create test duplicate data:

```bash
python test_duplicates.py
```

This creates several customers with intentional duplicates:
- **John Smith** & **Jon Smith** (same phone, similar names)
- **Sarah Johnson** & **Sara Johnston** (same phone, very similar names)
- **Mike Brown** & **Michael Brown** (same phone, similar names)

### Running Playwright Tests

Comprehensive end-to-end tests are available:

```bash
# The duplicate detection was tested with VS Code Playwright tools
# Screenshots and test results are stored in .playwright-mcp/
```

## 🔧 Troubleshooting

### Common Issues

1. **No Duplicates Detected**: 
   - Ensure there are actually similar records in the database
   - Check that the algorithm thresholds aren't too strict

2. **False Positives**:
   - Review the match reasons to understand why records were flagged
   - Use the "Ignore Group" action for false positives
   - Consider adjusting algorithm thresholds

3. **Performance Issues**:
   - Large databases may take longer to process
   - Consider running duplicate detection during off-peak hours

### Database Considerations

- **Backup Before Merging**: Always backup your database before performing merges
- **Test on Sample Data**: Test the merge process with sample data first
- **Monitor Merge History**: Regularly review merge history for accuracy

## 📋 Best Practices

### Before Running Detection
1. **Clean Your Data**: Remove obviously bad records first
2. **Standardize Formats**: Ensure phone numbers and addresses are in consistent formats
3. **Backup Database**: Always backup before making changes

### During Review
1. **Check Match Reasons**: Understand why records were flagged as duplicates
2. **Verify Customer Information**: Confirm records actually represent the same person
3. **Review Custom Fields**: Ensure important custom data won't be lost

### After Merging
1. **Verify Results**: Check that merged records have all expected data
2. **Test Functionality**: Ensure the system still works correctly
3. **Document Changes**: Keep records of what was merged and why

## 🔐 Security and Privacy

### Data Protection
- **Audit Trail**: All merge operations are logged with timestamps and user information
- **No Data Loss**: Original records are marked as merged, not deleted
- **Reversible**: Merge operations can be traced and potentially reversed

### Access Control
- **Admin Only**: Only users with appropriate permissions can access duplicate detection
- **Logged Operations**: All actions are logged for accountability

## 📞 Support

For additional help with duplicate detection:
1. Review this documentation
2. Check the Django admin panel for detailed record information
3. Examine the merge history for patterns
4. Test with sample data before processing real customers

---

**Remember**: The duplicate detection system is a powerful tool. Always review matches carefully and backup your data before performing merge operations.
