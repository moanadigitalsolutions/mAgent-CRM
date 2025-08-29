"""
Utility functions for customer management including duplicate detection.
"""
import re
from difflib import SequenceMatcher
from django.db.models import Q
from .models import Customer


def normalize_phone(phone):
    """Normalize phone number for comparison."""
    if not phone:
        return ""
    # Remove all non-digits
    digits_only = re.sub(r'\D', '', phone)
    
    # Handle international format - convert to local
    if digits_only.startswith('6421') or digits_only.startswith('6422') or digits_only.startswith('6427'):
        return '0' + digits_only[2:]  # Convert +6421xxx to 021xxx
    
    # Already in local format or other formats
    return digits_only


def normalize_name(name):
    """Normalize name for comparison."""
    if not name:
        return ""
    return re.sub(r'[^a-zA-Z\s]', '', name.lower().strip())


def calculate_name_similarity(name1, name2):
    """Calculate similarity between two names (0.0 to 1.0)."""
    if not name1 or not name2:
        return 0.0
    
    norm1 = normalize_name(name1)
    norm2 = normalize_name(name2)
    
    if not norm1 or not norm2:
        return 0.0
    
    return SequenceMatcher(None, norm1, norm2).ratio()


def find_potential_duplicates(customer=None, email=None, mobile=None, first_name=None, last_name=None, exclude_id=None):
    """
    Find potential duplicate customers based on various criteria.
    
    Args:
        customer: Customer instance to check for duplicates
        email: Email to check (if not using customer instance)
        mobile: Mobile to check (if not using customer instance)
        first_name: First name to check (if not using customer instance)
        last_name: Last name to check (if not using customer instance)
        exclude_id: Customer ID to exclude from results
    
    Returns:
        List of dictionaries with duplicate customer info and match reasons
    """
    if customer:
        email = customer.email
        mobile = customer.mobile
        first_name = customer.first_name
        last_name = customer.last_name
        exclude_id = customer.id
    
    duplicates = []
    
    # Normalize inputs
    norm_mobile = normalize_phone(mobile)
    norm_first = normalize_name(first_name)
    norm_last = normalize_name(last_name)
    
    # Build query to find potential duplicates
    query = Q()
    
    # Exact email match (highest priority)
    if email:
        query |= Q(email__iexact=email)
    
    # Exact mobile match (high priority)
    if norm_mobile:
        # Check both normalized formats
        original_mobile = mobile if mobile else ""
        query |= Q(mobile=original_mobile)
        # Also check for different formatting of same number
        for cust in Customer.objects.exclude(id=exclude_id) if exclude_id else Customer.objects.all():
            if normalize_phone(cust.mobile) == norm_mobile:
                query |= Q(id=cust.id)
    
    # Get candidates
    candidates = Customer.objects.filter(query).exclude(id=exclude_id) if exclude_id else Customer.objects.filter(query)
    candidates = candidates.distinct()
    
    # Process candidates and calculate match scores
    for candidate in candidates:
        match_reasons = []
        confidence_score = 0.0
        
        # Email match
        if email and candidate.email.lower() == email.lower():
            match_reasons.append("Exact email match")
            confidence_score += 50.0
        
        # Mobile match
        if norm_mobile and normalize_phone(candidate.mobile) == norm_mobile:
            match_reasons.append("Same mobile number")
            confidence_score += 40.0
        
        # Name similarity
        first_similarity = calculate_name_similarity(first_name, candidate.first_name)
        last_similarity = calculate_name_similarity(last_name, candidate.last_name)
        
        if first_similarity >= 0.8 and last_similarity >= 0.8:
            match_reasons.append(f"Very similar name ({first_similarity:.1%}, {last_similarity:.1%})")
            confidence_score += 30.0 * ((first_similarity + last_similarity) / 2)
        elif first_similarity >= 0.6 and last_similarity >= 0.6:
            match_reasons.append(f"Similar name ({first_similarity:.1%}, {last_similarity:.1%})")
            confidence_score += 15.0 * ((first_similarity + last_similarity) / 2)
        
        # Check for exact name matches but different contact info
        if (normalize_name(first_name) == normalize_name(candidate.first_name) and 
            normalize_name(last_name) == normalize_name(candidate.last_name)):
            if email != candidate.email or norm_mobile != normalize_phone(candidate.mobile):
                match_reasons.append("Exact name but different contact info")
                confidence_score += 25.0
        
        # Only include if we have at least one match reason
        if match_reasons:
            duplicates.append({
                'customer': candidate,
                'confidence_score': min(confidence_score, 100.0),  # Cap at 100%
                'match_reasons': match_reasons,
                'first_name_similarity': first_similarity,
                'last_name_similarity': last_similarity,
            })
    
    # Sort by confidence score (highest first)
    duplicates.sort(key=lambda x: x['confidence_score'], reverse=True)
    
    # Also check for similar names across all customers (lower priority)
    if norm_first and norm_last and len(duplicates) < 5:  # Only if we don't have many exact matches
        name_candidates = Customer.objects.exclude(id=exclude_id) if exclude_id else Customer.objects.all()
        
        for candidate in name_candidates:
            # Skip if already in duplicates
            if any(d['customer'].id == candidate.id for d in duplicates):
                continue
                
            first_sim = calculate_name_similarity(first_name, candidate.first_name)
            last_sim = calculate_name_similarity(last_name, candidate.last_name)
            
            if first_sim >= 0.7 and last_sim >= 0.7:
                confidence_score = 10.0 * ((first_sim + last_sim) / 2)
                duplicates.append({
                    'customer': candidate,
                    'confidence_score': confidence_score,
                    'match_reasons': [f"Similar name only ({first_sim:.1%}, {last_sim:.1%})"],
                    'first_name_similarity': first_sim,
                    'last_name_similarity': last_sim,
                })
    
    # Re-sort and limit results
    duplicates.sort(key=lambda x: x['confidence_score'], reverse=True)
    return duplicates[:10]  # Return top 10 matches


