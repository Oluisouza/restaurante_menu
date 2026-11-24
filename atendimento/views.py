import csv

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, render, redirect
from django.http import Http404, HttpResponse
from django.db.models import Prefetch
from django.utils import timezone

from datetime import date, timedelta

from core.utils import gerente_requerido, restaurante_atual

from . import dashboard
from .forms import CancelarItemForm, ComandaForm, ItemComandaForm, FechamentoForm, PersonalizarItemForm, PeriodoForm
from .models import Comanda, Mesa, ItemComanda
from cardapio.models import Categoria, Combo, Prato

def _comanda_do_restaurante(request, pk):
    return get_object_or_404(
        Comanda.objects.select_related('mesa'), pk=pk, restaurante=restaurante_atual(request)
    )

def _item_do_restaurante(request, pk):
    return get_object_or_404(
        ItemComanda.objects.select_related('comanda', 'comanda__mesa'),
        pk=pk, comanda__restaurante=restaurante_atual(request),
    )

def salao(request):
    restaurante = restaurante_atual(request)
    abertas = Comanda.objects.filter(
        restaurante=restaurante, status=Comanda.Status.ABERTA
    ).prefetch_related('itens__adicionais')
    mesas = Mesa.objects.filter(restaurante=restaurante, ativa=True).prefetch_related(
        Prefetch('comandas', queryset=abertas, to_attr='abertas')
    )
    contexto = {'mesas': mesas, 'avulsas': abertas.filter(mesa__isnull=True), 'total_abertas': abertas.count(),}
    return render(request, 'atendimento/salao.html', contexto)

def detalhe_comanda(request, pk):
    comanda = _comanda_do_restaurante(request, pk)
    contexto = { 'comanda': comanda, 'itens': comanda.itens.select_related('prato', 'combo'),}
    return render(request, 'atendimento/detalhe_comanda.html', contexto)

def detalhe_mesa(request, pk):
    mesa = get_object_or_404(Mesa, pk=pk, restaurante=restaurante_atual(request))
    contexto = { 'mesa': mesa, 'comandas': mesa.comandas.select_related('mesa').order_by('-aberta_em'),}
    return render(request, 'atendimento/detalhe_mesa.html', contexto)

def lista_comandas(request):
    status = request.GET.get('status', '')
    comandas = (
        Comanda.objects.filter(restaurante=restaurante_atual(request))
        .select_related('mesa')
        .prefetch_related('itens__adicionais')
    )
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
    restaurante = restaurante_atual(request)

    if request.method == 'POST':
        form = ComandaForm(request.POST, instance=Comanda(tipo=tipo_valor), tipo=tipo_valor, restaurante=restaurante)
        if form.is_valid():
            comanda = form.save()
            messages.success(request, f'Comanda {comanda.codigo} aberta.')
            return redirect('atendimento:lancar_item', pk = comanda.pk)
    else:
        inicial = {}
        mesa_id = request.GET.get('mesa')
        if mesa_id and tipo_valor == Comanda.Tipo.MESA:
            inicial['mesa'] = mesa_id
        form = ComandaForm(initial=inicial, instance=Comanda(tipo=tipo_valor), tipo=tipo_valor, restaurante=restaurante)

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
            Prato.objects.select_related('categoria'), pk=_id_valido(prato_id), restaurante=comanda.restaurante
        )
    elif combo_id:
        produto = get_object_or_404(Combo, pk=_id_valido(combo_id), restaurante=comanda.restaurante)
    else:
        messages.error(request, 'Nenhum produto informado.')
        return

    try:
        comanda.lancar(produto)
    except ValidationError as erro:
        messages.error(request, '; '.join(erro.messages))
        return

    messages.success(request, f'{produto.nome} lançado.')

