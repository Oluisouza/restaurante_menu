from django.db.models import ProtectedError
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated

from core.permissoes import GerenteAltera
from core.utils import restaurante_atual

from .models import Prato
from .serializers import PratoSerializer


class PratosDoRestaurante:
    """A API só enxerga os pratos do restaurante de quem pede."""

    serializer_class = PratoSerializer
    permission_classes = [IsAuthenticated, GerenteAltera]

    def get_queryset(self):
        return Prato.objects.filter(restaurante=restaurante_atual(self.request))


class PratoListCreate(PratosDoRestaurante, generics.ListCreateAPIView):
    pass


class PratoDetail(PratosDoRestaurante, generics.RetrieveUpdateDestroyAPIView):

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(
                f'{instance.nome} já foi usado em comandas ou combos. Marque como indisponível.'
            )