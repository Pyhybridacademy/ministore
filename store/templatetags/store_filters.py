from django import template

register = template.Library()

@register.filter(name='multiply')
def multiply(value, arg):
    """Multiplies the value by the argument.

    Usage: {{ value|multiply:argument }}
    """
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0  # Or some other appropriate default