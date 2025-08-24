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