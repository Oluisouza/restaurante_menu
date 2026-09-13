from django.shortcuts import get_object_or_404, render

from .models import Comanda, Mesa

def salao(request):
    mesas = Mesa.objects.filter(ativa=True)
    avulsas = Comanda.objects.filter(status=Comanda.Status.ABERTA, mesa__isnull=True,)
    contexto = {'mesas': mesas, 'avulsas': avulsas, 'total_abertas': Comanda.objects.filter(status=Comanda.Status.ABERTA).count(),}
    return render(request, 'atendimento/salao.html', contexto)

def detalhe_comanda(request, pk):
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=pk)
    contexto = { 'comanda': comanda, 'itens': comanda.itens.select_related('prato', 'combo'),}
    return render(request, 'atendimento/detalhe_comanda.html', contexto)

def detalhe_mesa(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk)
    contexto = { 'mesa': mesa, 'comandas': mesa.comandas.select_related('mesa').order_by('-aberta_em'),}
    return render(request, 'atendimento/detalhe_mesa.html', contexto)

def lista_comandas(request):
    status = request.GET.get('status', '')
    comandas = Comanda.objects.select_related('mesa')
    if status:
        comandas = comandas.filter(status=status)
    contexto = {'comandas': comandas, 'status_selecionado': status, 'status_opcoes': Comanda.Status.choices,}
    return render(request, 'atendimento/lista_comandas.html', contexto)