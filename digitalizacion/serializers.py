from rest_framework import serializers
from .models import LoteDigitalizacion, DocumentoDigital, EtapaPipeline, Fedatacion

class EtapaPipelineSerializer(serializers.ModelSerializer):
    class Meta:
        model = EtapaPipeline
        fields = '__all__'


class DocumentoDigitalSerializer(serializers.ModelSerializer):
    class Meta:
        model = DocumentoDigital
        fields = '__all__'


class LoteDigitalizacionSerializer(serializers.ModelSerializer):
    documentos = DocumentoDigitalSerializer(many=True, read_only=True)
    etapas = EtapaPipelineSerializer(many=True, read_only=True)

    class Meta:
        model = LoteDigitalizacion
        fields = '__all__'


class FedatacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Fedatacion
        fields = '__all__'
