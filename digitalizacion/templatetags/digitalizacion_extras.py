from django import template

register = template.Library()

@register.filter
def basename(value):
    if not value:
        return ''
    return str(value).rsplit('/', 1)[-1].rsplit('\\', 1)[-1]
