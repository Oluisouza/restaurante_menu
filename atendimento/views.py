from django.contrib import messages
from django.shortcuts import get_object_or_404, render, redirect

from .forms import ComandaForm, ItemComandaForm
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

def nova_comanda(request):
    if request.method == 'POST':
        form = ComandaForm(request.POST)
        if form.is_valid():
            comanda = form.save()
            messages.success(request, f'Comanda {comanda.codigo} aberta.')
            return redirect('atendimento:lancar_item', pk = comanda.pk)
    else:
        inicial = {}
        mesa_id = request.GET.get('mesa')
        if mesa_id:
            inicial = {'tipo': Comanda.Tipo.MESA, 'mesa': mesa_id}
        form = ComandaForm(initial=inicial)

    return render(request, 'atendimento/form_comanda.html', {'form': form})

def lancar_item(request, pk):
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=pk)

    if not comanda.esta_aberta:
        messages.error(request, f'A comanda {comanda.codigo} já foi encerrada.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    if request.method == 'POST':
        form = ItemComandaForm(request.POST)
        if form.is_valid():
            item = form.save(commit=False)
            item.comanda = comanda
            item.save()
            messages.success(request, f'{item.quantidade}x {item.descricao_produto} lançado.',)
            if 'salvar_e_novo' in request.POST:
                return redirect('atendimento:lancar_item', pk=comanda.pk)
            return redirect('atendimento:detalhe_comanda', pk=comanda.pk)
    else:
        form = ItemComandaForm()

    contexto = {
        'form': form,
        'comanda': comanda,
        'itens': comanda.itens.select_related('prato', 'combo'),
    }
    return render(request, 'atendimento/form_item.html', contexto)