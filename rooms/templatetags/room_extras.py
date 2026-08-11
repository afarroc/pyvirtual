from django import template

register = template.Library()

@register.filter
def filter_by_type(value, cell_type):
    if not value:
        return []
    return [item for item in value if getattr(item, 'cell_type', None) == cell_type]

@register.filter
def is_current_cell(cell, player):
    if not player:
        return False
    return getattr(cell, 'position_x', None) == getattr(player, 'position_x', None) and getattr(cell, 'position_y', None) == getattr(player, 'position_y', None)

@register.filter
def is_navigable(cell):
    return getattr(cell, 'cell_type', None) in ('UNIVERSE', 'ROOM')

@register.filter
def is_navigable_cell(cell):
    return getattr(cell, 'cell_type', None) in ('UNIVERSE', 'ROOM', 'DOOR', 'PORTAL')
