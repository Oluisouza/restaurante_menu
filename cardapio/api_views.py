from django.db.models import ProtectedError
from rest_framework import generics
from rest_framework.exceptions import ValidationError

from .models import Prato
from .serializers import PratoSerializer


class PratoListCreate(generics.ListCreateAPIView):
    queryset = Prato.objects.all()
    serializer_class = PratoSerializer


class PratoDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Prato.objects.all()
    serializer_class = PratoSerializer

    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError(
                f'{instance.nome} já foi usado em comandas ou combos. Marque como indisponível.'
            )