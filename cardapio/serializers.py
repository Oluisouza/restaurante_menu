import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Prato


class PratoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Prato
        fields = ['id', 'nome', 'descricao', 'preco', 'categoria', 'imagem', 'disponivel', 'criado_em']
        read_only_fields = ['criado_em']

    def validate(self, dados):
        # O ModelForm confere as constraints do model; o serializer, não.
        # Montamos o prato como ele ficaria e pedimos ao próprio model que confira:
        # a regra continua num lugar só, e a API responde 400 em vez de 500.
        prato = copy.copy(self.instance) if self.instance else Prato()
        for campo, valor in dados.items():
            setattr(prato, campo, valor)
        try:
            prato.validate_constraints()
        except DjangoValidationError as erro:
            raise serializers.ValidationError(erro.messages)
        return dados