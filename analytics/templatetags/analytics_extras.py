from django import template

register = template.Library()

@register.filter
def replace(value, arg):
    """
    Replace occurrences of 'old' with 'new' in the given string.
    Usage: {{ string|replace:"old,new" }}
    """
    if not isinstance(value, str):
        value = str(value)
    
    if ',' in arg:
        old, new = arg.split(',', 1)
        return value.replace(old, new)
    return value

@register.filter
def replace_underscore(value):
    """
    Replace underscores with spaces.
    Usage: {{ string|replace_underscore }}
    """
    if not isinstance(value, str):
        value = str(value)
    return value.replace('_', ' ')