def get_duplicate_summary():
    """Get a summary of potential duplicates across all customers."""
    all_customers = Customer.objects.all()
    duplicate_groups = []
    processed_ids = set()
    
    for customer in all_customers:
        if customer.id in processed_ids:
            continue
            
        duplicates = find_potential_duplicates(customer=customer)
        
        # Only include groups with high confidence duplicates
        high_confidence_duplicates = [d for d in duplicates if d['confidence_score'] >= 30.0]
        
        if high_confidence_duplicates:
            # Mark all customers in this group as processed
            group_ids = {customer.id}
            for dup in high_confidence_duplicates:
                group_ids.add(dup['customer'].id)
            
            # Only add if we haven't processed this group yet
            if not group_ids.intersection(processed_ids):
                duplicate_groups.append({
                    'primary_customer': customer,
                    'duplicates': high_confidence_duplicates,
                    'group_size': len(high_confidence_duplicates) + 1,
                    'max_confidence': max(d['confidence_score'] for d in high_confidence_duplicates)
                })
                processed_ids.update(group_ids)
    
    return duplicate_groups


def get_duplicate_summary_stats():
    """Get summary statistics about duplicate detection."""
    duplicates = get_duplicate_summary()
    
    if not duplicates:
        return {
            'total_groups': 0,
            'total_customers': 0,
            'confidence_breakdown': {
                'high': 0,
                'medium': 0,
                'low': 0
            }
        }
    
    total_groups = len(duplicates)
    total_customers = sum(group['group_size'] for group in duplicates)
    
    confidence_breakdown = {'high': 0, 'medium': 0, 'low': 0}
    for group in duplicates:
        max_conf = group['max_confidence']
        if max_conf >= 80:
            confidence_breakdown['high'] += 1
        elif max_conf >= 60:
            confidence_breakdown['medium'] += 1
        else:
            confidence_breakdown['low'] += 1
    
    return {
        'total_groups': total_groups,
        'total_customers': total_customers,
        'confidence_breakdown': confidence_breakdown
    }


def combine_customer_data(primary_customer, duplicate_customer, field_selections=None):
    """
    Combine data from two customer records based on user selections.

    Args:
        primary_customer: The customer record to keep as primary
        duplicate_customer: The customer record to merge from
        field_selections: Dict mapping field names to source ('primary' or 'duplicate')

    Returns:
        Dict with combined data and merge details
    """
    if field_selections is None:
        field_selections = {}

    combined_data = {}
    merge_details = {
        'fields_merged': [],
        'data_sources': {},
        'conflicts_resolved': []
    }

    # Define fields that can be merged
    mergeable_fields = [
        'first_name', 'last_name', 'mobile', 'email',
        'street_address', 'suburb', 'city', 'postcode'
    ]

    for field in mergeable_fields:
        primary_value = getattr(primary_customer, field)
        duplicate_value = getattr(duplicate_customer, field)

        # Determine which value to use
        if field in field_selections:
            source = field_selections[field]
            if source == 'duplicate':
                combined_data[field] = duplicate_value
                merge_details['data_sources'][field] = 'duplicate'
            else:
                combined_data[field] = primary_value
                merge_details['data_sources'][field] = 'primary'
        else:
            # Auto-resolve based on data quality
            if field == 'email' and not primary_value and duplicate_value:
                combined_data[field] = duplicate_value
                merge_details['data_sources'][field] = 'duplicate'
            elif field == 'mobile' and not primary_value and duplicate_value:
                combined_data[field] = duplicate_value
                merge_details['data_sources'][field] = 'duplicate'
            elif field in ['first_name', 'last_name'] and len(str(duplicate_value or '')) > len(str(primary_value or '')):
                combined_data[field] = duplicate_value
                merge_details['data_sources'][field] = 'duplicate'
            else:
                combined_data[field] = primary_value
                merge_details['data_sources'][field] = 'primary'

        # Track if this was a conflict that needed resolution
        if primary_value and duplicate_value and primary_value != duplicate_value:
            merge_details['conflicts_resolved'].append({
                'field': field,
                'primary_value': primary_value,
                'duplicate_value': duplicate_value,
                'chosen': combined_data[field]
            })

    merge_details['fields_merged'] = list(combined_data.keys())
    return combined_data, merge_details


