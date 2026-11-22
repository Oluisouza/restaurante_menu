import copy

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from core.utils import restaurante_atual

from .models import Categoria, Prato


class PratoSerializer(serializers.ModelSerializer):

    class Meta:
        model = Prato
        fields = ['id', 'nome', 'descricao', 'preco', 'categoria', 'imagem', 'disponivel', 'criado_em']
        read_only_fields = ['criado_em']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.restaurante = restaurante_atual(self.context['request'])
        self.fields['categoria'].queryset = Categoria.objects.filter(restaurante=self.restaurante)

    def validate(self, dados):
        # O ModelForm confere as constraints do model; o serializer, não.
        # Montamos o prato como ele ficaria e pedimos ao próprio model que confira:
        # a regra continua num lugar só, e a API responde 400 em vez de 500.
        prato = copy.copy(self.instance) if self.instance else Prato(restaurante=self.restaurante)
        for campo, valor in dados.items():
            setattr(prato, campo, valor)
        try:
            prato.validate_constraints()
        except DjangoValidationError as erro:
            raise serializers.ValidationError(erro.messages)
        return dados

    def create(self, dados):
        return super().create({**dados, 'restaurante': self.restaurante})