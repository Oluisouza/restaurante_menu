from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate

from .models import Comanda, ItemComanda


def comandas_fechadas(restaurante, inicio=None, fim=None):
    fechadas = Comanda.objects.filter(restaurante=restaurante, status=Comanda.Status.FECHADA)
    if inicio:
        fechadas = fechadas.filter(fechada_em__date__gte=inicio)
    if fim:
        fechadas = fechadas.filter(fechada_em__date__lte=fim)
    return fechadas


def indicadores(fechadas):
    """KPI: os números grandes dos cartões, numa consulta só."""
    return fechadas.aggregate(
        faturamento=Sum('total_pago'),
        quantidade=Count('id'),
        ticket_medio=Avg('total_pago'),
        descontos=Sum('desconto'),
    )


def mais_vendidos(fechadas, limite=10):
    """Ranking: os itens que mais saíram, em unidades."""
    return (
        ItemComanda.objects
        .filter(comanda__in=fechadas)
        .exclude(status=ItemComanda.Status.CANCELADO)
        .values('prato__nome', 'combo__nome')
        .annotate(unidades=Sum('quantidade'))
        .order_by('-unidades')[:limite]
    )


def por_pagamento(fechadas):
    """Distribuição: quanto entrou por cada forma de pagamento."""
    rotulos = dict(Comanda.FormaPagamento.choices)
    return [
        {**linha, 'rotulo': rotulos.get(linha['forma_pagamento'], '—')}
        for linha in (
            fechadas.values('forma_pagamento')
            .annotate(total=Sum('total_pago'), quantidade=Count('id'))
            .order_by('-total')
        )
    ]


def faturamento_por_dia(fechadas):
    """Série no tempo: o faturamento de cada dia do período, em ordem."""
    return (
        fechadas.annotate(dia=TruncDate('fechada_em'))
        .values('dia')
        .annotate(total=Sum('total_pago'), quantidade=Count('id'))
        .order_by('dia')
    )


def serie_diaria(fechadas, inicio, fim):
    """A série pronta para o gráfico: todos os dias do período, inclusive os sem venda."""
    por_dia = {linha['dia']: linha['total'] for linha in faturamento_por_dia(fechadas)}
    dias = (inicio + timedelta(days=n) for n in range((fim - inicio).days + 1))
    return [{'dia': dia.strftime('%d/%m'), 'total': por_dia.get(dia, Decimal('0'))} for dia in dias]