def merge_customer_files(primary_customer, duplicate_customer):
    """
    Handle file merging during customer merge operation.

    Returns:
        Dict with file merge information
    """
    from .models import CustomerFile

    primary_files = CustomerFile.objects.filter(customer=primary_customer)
    duplicate_files = CustomerFile.objects.filter(customer=duplicate_customer)

    file_info = {
        'primary_files': [{'id': f.id, 'name': f.file.name, 'type': f.file_type} for f in primary_files],
        'duplicate_files': [{'id': f.id, 'name': f.file.name, 'type': f.file_type} for f in duplicate_files],
        'files_to_transfer': []
    }

    # Identify files that should be transferred
    duplicate_file_names = {f.file.name for f in duplicate_files}
    primary_file_names = {f.file.name for f in primary_files}

    # Files in duplicate that don't exist in primary
    for file in duplicate_files:
        if file.file.name not in primary_file_names:
            file_info['files_to_transfer'].append({
                'id': file.id,
                'name': file.file.name,
                'type': file.file_type,
                'action': 'transfer'
            })

    return file_info


def merge_customer_notes(primary_customer, duplicate_customer):
    """
    Handle note merging during customer merge operation.

    Returns:
        Dict with note merge information
    """
    from .models import CustomerNote

    primary_notes = CustomerNote.objects.filter(customer=primary_customer)
    duplicate_notes = CustomerNote.objects.filter(customer=duplicate_customer)

    note_info = {
        'primary_notes_count': primary_notes.count(),
        'duplicate_notes_count': duplicate_notes.count(),
        'notes_to_transfer': duplicate_notes.count(),
        'oldest_note_date': None,
        'newest_note_date': None
    }

    if duplicate_notes.exists():
        note_info['oldest_note_date'] = duplicate_notes.order_by('created_at').first().created_at
        note_info['newest_note_date'] = duplicate_notes.order_by('-created_at').first().created_at

    return note_info


def merge_customer_tags(primary_customer, duplicate_customer):
    """
    Handle tag merging during customer merge operation.

    Returns:
        Dict with tag merge information
    """
    primary_tags = set(primary_customer.tags.all())
    duplicate_tags = set(duplicate_customer.tags.all())

    tag_info = {
        'primary_tags': [{'id': t.id, 'name': t.name} for t in primary_tags],
        'duplicate_tags': [{'id': t.id, 'name': t.name} for t in duplicate_tags],
        'tags_to_add': []
    }

    # Tags in duplicate that don't exist in primary
    for tag in duplicate_tags:
        if tag not in primary_tags:
            tag_info['tags_to_add'].append({
                'id': tag.id,
                'name': tag.name,
                'action': 'add'
            })

    return tag_info


def perform_customer_merge(primary_customer, duplicate_customer, field_selections=None, user=None, notes=""):
    """
    Perform the actual merge of two customer records.

    Args:
        primary_customer: Customer to keep
        duplicate_customer: Customer to merge from and delete
        field_selections: Dict of field selections
        user: User performing the merge
        notes: Optional notes about the merge

    Returns:
        Tuple of (success, merge_record, error_message)
    """
    from .models import DuplicateMerge, CustomerFile, CustomerNote
    from django.db import transaction

    try:
        with transaction.atomic():
            # Combine the data
            combined_data, merge_details = combine_customer_data(
                primary_customer, duplicate_customer, field_selections
            )

            # Update primary customer with combined data
            for field, value in combined_data.items():
                setattr(primary_customer, field, value)
            primary_customer.save()

            # Transfer files
            file_info = merge_customer_files(primary_customer, duplicate_customer)
            for file_data in file_info['files_to_transfer']:
                try:
                    file_obj = CustomerFile.objects.get(id=file_data['id'])
                    file_obj.customer = primary_customer
                    file_obj.save()
                except CustomerFile.DoesNotExist:
                    continue

            # Transfer notes
            duplicate_notes = CustomerNote.objects.filter(customer=duplicate_customer)
            for note in duplicate_notes:
                note.customer = primary_customer
                note.save()

            # Add tags
            tag_info = merge_customer_tags(primary_customer, duplicate_customer)
            for tag_data in tag_info['tags_to_add']:
                try:
                    from .models import Tag
                    tag = Tag.objects.get(id=tag_data['id'])
                    primary_customer.tags.add(tag)
                except Tag.DoesNotExist:
                    continue

            # Create merge record
            merge_record = DuplicateMerge.objects.create(
                primary_customer=primary_customer,
                duplicate_customer=duplicate_customer,
                action_taken='merge',
                merged_data={
                    'combined_data': combined_data,
                    'merge_details': merge_details,
                    'file_info': file_info,
                    'note_info': merge_customer_notes(primary_customer, duplicate_customer),
                    'tag_info': tag_info
                },
                notes=notes,
                performed_by=user
            )

            # Mark duplicate as inactive instead of deleting
            duplicate_customer.is_active = False
            duplicate_customer.save()

            return True, merge_record, None

    except Exception as e:
        return False, None, str(e)