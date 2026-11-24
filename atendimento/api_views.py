from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.utils import restaurante_atual

from . import dashboard
from .views import _periodo


class DashboardApi(APIView):
    """Os números do dashboard em JSON: mesmas funções, mesmo período, mesmo restaurante."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        form, inicio, fim = _periodo(request)
        if form.errors:
            return Response(form.errors, status=400)

        fechadas = dashboard.comandas_fechadas(restaurante_atual(request), inicio, fim)
        return Response({
            'inicio': inicio,
            'fim': fim,
            'indicadores': dashboard.indicadores(fechadas),
            'mais_vendidos': [
                {'item': linha['prato__nome'] or linha['combo__nome'], 'unidades': linha['unidades']}
                for linha in dashboard.mais_vendidos(fechadas)
            ],
            'por_pagamento': [
                {'forma': linha['rotulo'], 'comandas': linha['quantidade'], 'total': linha['total']}
                for linha in dashboard.por_pagamento(fechadas)
            ],
        })