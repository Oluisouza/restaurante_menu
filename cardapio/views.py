from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import restaurante_atual

from .forms import PratoForm
from .models import Categoria, Combo, Prato

def filtrar_pratos(request, pratos):
    busca = request.GET.get('q', '').strip()
    categoria_id = request.GET.get('categoria', '')

    filtros = Q()
    if busca:
        filtros &= Q(nome__icontains=busca) | Q(descricao__icontains=busca)
    if categoria_id.isdigit():
        filtros &= Q(categoria_id=categoria_id)

    return pratos.filter(filtros), busca, categoria_id

def filtrar_combos(combos, busca, categoria_id):
    if busca:
        combos = combos.filter(
            Q(nome__icontains=busca)
            | Q(descricao__icontains=busca)
            | Q(itens__prato__nome__icontains=busca)
        )
    if categoria_id.isdigit():
        combos = combos.filter(itens__prato__categoria_id=categoria_id)
    return combos.distinct()

def lista_cardapio(request):
    restaurante = restaurante_atual(request)
    pratos, busca, categoria_id = filtrar_pratos(
        request, Prato.objects.filter(restaurante=restaurante, disponivel=True).select_related('categoria')
    )
    categorias = Categoria.objects.filter(restaurante=restaurante, eh_adicional=False)

    secoes = []
    for categoria in categorias:
        itens = [prato for prato in pratos if prato.categoria_id == categoria.id]
        if itens:
            secoes.append({'categoria': categoria, 'pratos': itens})

    contexto = {
        'secoes': secoes,
        'categorias': categorias,
        'combos': filtrar_combos(
            Combo.objects.filter(restaurante=restaurante, disponivel=True).prefetch_related('itens__prato'),
            busca, categoria_id,
        ),
        'busca': busca,
        'categoria_selecionada': categoria_id,
    }
    return render(request, 'cardapio/lista_cardapio.html', contexto)

def lista_pratos(request):
    restaurante = restaurante_atual(request)
    pratos, busca, categoria_id = filtrar_pratos(
        request, Prato.objects.filter(restaurante=restaurante).select_related('categoria')
    )
    contexto = {
        'pratos': pratos,
        'busca': busca,
        'categorias': Categoria.objects.filter(restaurante=restaurante),
        'categoria_selecionada': categoria_id,
    }
    return render(request, 'cardapio/lista_pratos.html', contexto)

def form_prato(request, pk=None):
    restaurante = restaurante_atual(request)
    prato = get_object_or_404(Prato, pk=pk, restaurante=restaurante) if pk else None

    if request.method == 'POST':
        form = PratoForm(request.POST, request.FILES, instance=prato, restaurante=restaurante)
        if form.is_valid():
            salvo = form.save()
            acao = 'atualizado' if pk else 'cadastrado'
            messages.success(request, f'{salvo.nome} {acao}.')
            return redirect('cardapio:lista_pratos')
    else:
        form = PratoForm(instance=prato, restaurante=restaurante)

    return render(request, 'cardapio/form_prato.html', {'form': form, 'prato': prato})

def excluir_prato(request, pk):
    prato = get_object_or_404(Prato, pk=pk, restaurante=restaurante_atual(request))

    if request.method == 'POST':
        nome = prato.nome
        try:
            prato.delete()
        except ProtectedError:
            messages.error(
                request,
                f'{nome} não pode ser excluído porque já foi usado em comandas '
                f'ou comboas. Marque como indisponível. ',
            )
        else:
            messages.success(request, f'{nome} excluído do cardápio')
        return redirect('cardapio:lista_pratos')

    return render(request, 'cardapio/confirmar_exclusao_prato.html', {'prato': prato})