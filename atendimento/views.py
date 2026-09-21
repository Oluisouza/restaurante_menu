from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404
from django.db.models import Avg, Count, Prefetch, Sum
from django.utils import timezone

from datetime import date, timedelta

from .forms import ComandaForm, ItemComandaForm, FechamentoForm, PersonalizarItemForm
from .models import Comanda, Mesa, ItemComanda
from cardapio.models import Categoria, Combo, Prato

def salao(request):
    mesas = Mesa.objects.filter(ativa=True)
    avulsas = Comanda.objects.filter(status=Comanda.Status.ABERTA, mesa__isnull=True,)
    contexto = {'mesas': mesas, 'avulsas': avulsas, 'total_abertas': Comanda.objects.filter(status=Comanda.Status.ABERTA).count(),}
    return render(request, 'atendimento/salao.html', contexto)

def detalhe_comanda(request, pk):
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=pk)
    contexto = { 'comanda': comanda, 'itens': comanda.itens_validos.select_related('prato', 'combo'),}
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

TIPOS_POR_URL = {
    'mesa': Comanda.Tipo.MESA,
    'viagem': Comanda.Tipo.VIAGEM,
    'balcao': Comanda.Tipo.BALCAO,
}

def nova_comanda(request, tipo):
    tipo_valor = TIPOS_POR_URL.get(tipo)
    if tipo_valor is None:
        raise Http404('Tipo de atendimento inválido.')
    
    if request.method == 'POST':
        form = ComandaForm(request.POST, instance=Comanda(tipo=tipo_valor), tipo=tipo_valor)
        if form.is_valid():
            comanda = form.save()
            messages.success(request, f'Comanda {comanda.codigo} aberta.')
            return redirect('atendimento:lancar_item', pk = comanda.pk)
    else:
        inicial = {}
        mesa_id = request.GET.get('mesa')
        if mesa_id and tipo_valor == Comanda.Tipo.MESA:
            inicial['mesa'] = mesa_id
        form = ComandaForm(initial=inicial, instance=Comanda(tipo=tipo_valor), tipo=tipo_valor)

    contexto = {
        'form': form,
        'tipo': tipo_valor,
        'rotulo_tipo': dict(Comanda.Tipo.choices)[tipo_valor],
    }

    return render(request, 'atendimento/form_comanda.html', contexto)

def _id_valido(valor):
    """Converte um id vindo do cliente; qualquer coisa que nao seja numero vira 404."""
    if not (valor or '').isdigit():
        raise Http404('Identificador inválido.')
    return int(valor)


def _adicionar_produto(request, comanda):
    prato_id = request.POST.get('prato')
    combo_id = request.POST.get('combo')

    if prato_id:
        produto = get_object_or_404(
            Prato, pk=_id_valido(prato_id), categoria__eh_adicional=False
        )
        chave = {'prato': produto, 'combo': None}
    elif combo_id:
        produto = get_object_or_404(Combo, pk=_id_valido(combo_id))
        chave = {'prato': None, 'combo': produto}
    else:
        messages.error(request, 'Nenhum produto informado.')
        return

    if not produto.disponivel:
        messages.error(request, f'{produto.nome} acabou de ficar indisponível.')
        return

    existente = comanda.itens.filter(
        status=ItemComanda.Status.PENDENTE, observacao='', adicionais__isnull=True, **chave
    ).first()

    if existente:
        existente.quantidade += 1
        existente.save(update_fields=['quantidade'])
    else:
        ItemComanda.objects.create(comanda=comanda, quantidade=1, **chave)

    messages.success(request, f'{produto.nome} lançado.')

