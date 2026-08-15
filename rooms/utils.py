from django.contrib.auth import get_user_model

User = get_user_model()


def create_cell(
    name,
    cell_type='ROOM',
    owner=None,
    parent=None,
    position_x=0,
    position_y=0,
    position_z=0,
    length=30,
    width=30,
    height=10,
    color_primary='#2196f3',
    color_secondary='#1976d2',
    material_type=None,
    description='',
    is_active=True,
    properties=None,
    **kwargs
):
    """
    Crea una Cell en la base de datos.
    
    Args:
        name (str): Nombre de la celda.
        cell_type (str): Tipo de celda. Opciones: UNIVERSE, ROOM, AREA, CONTAINER, FURNITURE, OBJECT, ITEM, PORTAL, DOOR, DECORATION.
        owner (User, optional): Usuario propietario.
        parent (Cell, optional): Celda padre.
        position_x (int): Posición X.
        position_y (int): Posición Y.
        position_z (int): Posición Z.
        length (int): Largo en cm.
        width (int): Ancho en cm.
        height (int): Alto en cm.
        color_primary (str): Color primario hex.
        color_secondary (str): Color secundario hex.
        material_type (str, optional): Tipo de material.
        description (str): Descripción.
        is_active (bool): Si está activa.
        properties (dict, optional): Propiedades extendidas.
        **kwargs: Campos adicionales del modelo Cell.
    
    Returns:
        Cell: Instancia creada.
    """
    from rooms.models import Cell
    
    cell = Cell(
        name=name,
        cell_type=cell_type,
        owner=owner,
        parent=parent,
        position_x=position_x,
        position_y=position_y,
        position_z=position_z,
        length=length,
        width=width,
        height=height,
        color_primary=color_primary,
        color_secondary=color_secondary,
        material_type=material_type,
        description=description,
        is_active=is_active,
        properties=properties or {},
        **kwargs
    )
    cell.save()
    return cell


# =============================================================================
# Geometría MIT — Shapely
# =============================================================================

def _ensure_geometry(value):
    """Normaliza a un objeto Shapely desde JSONB/WKT almacenado."""
    try:
        from shapely.geometry import shape, Polygon, Point, box
        from shapely import wkt
    except ImportError as exc:
        raise ImportError('Shapely es requerido para operaciones espaciales en rooms') from exc

    if value is None:
        return None
    if hasattr(value, 'geom_type'):
        return value
    if isinstance(value, dict):
        return shape(value)
    if isinstance(value, str):
        return wkt.loads(value)
    return None


def cell_geometry(cell):
    """Devuelve la geometría de la celda como objeto Shapely."""
    return _ensure_geometry(getattr(cell, 'geometry', None))


def set_cell_geometry_from_bbox(cell, x, y, width, length, z=None, height=None):
    """Almacena en `geometry` un polígono/volumen derivado del bbox de la celda."""
    try:
        from shapely.geometry import Polygon
    except ImportError as exc:
        raise ImportError('Shapely es requerido para operaciones espaciales en rooms') from exc

    x2 = x + width
    y2 = y + length
    geom = Polygon([(x, y), (x2, y), (x2, y2), (x, y2)])
    if z is not None and height is not None:
        geom = geom.buffer(0)
    cell.geometry = geom.__geo_interface__
    cell.save(update_fields=['geometry'])
    return cell


def set_player_position_geometry(player_profile, x, y, z=None):
    """Almacena en `position_geometry` un Point en formato GeoJSON."""
    try:
        from shapely.geometry import Point
    except ImportError as exc:
        raise ImportError('Shapely es requerido para operaciones espaciales en rooms') from exc

    point = Point(float(x), float(y), float(z)) if z is not None else Point(float(x), float(y))
    player_profile.position_geometry = point.__geo_interface__
    player_profile.save(update_fields=['position_geometry'])
    return player_profile


def distance_between(player_profile, cell):
    """Distancia Euclidiana entre el jugador y la geometría de la celda."""
    try:
        from shapely.geometry import Point
        from shapely.ops import nearest_points
    except ImportError as exc:
        raise ImportError('Shapely es requerido para operaciones espaciales en rooms') from exc

    point = _ensure_geometry(getattr(player_profile, 'position_geometry', None))
    if point is None:
        return None
    target = cell_geometry(cell)
    if target is None:
        return None
    return point.distance(target)


def cell_contains_point(cell, player_profile):
    """True si la celda contiene la posición del jugador."""
    target = cell_geometry(cell)
    if target is None:
        return False
    point = _ensure_geometry(getattr(player_profile, 'position_geometry', None))
    if point is None:
        return False
    return target.contains(point)


def room_area(cell):
    """Área de la celda en unidades del modelo (cm² si usas bbox en cm)."""
    geom = cell_geometry(cell)
    if geom is None:
        return None
    return geom.area
