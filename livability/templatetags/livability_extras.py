from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, css_class):
    return value.as_widget(attrs={'class': css_class})

@register.filter
def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0