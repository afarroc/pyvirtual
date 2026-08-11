from django.test import SimpleTestCase
from unittest.mock import MagicMock
from .forms import BoxForm, ObjectCreateForm


class BoxFormTestCase(SimpleTestCase):
    def test_box_form_valid_data(self):
        form = BoxForm(data={
            'name': 'Caja Test',
            'position_x': 1,
            'position_y': 2,
            'width': 60,
            'height': 40,
            'depth': 40,
            'color': '#8B4513',
            'material_type': 'CARDBOARD',
            'is_open': False,
            'is_locked': False,
            'required_key': '',
            'mass': 1.5,
            'capacity': 10,
            'contents': '[{"id": 1, "name": "item1"}]'
        })
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_box_form_invalid_name(self):
        form = BoxForm(data={
            'name': '',
            'position_x': 1,
            'position_y': 2
        })
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_box_form_invalid_contents_json(self):
        form = BoxForm(data={
            'name': 'Caja Test',
            'position_x': 1,
            'position_y': 2,
            'contents': 'esto no es json'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('contents', form.errors)

    def test_box_form_contents_must_be_list(self):
        form = BoxForm(data={
            'name': 'Caja Test',
            'position_x': 1,
            'position_y': 2,
            'contents': '{"id": 1}'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('contents', form.errors)

    def test_box_form_negative_position(self):
        form = BoxForm(data={
            'name': 'Caja Test',
            'position_x': -1,
            'position_y': 2,
            'width': 60,
            'height': 40,
            'depth': 40,
            'color': '#8B4513',
            'material_type': 'CARDBOARD',
            'is_open': False,
            'is_locked': False,
            'required_key': '',
            'mass': 1.5,
            'capacity': 10,
            'contents': '[{"id": 1}]'
        })
        self.assertFalse(form.is_valid())
        self.assertIn('position_x', form.errors)

    def test_box_form_valid_contents_parsed_as_list(self):
        form = BoxForm(data={
            'name': 'Caja Test',
            'position_x': 1,
            'position_y': 2,
            'width': 60,
            'height': 40,
            'depth': 40,
            'color': '#8B4513',
            'material_type': 'CARDBOARD',
            'is_open': False,
            'is_locked': False,
            'required_key': '',
            'mass': 1.5,
            'capacity': 10,
            'contents': '[{"id": 1, "name": "item1"}]'
        })
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data['contents'], [{"id": 1, "name": "item1"}])


class ObjectCreateFormTestCase(SimpleTestCase):
    def setUp(self):
        self.room = MagicMock()
        self.room.length = 10
        self.room.width = 10

    def test_object_create_form_box_valid(self):
        form = ObjectCreateForm(data={
            'cell_type': 'CONTAINER',
            'name': 'Caja Objeto',
            'position_x': 1,
            'position_y': 2,
            'box_width': 60,
            'box_height': 40,
            'box_depth': 40,
            'box_color': '#8B4513',
            'box_material_type': 'CARDBOARD',
            'box_is_locked': False,
            'box_required_key': '',
            'box_mass': 1.0,
            'box_capacity': 10,
            'box_contents': '[{"id": 1}]'
        })
        form.room = self.room
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_object_create_form_work_valid(self):
        form = ObjectCreateForm(data={
            'object_type': 'WORK',
            'name': 'Workstation',
            'position_x': 1,
            'position_y': 2,
            'effect': '{"energy": 5}'
        })
        form.room = self.room
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_object_create_form_invalid_object_type(self):
        form = ObjectCreateForm(data={
            'object_type': 'INVALID',
            'name': 'Objeto',
            'position_x': 1,
            'position_y': 2
        })
        form.room = self.room
        self.assertFalse(form.is_valid())
        self.assertIn('object_type', form.errors)

    def test_object_create_form_position_exceeds_room(self):
        form = ObjectCreateForm(data={
            'object_type': 'WORK',
            'name': 'Objeto',
            'position_x': 99,
            'position_y': 2
        })
        form.room = self.room
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)

    def test_object_create_form_box_contents_invalid_json(self):
        form = ObjectCreateForm(data={
            'cell_type': 'CONTAINER',
            'name': 'Caja',
            'position_x': 1,
            'position_y': 2,
            'box_contents': 'no es json'
        })
        form.room = self.room
        self.assertFalse(form.is_valid())
        self.assertIn('__all__', form.errors)
