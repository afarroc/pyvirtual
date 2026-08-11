from django import forms
from .models import Cell, CellConnection, Evaluation, PlayerProfile
import json
from django.db.models import Q
from django.utils.translation import gettext as _


class CellForm(forms.ModelForm):
    class Meta:
        model = Cell
        fields = [
            'name', 'description', 'cell_type', 'capacity', 'properties',
            'position_x', 'position_y', 'position_z', 'length', 'width', 'height',
            'pitch', 'yaw', 'roll', 'parent',
            'color_primary', 'color_secondary', 'material_type', 'texture_url', 'opacity',
            'mass', 'density', 'friction', 'restitution',
            'is_active', 'health', 'temperature', 'lighting_intensity',
            'sound_ambient', 'properties'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nombre de la celda/habitación',
                'class': 'form-control',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Descripción detallada',
                'class': 'form-control',
                'rows': 3
            }),
            'cell_type': forms.Select(attrs={
                'class': 'form-select',
                'required': True
            }),
            'capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Capacidad máxima',
                'min': 1
            }),
            'properties': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Propiedades en formato JSON'
            }),
            'position_x': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Posición X'
            }),
            'position_y': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Posición Y'
            }),
            'position_z': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Posición Z'
            }),
            'length': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Longitud',
                'min': 1
            }),
            'width': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Anchura',
                'min': 1
            }),
            'height': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Altura',
                'min': 1
            }),
            'pitch': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rotación X (grados)'
            }),
            'yaw': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rotación Y (grados)'
            }),
            'roll': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Rotación Z (grados)'
            }),
            'parent': forms.Select(attrs={
                'class': 'form-select',
                'placeholder': 'Celda padre (opcional)'
            }),
            'color_primary': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'placeholder': '#2196f3'
            }),
            'color_secondary': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color',
                'placeholder': '#1976d2'
            }),
            'material_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'texture_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://ejemplo.com/textura.jpg'
            }),
            'opacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.0,
                'max': 1.0,
                'step': 0.1,
                'placeholder': '0.0 - 1.0'
            }),
            'mass': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.1,
                'step': 0.1,
                'placeholder': 'Masa en kg'
            }),
            'density': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.1,
                'step': 0.1,
                'placeholder': 'Densidad en g/cm³'
            }),
            'friction': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.0,
                'max': 1.0,
                'step': 0.1,
                'placeholder': '0.0 - 1.0'
            }),
            'restitution': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0.0,
                'max': 1.0,
                'step': 0.1,
                'placeholder': '0.0 - 1.0'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'health': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'placeholder': '0-100'
            }),
            'temperature': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 0.1,
                'placeholder': 'Temperatura en °C'
            }),
            'lighting_intensity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'max': 100,
                'placeholder': '0-100'
            }),
            'sound_ambient': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sonido ambiente (opcional)'
            }),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            parent_qs = Cell.objects.filter(
                Q(owner=user) | Q(cell_type='UNIVERSE')
            ).filter(cell_type__in=['UNIVERSE', 'ROOM'])
            self.fields['parent'].queryset = parent_qs.distinct()

        optional_fields = [
            'capacity', 'properties', 'position_x', 'position_y', 'position_z', 'length', 'width', 'height',
            'pitch', 'yaw', 'roll', 'color_primary', 'color_secondary', 'material_type',
            'texture_url', 'opacity', 'mass', 'density', 'friction', 'restitution',
            'is_active', 'health', 'temperature', 'lighting_intensity', 'sound_ambient',
            'description', 'image', 'parent'
        ]

        for field_name in optional_fields:
            if field_name in self.fields:
                self.fields[field_name].required = False

    def clean_properties(self):
        properties = self.cleaned_data.get('properties')
        if isinstance(properties, str):
            try:
                return json.loads(properties)
            except json.JSONDecodeError:
                raise forms.ValidationError("Formato JSON inválido para properties.")
        return properties or {}


class CellDetailForm(forms.ModelForm):
    class Meta:
        model = Cell
        fields = [
            'name', 'description', 'cell_type',
            'position_x', 'position_y', 'position_z',
            'width', 'height', 'depth', 'length',
            'color', 'color_primary', 'color_secondary',
            'material_type', 'capacity', 'contents',
            'is_open', 'is_locked', 'required_key',
            'mass', 'effect', 'is_active', 'owner', 'properties'
        ]


