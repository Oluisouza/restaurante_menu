from django.shortcuts import render

from .models import Categoria, Combo, Prato

def lista_cardapio(request):
    busca = request.GET.get('q', '')
    pratos = Prato.objects.filter(disponivel=True).select_related('categoria')
    if busca:
        pratos = pratos.filter(nome__icontains=busca)

    contexto = {'categorias': Categoria.objects.filter(eh_adicional=False), 'pratos': pratos, 'combos': Combo.objects.filter(disponivel=True).prefetch_related('itens__prato'), 'busca': busca,}
    return render(request, 'cardapio/lista_cardapio.html', contexto)