def _ajustar_item(request, comanda, acao):
    item = get_object_or_404(
        ItemComanda, pk=_id_valido(request.POST.get('item')), comanda=comanda
    )
    descricao = item.descricao_produto

    try:
        item.exigir_alteravel()
    except ValidationError as erro:
        messages.error(request, '; '.join(erro.messages))
        return

    if acao == 'incrementar':
        item.quantidade += 1
        item.save(update_fields=['quantidade'])
    elif acao == 'decrementar' and item.quantidade > 1:
        item.quantidade -= 1
        item.save(update_fields=['quantidade'])
    else:
        item.remover()
        messages.success(request, f'{descricao} removido.')

def _personalizar_item(request, comanda):
    item = get_object_or_404(
        ItemComanda, pk=_id_valido(request.POST.get('item')), comanda=comanda
    )
    try:
        item.exigir_alteravel()
    except ValidationError as erro:
        messages.error(request, '; '.join(erro.messages))
        return

    form = PersonalizarItemForm(request.POST, instance=item)
    if form.is_valid():
        form.save()
        messages.success(request, f'{item.descricao_produto} atualizado.')
    else:
        erros = '; '.join(m for lista in form.errors.values() for m in lista)
        messages.error(request, erros)


def lancar_item(request, pk):
    comanda = _comanda_do_restaurante(request, pk)

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
        Categoria.objects.filter(restaurante=comanda.restaurante, eh_adicional=False)
        .prefetch_related(Prefetch(
            'pratos', queryset=Prato.objects.filter(restaurante=comanda.restaurante, disponivel=True)
        ))
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
        'combos': Combo.objects.filter(restaurante=comanda.restaurante, disponivel=True).prefetch_related('itens__prato'),
        'itens': comanda.itens_validos.select_related('prato', 'combo').prefetch_related('adicionais__prato'),
        'item_personalizando': item_personalizando,
        'form_personalizar': form_personalizar,
    }
    return render(request, 'atendimento/pdv.html', contexto)

def fechar_comanda(request, pk):
    comanda = _comanda_do_restaurante(request, pk)

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
    comanda = _comanda_do_restaurante(request, pk)

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
    item = _item_do_restaurante(request, pk)
    comanda = item.comanda

    try:
        item.exigir_alteravel()
    except ValidationError as erro:
        messages.error(request, '; '.join(erro.messages))
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
    item = _item_do_restaurante(request, pk)
    comanda = item.comanda

    try:
        item.exigir_alteravel()
    except ValidationError as erro:
        messages.error(request, '; '.join(erro.messages))
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    if request.method == 'POST':
        descricao = item.descricao_produto
        item.remover()
        messages.success(request, f'{descricao} removido da comanda.')
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    return render(request, 'atendimento/confirmar_exclusao_item.html', {'item': item, 'comanda': comanda}, )

