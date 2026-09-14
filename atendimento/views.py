from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render, redirect

from .forms import ComandaForm, ItemComandaForm, FechamentoForm
from .models import Comanda, Mesa, ItemComanda

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

def fechar_comanda(request, pk):
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=pk)

    if not comanda.esta_aberta:
        messages.warning(request, f'A comanda {comanda.codigo} já foi encerrada.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    if request.method == 'POST':
        form = FechamentoForm(request.POST, instance=comanda)
        if form.is_valid():
            comanda = form.save(commit=False)
            try:
                comanda.fechar()
            except ValidationError as erro:
                form.add_error(None, erro)
            else:
                messages.success(request, f'Comanda {comanda.codigo} fechada - R$ {comanda.total_pago:.2f}.')
                return redirect('atendimento:detalhe_comanda', pk=comanda.pk)
    else: 
        form = FechamentoForm(instance=comanda)

    nao_entregues = comanda.itens_validos.exclude(status=ItemComanda.Status.ENTREGUE).count()

    contexto = {
        'comanda': comanda,
        'form': form,
        'itens': comanda.itens_validos.select_related('prato', 'combo'),
        'nao_entregues': nao_entregues,
    }
    return render(request, 'atendimento/fechar_comanda.html', contexto)

def cancelar_comanda(request, pk):
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=pk)

    if request.method == 'POST':
        try:
            comanda.cancelar()
        except ValidationError as erro:
            messages.error(request, '; '.join(erro.messages))
        else:
            messages.success(request, f'Comanda {comanda.codigo} cancelada.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    return render(request, 'atendimento/confirmar_cancelamento.html', {'comanda': comanda})