def _ajustar_item(request, comanda, acao):
    item = get_object_or_404(
        ItemComanda, pk=_id_valido(request.POST.get('item')), comanda=comanda
    )
    descricao = item.descricao_produto

    if acao != 'remover' and item.status != ItemComanda.Status.PENDENTE:
        messages.error(request, 'Este item já foi para a cozinha. Lance o produto de novo.')
        return

    if acao == 'incrementar':
        item.quantidade += 1
        item.save(update_fields=['quantidade'])
    elif acao == 'decrementar' and item.quantidade > 1:
        item.quantidade -= 1
        item.save(update_fields=['quantidade'])
    else:
        item.delete()
        messages.success(request, f'{descricao} removido.')

def _personalizar_item(request, comanda):
    item = get_object_or_404(
        ItemComanda, pk=_id_valido(request.POST.get('item')), comanda=comanda
    )
    if item.status != ItemComanda.Status.PENDENTE:
        messages.error(request, 'Este item já foi para a cozinha.')
        return

    form = PersonalizarItemForm(request.POST, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, f'{item.descricao_produto} atualizado.')
    else:
        erros = '; '.join(m for lista in form.errors.values() for m in lista)
        messages.error(request, erros)


def lancar_item(request, pk):
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=pk)

    if not comanda.esta_aberta:
        messages.error(request, f'A comanda {comanda.codigo} já foi encerrada.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'adicionar':
            _adicionar_produto(request, comanda)
        elif acao in ('incrementar', 'decrementar', 'remover'):
            _ajustar_item(request, comanda, acao)
        elif acao == 'personalizar':
            _personalizar_item(request, comanda)
        else:
            messages.error(request, 'Ação desconhecida.')
        return redirect('atendimento:lancar_item', pk=comanda.pk)

    categorias = (
        Categoria.objects.filter(eh_adicional=False)
        .prefetch_related(Prefetch('pratos', queryset=Prato.objects.filter(disponivel=True)))
    )

    item_personalizando = None
    form_personalizar = None
    alvo = request.GET.get('personalizar', '')
    if alvo.isdigit():
        item_personalizando = comanda.itens.filter(
            pk=alvo, status=ItemComanda.Status.PENDENTE
        ).first()
        if item_personalizando:
            form_personalizar = PersonalizarItemForm(instance=item_personalizando)

    contexto = {
        'comanda': comanda,
        'categorias': categorias,
        'combos': Combo.objects.filter(disponivel=True).prefetch_related('itens__prato'),
        'itens': comanda.itens_validos.select_related('prato', 'combo').prefetch_related('adicionais__prato'),
        'item_personalizando': item_personalizando,
        'form_personalizar': form_personalizar,
    }
    return render(request, 'atendimento/pdv.html', contexto)

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
        'itens': comanda.itens_validos.select_related('prato', 'combo').prefetch_related('adicionais__prato'),
        'nao_entregues': nao_entregues,
    }
    return render(request, 'atendimento/fechar_comanda.html', contexto)