def cozinha(request):
    if request.method == 'POST':
        item = _item_do_restaurante(request, _id_valido(request.POST.get('item')))
        try:
            item.mudar_status(request.POST.get('status'), motivo='Cancelado pela cozinha')
        except ValidationError as erro:
            messages.error(request, '; '.join(erro.messages))
        else:
            messages.success(
                request, f'{item.descricao_produto}: {item.get_status_display()}.'
            )

        return redirect('atendimento:cozinha')

    itens = (
        ItemComanda.objects
        .filter(comanda__restaurante=restaurante_atual(request), comanda__status=Comanda.Status.ABERTA)
        .exclude(status__in=[ItemComanda.Status.ENTREGUE, ItemComanda.Status.CANCELADO])
        .select_related('comanda', 'comanda__mesa', 'prato', 'combo')
        .prefetch_related('adicionais__prato')
        .order_by('criado_em')
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
    restaurante = restaurante_atual(request)
    fechadas = dashboard.comandas_fechadas(restaurante, inicio=dia, fim=dia)
    comandas = Comanda.objects.filter(restaurante=restaurante)

    contexto = {
        'dia': dia,
        'dia_anterior': dia - timedelta(days=1),
        'dia_seguinte': dia + timedelta(days=1),
        'eh_hoje': dia == timezone.localdate(),
        'totais': dashboard.indicadores(fechadas),
        'por_pagamento': dashboard.por_pagamento(fechadas),
        'mais_vendidos': dashboard.mais_vendidos(fechadas),
        'canceladas': comandas.filter(
            status=Comanda.Status.CANCELADA, fechada_em__date=dia
        ).count(),
        'abertas_agora': comandas.filter(status=Comanda.Status.ABERTA).count(),
    }
    return render(request, 'atendimento/resumo.html', contexto)

DIAS_PADRAO = 30

def _periodo(request):
    """Lê o período da URL com um Form: data malformada nunca chega ao ORM."""
    hoje = timezone.localdate()
    padrao = {'inicio': hoje - timedelta(days=DIAS_PADRAO - 1), 'fim': hoje}
    form = PeriodoForm(request.GET or {k: v.isoformat() for k, v in padrao.items()})
    if form.is_valid():
        return form, form.cleaned_data['inicio'], form.cleaned_data['fim']
    return form, padrao['inicio'], padrao['fim']


def painel(request):
    form, inicio, fim = _periodo(request)
    fechadas = dashboard.comandas_fechadas(restaurante_atual(request), inicio, fim)
    eh_gerente = request.user.perfil.eh_gerente
    contexto = {
        'form': form,
        'inicio': inicio,
        'fim': fim,
        'eh_gerente': eh_gerente,
        'indicadores': dashboard.indicadores(fechadas),
        'mais_vendidos': dashboard.mais_vendidos(fechadas),
        'por_pagamento': dashboard.por_pagamento(fechadas),
    }
    if eh_gerente:  # o atendente vê os números do período, sem a série e sem exportar
        contexto['serie'] = dashboard.serie_diaria(fechadas, inicio, fim)
    return render(request, 'atendimento/dashboard.html', contexto)

def _celula_segura(texto):
    """O Excel trata como fórmula a célula que começa com = + - @. Um apóstrofo desarma."""
    texto = str(texto)
    return f"'{texto}" if texto[:1] in ('=', '+', '-', '@') else texto


def _reais(valor):
    return f'{valor:.2f}'.replace('.', ',')

@gerente_requerido
def exportar_csv(request):
    _, inicio, fim = _periodo(request)
    fechadas = (
        dashboard.comandas_fechadas(restaurante_atual(request), inicio, fim)
        .select_related('mesa')
        .order_by('fechada_em')
    )

    resposta = HttpResponse(content_type='text/csv; charset=utf-8')
    resposta['Content-Disposition'] = f'attachment; filename="comandas_{inicio}_a_{fim}.csv"'
    resposta.write('\ufeff')  # BOM: avisa ao Excel que o arquivo é UTF-8

    planilha = csv.writer(resposta, delimiter=';')
    planilha.writerow(['Código', 'Fechada em', 'Tipo', 'Mesa', 'Responsável', 'Pagamento', 'Desconto', 'Total pago'])
    for comanda in fechadas:
        planilha.writerow([
            comanda.codigo,
            timezone.localtime(comanda.fechada_em).strftime('%d/%m/%Y %H:%M'),
            comanda.get_tipo_display(),
            comanda.mesa.identificacao if comanda.mesa else '',
            _celula_segura(comanda.responsavel),
            comanda.get_forma_pagamento_display(),
            _reais(comanda.desconto),
            _reais(comanda.total_pago),
        ])
    return resposta

def cancelar_item(request, pk):
    item = _item_do_restaurante(request, pk)
    comanda = item.comanda

    try:
        item.exigir_cancelavel()
    except ValidationError as erro:
        messages.error(request, '; '.join(erro.messages))
        return redirect('atendimento:detalhe_comanda', pk=comanda.pk)

    if request.method == 'POST':
        form = CancelarItemForm(request.POST)
        if form.is_valid():
            item.cancelar(form.cleaned_data['motivo'])
            messages.success(request, f'{item.descricao_produto} cancelado.')
            return redirect('atendimento:detalhe_comanda', pk=comanda.pk)
    else:
        form = CancelarItemForm()

    return render(request, 'atendimento/confirmar_cancelamento_item.html', {'form': form, 'item': item, 'comanda': comanda})