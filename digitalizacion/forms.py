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
        fields = ['lote', 'document_id', 'tipo', 'titulo', 'creator', 'fecha_documento', 'language', 'rights']
        widgets = {
            'lote': forms.Select(attrs={'class': 'm360-form-control'}),
            'document_id': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'upn_YYYY-MM-DD_NNN'}),
            'tipo': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'Plan de estudios, Examen, Acta...'}),
            'titulo': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'Título del documento'}),
            'creator': forms.TextInput(attrs={'class': 'm360-form-control', 'placeholder': 'Entidad responsable'}),
            'fecha_documento': forms.DateInput(attrs={'class': 'm360-form-control', 'type': 'date'}),
            'language': forms.TextInput(attrs={'class': 'm360-form-control', 'value': 'es'}),
            'rights': forms.TextInput(attrs={'class': 'm360-form-control', 'value': 'Derechos reservados UPN'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.label_suffix = ''
            existing = field.widget.attrs.get('class', '')
            field.widget.attrs['class'] = (existing + ' m360-form-control').strip()

    def clean_document_id(self):
        doc_id = self.cleaned_data['document_id']
        lote = self.cleaned_data.get('lote')
        if lote and DocumentoDigital.objects.filter(lote=lote, document_id=doc_id).exists():
            raise forms.ValidationError(f"El documento '{doc_id}' ya está registrado en este lote.")
        return doc_id

