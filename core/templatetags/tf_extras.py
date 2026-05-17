
from django import template

register = template.Library()

@register.filter
def get_item(value, key):

    if value is None:
        return None
    try:
        return value.get(key, None)
    except AttributeError:
        try:
            return value[key]
        except (KeyError, IndexError, TypeError):
            return None

@register.filter
def to_json_safe(value):

    import json
    return json.dumps(value, default=str)