def cancelar_comanda(request, pk):
    comanda = get_object_or_404(Comanda.objects.select_related('mesa'), pk=pk)

    if not comanda.esta_aberta:
        messages.warning(request, f'A comanda {comanda.codigo} já foi encerrada.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    if request.method == 'POST':
        try:
            comanda.cancelar()
        except ValidationError as erro:
            messages.error(request, '; '.join(erro.messages))
        else:
            messages.success(request, f'Comanda {comanda.codigo} cancelada.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    return render(request, 'atendimento/confirmar_cancelamento.html', {'comanda': comanda})

def editar_item(request, pk):
    item = get_object_or_404(ItemComanda.objects.select_related('comanda', 'comanda__mesa'), pk=pk)
    comanda = item.comanda

    if not comanda.esta_aberta:
        messages.error(request, f'A comanda {comanda.codigo} já foi encerrada.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    if request.method == 'POST':
        form = ItemComandaForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item atualizado.')
            return redirect('atendimento:detalhe_comanda', pk=comanda.pk)
    else:
        form = ItemComandaForm(instance=item)

    return render(request, 'atendimento/form_item_edicao.html', {'form': form, 'item': item, 'comanda': comanda},)

def excluir_item(request, pk):
    item = get_object_or_404(ItemComanda.objects.select_related('comanda'), pk=pk)
    comanda = item.comanda

    if not comanda.esta_aberta:
        messages.error(request, f'A comanda {comanda.codigo} já foi encerrada.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    if request.method == 'POST':
        descricao = item.descricao_produto
        item.delete()
        messages.success(request, f'{descricao} removido da comanda.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    return render(request, 'atendimento/confirmar_exclusao_item.html', {'item': item, 'comanda': comanda}, )

def cozinha(request):
    TRANSICOES = {
        ItemComanda.Status.PENDENTE: [ItemComanda.Status.EM_PREPARO, ItemComanda.Status.CANCELADO],
        ItemComanda.Status.EM_PREPARO: [ItemComanda.Status.PRONTO, ItemComanda.Status.CANCELADO],
        ItemComanda.Status.PRONTO: [ItemComanda.Status.ENTREGUE],
        ItemComanda.Status.ENTREGUE: [],
        ItemComanda.Status.CANCELADO: [],
    }

    if request.method == 'POST':
        item = get_object_or_404(
            ItemComanda.objects.select_related('comanda'), pk=_id_valido(request.POST.get('item'))
        )
        novo_status = request.POST.get('status')

        if not item.comanda.esta_aberta:
            messages.error(request, 'A comanda deste item já foi encerrada.')
        elif novo_status not in TRANSICOES[item.status]:
            messages.error(request, 'Essa mudança de status não é permitida.')
        else:
            item.status = novo_status
            item.save(update_fields=['status'])
            messages.success(
                request, f'{item.descricao_produto}: {item.get_status_display()}.'
            )

        return redirect('atendimento:cozinha')

    itens = (
        ItemComanda.objects.filter(comanda__status=Comanda.Status.ABERTA).exclude(status__in=[ItemComanda.Status.ENTREGUE, ItemComanda.Status.CANCELADO]).select_related('comanda', 'comanda__mesa', 'prato', 'combo').prefetch_related('adicionais__prato').order_by('criado_em')
    )
    return render(request, 'atendimento/cozinha.html', {'itens': itens})

def _data_do_resumo(request):
    texto = request.GET.get('data', '')
    try:
        return date.fromisoformat(texto)
    except ValueError:
        return timezone.localdate()


def resumo(request):
    dia = _data_do_resumo(request)

    fechadas = Comanda.objects.filter(
        status=Comanda.Status.FECHADA, fechada_em__date=dia
    )
    totais = fechadas.aggregate(
        faturamento=Sum('total_pago'),
        quantidade=Count('id'),
        ticket_medio=Avg('total_pago'),
        descontos=Sum('desconto'),
    )

    rotulos = dict(Comanda.FormaPagamento.choices)
    por_pagamento = [
        {**linha, 'rotulo': rotulos.get(linha['forma_pagamento'], '—')}
        for linha in (
            fechadas.values('forma_pagamento')
            .annotate(total=Sum('total_pago'), quantidade=Count('id'))
            .order_by('-total')
        )
    ]

    mais_vendidos = (
        ItemComanda.objects
        .filter(comanda__in=fechadas)
        .exclude(status=ItemComanda.Status.CANCELADO)
        .values('prato__nome', 'combo__nome')
        .annotate(unidades=Sum('quantidade'))
        .order_by('-unidades')[:10]
    )

    contexto = {
        'dia': dia,
        'dia_anterior': dia - timedelta(days=1),
        'dia_seguinte': dia + timedelta(days=1),
        'eh_hoje': dia == timezone.localdate(),
        'totais': totais,
        'por_pagamento': por_pagamento,
        'mais_vendidos': mais_vendidos,
        'canceladas': Comanda.objects.filter(
            status=Comanda.Status.CANCELADA, fechada_em__date=dia
        ).count(),
        'abertas_agora': Comanda.objects.filter(status=Comanda.Status.ABERTA).count(),
    }
    return render(request, 'atendimento/resumo.html', contexto)