from django.contrib import messages
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PratoForm
from .models import Categoria, Combo, Prato

def lista_cardapio(request):
    busca = request.GET.get('q', '')
    pratos = Prato.objects.filter(disponivel=True).select_related('categoria')
    if busca:
        pratos = pratos.filter(nome__icontains=busca)

    contexto = {
        'categorias': Categoria.objects.filter(eh_adicional=False), 
        'pratos': pratos, 
        'combos': Combo.objects.filter(disponivel=True).prefetch_related('itens__prato'), 
        'busca': busca,
    }
    return render(request, 'cardapio/lista_cardapio.html', contexto)

def lista_pratos(request):
    busca = request.GET.get('q', '')
    pratos = Prato.objects.select_related('categoria')
    if busca:
        pratos = pratos.filter(nome__icontains=busca)
    return render(request, 'cardapio/lista_pratos.html', {'pratos': pratos, 'busca': busca})

def form_prato(request, pk=None):
    prato = get_object_or_404(Prato, pk=pk) if pk else None

    if request.method == 'POST':
        form = PratoForm(request.POST, request.FILES, instance=prato)
        if form.is_valid():
            salvo = form.save()
            acao = 'atualizado' if pk else 'cadastrado'
            messages.success(request, f'{salvo.nome} {acao}.')
            return redirect('cardapio:lista_pratos')
    else:
            form = PratoForm(instance=prato)

    return render(request, 'cardapio/form_prato.html', {'form': form, 'prato': prato})

def excluir_prato(request, pk):
    prato = get_object_or_404(Prato, pk=pk)

    if request.method == 'POST':
        nome = prato.nome
        try:
            prato.delete()
        except ProtectedError:
            messages.error(
                request,
                f'{nome} não pode ser excluído porque já foi usado em comandas ou combos. '
                f'marque como indisponível. ',
            )
        else:
            messages.success(request, f'{nome} excluído do cardápio')
        return redirect('cardapio:lista_pratos')

    return render(request, 'cardapio/confirmar_exclusao_prato.html', {'prato': prato})
