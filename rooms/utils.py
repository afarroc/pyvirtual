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