class CellConnectionForm(forms.ModelForm):
    class Meta:
        model = CellConnection
        fields = ['from_cell', 'to_cell', 'entrance', 'bidirectional', 'energy_cost']
        widgets = {
            'from_cell': forms.Select(attrs={
                'class': 'form-select',
                'id': 'fromCellSelect'
            }),
            'to_cell': forms.Select(attrs={
                'class': 'form-select',
                'id': 'toCellSelect'
            }),
            'entrance': forms.Select(attrs={
                'class': 'form-select',
                'id': 'entranceSelect'
            }),
            'bidirectional': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'energy_cost': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Costo de energía'
            })
        }

    def __init__(self, *args, **kwargs):
        cell_id = kwargs.pop('cell_id', None)
        super().__init__(*args, **kwargs)

        if cell_id:
            self.fields['from_cell'].initial = cell_id
            self.fields['from_cell'].widget.attrs['disabled'] = True

    def clean(self):
        cleaned_data = super().clean()
        from_cell = cleaned_data.get('from_cell')
        to_cell = cleaned_data.get('to_cell')
        entrance = cleaned_data.get('entrance')

        if from_cell and to_cell and entrance:
            if entrance_id != from_cell.id and getattr(entrance, 'parent_id', None) != from_cell.id:
                raise forms.ValidationError("La entrada debe pertenecer a la celda de origen.")

            if CellConnection.objects.filter(
                from_cell=from_cell,
                to_cell=to_cell,
                entrance=entrance
            ).exclude(pk=self.instance.pk if self.instance else None).exists():
                raise forms.ValidationError("Ya existe una conexión con estos parámetros.")

        return cleaned_data


class EvaluationForm(forms.ModelForm):
    class Meta:
        model = Evaluation
        fields = ['rating', 'comment']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Tu evaluación...'
            }),
            'rating': forms.NumberInput(attrs={
                'min': 1,
                'max': 5,
                'class': 'form-control'
            })
        }
        labels = {
            'comment': _('Comentario'),
            'rating': _('Puntuación'),
        }


class ObjectCreateForm(forms.Form):
    object_type = forms.ChoiceField(choices=[
        ('WORK', 'Estación de trabajo'),
        ('SOCIAL', 'Área social'),
        ('REST', 'Zona de descanso'),
        ('DOOR', 'Puerta'),
        ('EQUIPMENT', 'Equipo'),
        ('CONTAINER', 'Contenedor'),
        ('ITEM', 'Item/Decor'),
        ('FURNITURE', 'Mobiliario'),
    ], widget=forms.Select(attrs={
        'class': 'form-select',
        'id': 'id_object_type'
    }))

    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'Nombre del objeto',
        'required': True
    }))

    position_x = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': 'X'
    }))
    position_y = forms.IntegerField(min_value=0, widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'placeholder': 'Y'
    }))

    effect = forms.CharField(required=False, widget=forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 2,
        'placeholder': 'JSON: {"energy": 5, "productivity": 10}'
    }))

    box_width = forms.IntegerField(required=False, min_value=1, widget=forms.NumberInput(attrs={
        'class': 'form-control'
    }))
    box_height = forms.IntegerField(required=False, min_value=1, widget=forms.NumberInput(attrs={
        'class': 'form-control'
    }))
    box_depth = forms.IntegerField(required=False, min_value=1, widget=forms.NumberInput(attrs={
        'class': 'form-control'
    }))
    box_color = forms.CharField(required=False, max_length=7, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'type': 'color',
        'placeholder': '#8B4513'
    }))
    box_material_type = forms.ChoiceField(required=False, choices=Cell._meta.get_field('material_type').choices, widget=forms.Select(attrs={
        'class': 'form-select'
    }))
    box_is_locked = forms.BooleanField(required=False, widget=forms.CheckboxInput(attrs={
        'class': 'form-check-input'
    }))
    box_required_key = forms.CharField(required=False, max_length=100, widget=forms.TextInput(attrs={
        'class': 'form-control',
        'placeholder': 'ID del objeto/llave necesario'
    }))
    box_mass = forms.DecimalField(required=False, max_digits=10, decimal_places=2, widget=forms.NumberInput(attrs={
        'class': 'form-control',
        'step': 0.1
    }))
    box_capacity = forms.IntegerField(required=False, min_value=1, widget=forms.NumberInput(attrs={
        'class': 'form-control'
    }))
    box_contents = forms.CharField(required=False, widget=forms.Textarea(attrs={
        'class': 'form-control',
        'rows': 2,
        'placeholder': 'JSON: [{"id": 1, "name": "item1"}]'
    }))

    def clean(self):
        cleaned_data = super().clean()
        room = getattr(self, 'room', None)

        if not room:
            raise forms.ValidationError("Habitación no válida.")

        position_x = cleaned_data.get('position_x') or 0
        position_y = cleaned_data.get('position_y') or 0
        if position_x > room.length:
            raise forms.ValidationError(f"La posición X excede el largo de la habitación ({room.length}).")
        if position_y > room.width:
            raise forms.ValidationError(f"La posición Y excede el ancho de la habitación ({room.width}).")

        effect = cleaned_data.get('effect')
        if effect:
            try:
                if isinstance(effect, str):
                    json.loads(effect)
            except (json.JSONDecodeError, TypeError):
                raise forms.ValidationError("Formato JSON inválido en effect.")

        box_contents = cleaned_data.get('box_contents')
        if box_contents:
            try:
                if isinstance(box_contents, str):
                    parsed = json.loads(box_contents)
                    if not isinstance(parsed, list):
                        raise forms.ValidationError("El contenido de la caja debe ser una lista JSON.")
                    cleaned_data['box_contents'] = parsed
            except (json.JSONDecodeError, TypeError):
                raise forms.ValidationError("Formato JSON inválido en contenidos de la caja.")

        return cleaned_data
