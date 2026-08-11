from rest_framework import serializers
from .models import Cell, CellConnection, Message, Comment, Evaluation
from django.contrib.auth import get_user_model

User = get_user_model()
from django.shortcuts import get_object_or_404


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username']


class LastMessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'content', 'user', 'created_at']


class CellSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    last_message = LastMessageSerializer(read_only=True)

    def get_member_count(self, obj):
        return getattr(obj, 'member_count', 0)

    class Meta:
        model = Cell
        fields = [
            'id', 'name', 'cell_type', 'position_x', 'position_y', 'position_z',
            'width', 'height', 'depth', 'length', 'color', 'color_primary', 'color_secondary',
            'material_type', 'capacity', 'contents', 'is_open', 'is_locked', 'required_key',
            'mass', 'effect', 'description', 'image', 'created_at', 'updated_at', 'is_active',
            'owner', 'properties', 'member_count', 'last_message'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MessageCellSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cell
        fields = ['id', 'name', 'cell_type']


class CellSearchSerializer(serializers.ModelSerializer):
    is_member = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cell
        fields = ['id', 'name', 'created_at', 'is_member']


class CellCRUDSerializer(serializers.ModelSerializer):
    """
    Serializer específico para operaciones CRUD de celdas tipo ROOM.
    Incluye todos los campos necesarios para crear, leer, actualizar y eliminar celdas.
    """
    owner_username = serializers.CharField(source='owner.username', read_only=True)
    member_count = serializers.SerializerMethodField()

    def get_member_count(self, obj):
        return getattr(obj, 'member_count', 0)

    class Meta:
        model = Cell
        fields = [
            'id', 'name', 'description', 'cell_type', 'capacity', 'properties',
            'position_x', 'position_y', 'position_z', 'length', 'width', 'height',
            'pitch', 'yaw', 'roll',
            'color_primary', 'color_secondary', 'material_type', 'texture_url', 'opacity',
            'mass', 'density', 'friction', 'restitution',
            'is_active', 'health', 'temperature', 'lighting_intensity',
            'sound_ambient', 'properties',
            'created_at', 'updated_at', 'owner_username', 'member_count'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'owner_username', 'member_count']

        extra_kwargs = {
            'capacity': {'allow_null': True, 'required': False},
            'description': {'allow_null': True, 'required': False},
            'length': {'allow_null': True, 'required': False},
            'width': {'allow_null': True, 'required': False},
            'height': {'allow_null': True, 'required': False},
            'color_primary': {'allow_null': True, 'required': False},
            'color_secondary': {'allow_null': True, 'required': False},
            'material_type': {'allow_null': True, 'required': False},
            'opacity': {'allow_null': True, 'required': False},
        }

    def create(self, validated_data):
        """Crear celda asignando el owner automáticamente"""
        validated_data['owner'] = self.context['request'].user
        return super().create(validated_data)

    def validate_properties(self, value):
        """Validar que properties sea JSON válido"""
        if value and isinstance(value, str):
            try:
                import json
                json.loads(value)
            except json.JSONDecodeError:
                raise serializers.ValidationError("Formato JSON inválido.")
        return value

    def to_internal_value(self, data):
        """Preprocesar datos antes de validación"""
        internal_data = dict(data)

        if internal_data.get('description') is None:
            internal_data['description'] = ''
        if internal_data.get('capacity') is None:
            internal_data['capacity'] = 0
        if internal_data.get('length') is None:
            internal_data['length'] = 30
        if internal_data.get('width') is None:
            internal_data['width'] = 30
        if internal_data.get('height') is None:
            internal_data['height'] = 10
        if internal_data.get('color_primary') is None:
            internal_data['color_primary'] = '#2196f3'
        if internal_data.get('color_secondary') is None:
            internal_data['color_secondary'] = '#1976d2'
        if internal_data.get('material_type') is None:
            internal_data['material_type'] = 'CONCRETE'
        if internal_data.get('opacity') is None:
            internal_data['opacity'] = 1.0

        return super().to_internal_value(internal_data)


class CellConnectionSerializer(serializers.ModelSerializer):
    from_cell_name = serializers.CharField(source='from_cell.name', read_only=True)
    to_cell_name = serializers.CharField(source='to_cell.name', read_only=True)
    entrance_name = serializers.CharField(source='entrance.name', read_only=True)

    class Meta:
        model = CellConnection
        fields = [
            'id', 'from_cell', 'from_cell_name', 'to_cell', 'to_cell_name',
            'entrance', 'entrance_name', 'bidirectional', 'energy_cost'
        ]
        read_only_fields = ['id', 'from_cell_name', 'to_cell_name', 'entrance_name']

        extra_kwargs = {
            'from_cell': {'required': True},
            'to_cell': {'required': True},
            'entrance': {'required': True},
            'bidirectional': {'required': False, 'default': True},
            'energy_cost': {'required': False, 'default': 0},
        }

    def validate(self, data):
        """Validar la conexión"""
        from_cell = data.get('from_cell')
        to_cell = data.get('to_cell')
        entrance = data.get('entrance')

        if from_cell and to_cell and entrance:
            if entrance_id != from_cell.id and getattr(entrance, 'parent_id', None) != from_cell.id:
                raise serializers.ValidationError("La entrada debe pertenecer a la celda de origen.")

            if CellConnection.objects.filter(
                from_cell=from_cell,
                to_cell=to_cell,
                entrance=entrance
            ).exists():
                if not self.instance or (
                    self.instance.from_cell != from_cell or
                    self.instance.to_cell != to_cell or
                    self.instance.entrance != entrance
                ):
                    raise serializers.ValidationError("Ya existe una conexión con estos parámetros.")

        return data


class MessageSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    room = MessageCellSerializer(read_only=True)

    class Meta:
        model = Message
        fields = ['id', 'content', 'user', 'room', 'created_at']


class CellMemberSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    cell = CellSerializer(read_only=True)

    class Meta:
        model = Evaluation
        fields = ['cell', 'user']


class CommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    room = CellSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ['id', 'user', 'room', 'comment', 'created_at']


class EvaluationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    room = CellSerializer(read_only=True)

    class Meta:
        model = Evaluation
        fields = ['id', 'user', 'room', 'rating', 'comment', 'created_at']
