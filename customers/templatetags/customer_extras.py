from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary by key"""
    return dictionary.get(key, '')

@register.filter(name='has_group')
def has_group(user, group_name):
    """Return True if the user belongs to the given group name and is authenticated.

    Usage: {% if user|has_group:'ReadOnly' %}
    """
    try:
        if not getattr(user, 'is_authenticated', False):
            return False
        return user.groups.filter(name=group_name).exists()
    except Exception:
        return False

@register.filter(name='lacks_group')
def lacks_group(user, group_name):
    """Inverse of has_group for template clarity."""
    return not has_group(user, group_name)