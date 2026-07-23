from django import forms
from .models import LoteDigitalizacion, DocumentoDigital


class LoteDigitalizacionForm(forms.ModelForm):
    class Meta:
        model = LoteDigitalizacion
        fields = ['nombre', 'proyecto_m360', 'curso_m360', 'ruta_base', 'metadata_proyecto']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'Ej: LOTE_20260719_001 - Archivo Central'}),
            'ruta_base': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': '/ruta/a/documentos'}),
            'metadata_proyecto': forms.Textarea(attrs={'class': 'm360-form-control', 'rows': 3, 'placeholder': '{"origen": "Archivo Central", "fecha_recepcion": "2026-07-19"}'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label_suffix = ''
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' m360-form-control').strip()


class DocumentoDigitalForm(forms.ModelForm):
    class Meta:
        model = DocumentoDigital
        fields = [
            'lote', 'document_id', 'tipo', 'titulo', 'creator',
            'fecha_documento', 'language', 'rights',
            'estado_conservacion', 'grapas_detectadas', 'objetos_ajenos',
            'foliado_aplicado', 'folios', 'observaciones_preparacion',
        ]
        widgets = {
            'lote': forms.Select(attrs={'class': 'm360-form-control'}),
            'document_id': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'upn_YYYY-MM-DD_NNN'}),
            'tipo': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'Plan de estudios, Examen, Acta...'}),
            'titulo': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'Título del documento'}),
            'creator': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'Entidad responsable'}),
            'fecha_documento': forms.DateInput(attrs={'class': 'm360-form-control', 'type': 'date'}),
            'language': forms.TextInput(attrs={'class': 'm360-form-control', 'value': 'es'}),
            'rights': forms.TextInput(attrs={'class': 'm360-form-control', 'value': 'Derechos reservados UPN'}),
            'estado_conservacion': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'Bueno / Regular / Crítico'}),
            'grapas_detectadas': forms.CheckboxInput(attrs={'class': 'm360-checkbox'}),
            'objetos_ajenos': forms.Textarea(attrs={'class': 'm360-form-control', 'rows': 2, 'placeholder': 'Post-its, clips, notas...'}),
            'foliado_aplicado': forms.CheckboxInput(attrs={'class': 'm360-checkbox'}),
            'folios': forms.NumberInput(attrs={'class': 'm360-form-control', 'placeholder': 'Ej: 7', 'min': '1'}),
            'observaciones_preparacion': forms.Textarea(attrs={'class': 'm360-form-control', 'rows': 2, 'placeholder': 'Reparaciones mínimas, retiros, observaciones del archivero.'}),
        }

    def __init__(self, *args, lote=None, **kwargs):
        super().__init__(*args, **kwargs)
        if lote and 'lote' in self.fields:
            self.fields['lote'].queryset = LoteDigitalizacion.objects.filter(pk=lote.pk)
        for name, field in self.fields.items():
            field.label_suffix = ''
            existing = field.widget.attrs.get('class', '')
            widget_type = field.widget.__class__.__name__
            if widget_type in {'CheckboxInput', 'RadioSelect', 'CheckboxSelectMultiple'}:
                field.widget.attrs['class'] = (existing + ' m360-checkbox').strip()
            else:
                field.widget.attrs['class'] = (existing + ' m360-form-control').strip()

    def clean_document_id(self):
        doc_id = self.cleaned_data['document_id']
        lote = self.cleaned_data.get('lote')
        if lote and DocumentoDigital.objects.filter(lote=lote, document_id=doc_id).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError(f"El documento '{doc_id}' ya está registrado en este lote.")
        return doc_id


