from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, css_class):
    existing_classes = value.field.widget.attrs.get('class', '')
    classes = f"{existing_classes} {css_class}".strip()
    return value.as_widget(attrs={**value.field.widget.attrs, 'class': classes})

