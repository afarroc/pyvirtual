"""
Utilidades GTD compartidas
"""

from typing import Any, Dict, Optional


def verify_inbox_links(user: Any, item: Any) -> Dict[str, Any]:
    """
    Verifica que los links de un inbox item sean válidos.
    Placeholder para implementación futura.
    """
    return {
        'valid': True,
        'broken_links': [],
        'item_id': getattr(item, 'id', None),
    }


def fix_broken_links(user: Any, item: Any) -> Dict[str, Any]:
    """
    Intenta reparar links rotos de un inbox item.
    Placeholder para implementación futura.
    """
    return {
        'fixed': False,
        'item_id': getattr(item, 'id', None),
        'reason': 'Not implemented yet',
    }
