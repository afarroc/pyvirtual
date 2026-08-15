"""
Cell Transition Manager - Sistema central para gestionar transiciones entre celdas ROOM.
Basado en arquitectura de separación de responsabilidades para sistemas interactivos 3D.
"""
import logging
from datetime import timedelta
from django.utils import timezone
from django.db import transaction
from django.contrib.auth import get_user_model

User = get_user_model()
from .models import Cell, CellConnection, PlayerProfile
from .exceptions import RoomManagerError

logger = logging.getLogger(__name__)


class CellTransitionManager:
    """
    Sistema central que orquesta todas las transiciones entre celdas ROOM.
    Implementa el patrón de separación de responsabilidades donde:
    - CellConnection: Define la conexión y reglas de acceso entre celdas ROOM.
    - Cell (DOOR/PORTAL): Define la entrada/salida física dentro de una celda ROOM.
    - CellTransitionManager: Ejecuta la transición y actualiza el estado global.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @transaction.atomic
    def attempt_transition(self, player_profile, entrance_cell, direction=None):
        """
        Intenta realizar una transición a través de una celda de tipo DOOR/PORTAL.

        Args:
            player_profile: Instancia de PlayerProfile.
            entrance_cell: Instancia de Cell con cell_type='DOOR' o 'PORTAL'.
            direction: Dirección opcional para validación adicional.

        Returns:
            dict: Resultado de la transición con estado y datos.
        """
        try:
            self.logger.info(f"Intentando transición para {player_profile.user.username} a través de {entrance_cell.name}")

            current_room = player_profile.current_room
            if not current_room or current_room.cell_type != 'ROOM':
                return {
                    'success': False,
                    'reason': 'NO_CURRENT_ROOM',
                    'message': 'No estás en ninguna habitación.'
                }

            connection = CellConnection.objects.filter(entrance=entrance_cell).first()
            if not connection:
                return {
                    'success': False,
                    'reason': 'NO_CONNECTION',
                    'message': f'La puerta {entrance_cell.name} no tiene conexión activa.'
                }

            if not self._is_entrance_enabled_for_room(entrance_cell, current_room):
                return {
                    'success': False,
                    'reason': 'DOOR_DISABLED',
                    'message': f'La puerta {entrance_cell.name} está deshabilitada para esta habitación.'
                }

            access_result = self._validate_access(player_profile, entrance_cell, connection)
            if not access_result['allowed']:
                return {
                    'success': False,
                    'reason': access_result['reason'],
                    'message': access_result['message']
                }

            target_room = self._determine_target_room(current_room, connection)
            if not target_room or target_room.cell_type != 'ROOM' or not target_room.is_active:
                return {
                    'success': False,
                    'reason': 'INVALID_DESTINATION',
                    'message': 'La habitación destino no es válida o está inactiva.'
                }

            energy_cost = self._calculate_energy_cost(connection, entrance_cell)
            if player_profile.energy < energy_cost:
                return {
                    'success': False,
                    'reason': 'INSUFFICIENT_ENERGY',
                    'message': f'No tienes suficiente energía. Necesitas {energy_cost}, tienes {player_profile.energy}.'
                }

            transition_result = self._execute_transition(
                player_profile, entrance_cell, target_room, energy_cost
            )

            return {
                'success': True,
                'target_room': target_room,
                'energy_cost': energy_cost,
                'experience_gained': self._get_experience_reward(entrance_cell),
                'message': f'Transición exitosa a {target_room.name}'
            }

        except Exception as e:
            self.logger.error(f"Error en transición: {e}", exc_info=True)
            return {
                'success': False,
                'reason': 'SYSTEM_ERROR',
                'message': 'Error interno del sistema. Inténtalo de nuevo.'
            }

    def _is_entrance_enabled_for_room(self, entrance_cell, room):
        props = entrance_cell.properties or {}
        parent_room = entrance_cell.get_room()
        return props.get('enabled', True) and parent_room and parent_room.id == room.id

    def _validate_access(self, player_profile, entrance_cell, connection):
        props = entrance_cell.properties or {}
        if props.get('access_level', 0) > 0:
            pass

        if props.get('is_locked', False):
            if props.get('required_key'):
                return {
                    'allowed': False,
                    'reason': 'REQUIRES_KEY',
                    'message': f'Necesitas la llave: {props.get("required_key")}'
                }
            return {
                'allowed': False,
                'reason': 'DOOR_LOCKED',
                'message': f'La puerta {entrance_cell.name} está cerrada con llave.'
            }

        allowed_users = entrance_cell.allowed_users.all() if hasattr(entrance_cell, 'allowed_users') else []
        if allowed_users.exists():
            if not allowed_users.filter(id=player_profile.user.id).exists():
                return {
                    'allowed': False,
                    'reason': 'ACCESS_DENIED',
                    'message': 'No tienes permisos para usar esta puerta.'
                }

        return {'allowed': True}

    def _check_usage_limits(self, entrance_cell):
        props = entrance_cell.properties or {}
        max_usage = props.get('max_usage_per_hour', 0)
        if max_usage <= 0:
            return {'allowed': True}

        one_hour_ago = timezone.now() - timedelta(hours=1)
        recent_usage = Cell.objects.filter(
            id=entrance_cell.id,
            updated_at__gte=one_hour_ago
        ).count()

        if recent_usage >= max_usage:
            return {
                'allowed': False,
                'message': f'Límite de uso excedido. Máximo {max_usage} usos por hora.'
            }

        return {'allowed': True}

    def _check_cooldown(self, entrance_cell):
        props = entrance_cell.properties or {}
        cooldown = props.get('cooldown', 0)
        last_opened = entrance_cell.updated_at
        if not last_opened or cooldown <= 0:
            return {'allowed': True}

        cooldown_end = last_opened + timedelta(seconds=cooldown)
        if timezone.now() < cooldown_end:
            remaining_seconds = (cooldown_end - timezone.now()).seconds
            return {
                'allowed': False,
                'message': f'En cooldown. Espera {remaining_seconds} segundos.'
            }

        return {'allowed': True}

    def _determine_target_room(self, current_room, connection):
        if connection.from_cell_id == current_room.id:
            return connection.to_cell
        elif connection.to_cell_id == current_room.id and connection.bidirectional:
            return connection.from_cell
        return None

    def _calculate_energy_cost(self, connection, entrance_cell):
        base_cost = connection.energy_cost
        props = entrance_cell.properties or {}
        modifier = props.get('energy_cost_modifier', 0)
        return max(0, base_cost + modifier)

    def _execute_transition(self, player_profile, entrance_cell, target_room, energy_cost):
        spawn_position = self._calculate_spawn_position(entrance_cell, target_room)
        player_profile.position_x, player_profile.position_y = spawn_position
        player_profile.current_room = target_room
        player_profile.energy -= energy_cost

        props = entrance_cell.properties or {}
        experience_reward = props.get('experience_reward', 0)
        if experience_reward > 0:
            player_profile.productivity = min(100, player_profile.productivity + experience_reward)

        entrance_cell.properties = {
            **props,
            'last_opened': timezone.now().isoformat(),
            'usage_count': props.get('usage_count', 0) + 1,
            'is_open': False,
        }
        entrance_cell.save()

        special_effects = props.get('special_effects')
        if special_effects:
            self._apply_special_effects(player_profile, special_effects)

        player_profile._update_position_geometry()
        player_profile.save()
        self.logger.info(f"Transición completada: {player_profile.user.username} -> {target_room.name}")

    def _calculate_spawn_position(self, entrance_cell, target_room):
        props = entrance_cell.properties or {}
        return (
            props.get('position_x') or target_room.position_x + target_room.length // 2,
            props.get('position_y') or target_room.position_y + target_room.width // 2,
        )

    def _apply_special_effects(self, player_profile, effects):
        if isinstance(effects, dict):
            if effects.get('energy_boost'):
                player_profile.energy = min(100, player_profile.energy + effects['energy_boost'])

            if effects.get('productivity_boost'):
                player_profile.productivity = min(100, player_profile.productivity + effects['productivity_boost'])

            if effects.get('social_boost'):
                player_profile.social = min(100, player_profile.social + effects['social_boost'])

            player_profile.save()

    def get_available_transitions(self, player_profile):
        current_room = player_profile.current_room
        if not current_room or current_room.cell_type != 'ROOM':
            return []

        transitions = []
        for child in current_room.children.filter(cell_type='DOOR', is_active=True):
            props = child.properties or {}
            if not props.get('enabled', True):
                continue

            connection = CellConnection.objects.filter(entrance=child).first()
            if not connection:
                continue

            target_room = self._determine_target_room(current_room, connection)
            if not target_room:
                continue

            access_check = self._validate_access(player_profile, child, connection)
            energy_cost = self._calculate_energy_cost(connection, child)

            transitions.append({
                'entrance': child,
                'target_room': target_room,
                'energy_cost': energy_cost,
                'accessible': access_check['allowed'],
                'reason': access_check.get('reason'),
                'experience_reward': props.get('experience_reward', 0)
            })

        return transitions


# Instancia global del manager
cell_transition_manager = CellTransitionManager()


def get_room_transition_manager():
    """
    Factory function para obtener la instancia del CellTransitionManager.
    """
    return cell_transition_manager
