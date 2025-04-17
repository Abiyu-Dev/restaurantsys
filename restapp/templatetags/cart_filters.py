from django import template
from ..models import MenuItem

register = template.Library()

@register.filter
def get_item(item_id):
    try:
        return MenuItem.objects.get(id=item_id)
    except MenuItem.DoesNotExist:
        return None

@register.filter
def multiply(value, arg):
    """Multiply the value by the arg"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0