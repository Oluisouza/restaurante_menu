from decimal import Decimal

from django.contrib import admin
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction

from cardapio.models import Categoria, Prato

from .admin import ComandaAdmin, ItemComandaAdmin
from .models import Comanda, ItemComanda, Mesa


class RotasTest(TestCase):
    """Garante que toda tela responde 200 e que os links montam."""

    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nome='Cafés', ordem=1)
        cls.prato = Prato.objects.create(
            nome='Espresso', preco=Decimal('6.00'), categoria=cls.categoria
        )
        cls.mesa = Mesa.objects.create(identificacao='01', capacidade=4)
        cls.comanda = Comanda.objects.create(
            tipo=Comanda.Tipo.MESA, mesa=cls.mesa, responsavel='Teste'
        )
        ItemComanda.objects.create(
            comanda=cls.comanda, prato=cls.prato, quantidade=2
        )

    def test_telas_sem_parametro(self):
        for nome in [
            'atendimento:salao',
            'atendimento:lista_comandas',
            'atendimento:cozinha',
            'atendimento:resumo',
            'cardapio:lista_cardapio',
            'cardapio:lista_pratos',
            'cardapio:novo_prato',
        ]:
            with self.subTest(rota=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200)

    def test_abertura_por_tipo(self):
        for tipo in ['mesa', 'viagem', 'balcao']:
            with self.subTest(tipo=tipo):
                url = reverse('atendimento:nova_comanda', args=[tipo])
                self.assertEqual(url, f'/comandas/nova/{tipo}/')
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_telas_da_comanda(self):
        pk = self.comanda.pk
        for nome in [
            'atendimento:detalhe_comanda',
            'atendimento:lancar_item',
            'atendimento:fechar_comanda',
            'atendimento:cancelar_comanda',
        ]:
            with self.subTest(rota=nome):
                url = reverse(nome, args=[pk])
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_telas_do_item(self):
        item = self.comanda.itens.first()
        for nome in ['atendimento:editar_item', 'atendimento:excluir_item']:
            with self.subTest(rota=nome):
                url = reverse(nome, args=[item.pk])
                self.assertEqual(self.client.get(url).status_code, 200)


class RegrasTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nome='Cafés', ordem=1)
        cls.prato = Prato.objects.create(
            nome='Espresso', preco=Decimal('6.00'), categoria=cls.categoria
        )

    def _comanda_com_item(self, preco='12.25', quantidade=1):
        prato = Prato.objects.create(
            nome=f'Item {preco}-{quantidade}',
            preco=Decimal(preco),
            categoria=self.categoria,
        )
        comanda = Comanda.objects.create(tipo=Comanda.Tipo.VIAGEM, responsavel='X')
        ItemComanda.objects.create(comanda=comanda, prato=prato, quantidade=quantidade)
        return comanda

    def test_preco_e_snapshot(self):
        comanda = self._comanda_com_item('6.00')
        item = comanda.itens.get()
        item.prato.preco = Decimal('99.00')
        item.prato.save()
        item.quantidade = 2
        item.save()
        item.refresh_from_db()
        self.assertEqual(item.preco_unitario, Decimal('6.00'))
        self.assertEqual(comanda.subtotal, Decimal('12.00'))

    def test_nao_fecha_sem_itens(self):
        comanda = Comanda.objects.create(tipo=Comanda.Tipo.VIAGEM, responsavel='X')
        with self.assertRaises(ValidationError):
            comanda.fechar(Comanda.FormaPagamento.PIX)

    def test_desconto_maior_que_conta(self):
        comanda = self._comanda_com_item('6.00')
        comanda.desconto = Decimal('999.00')
        with self.assertRaises(ValidationError):
            comanda.fechar(Comanda.FormaPagamento.PIX)

    def test_taxa_arredonda_para_cima(self):
        casos = [('12.25', '1.23'), ('0.05', '0.01'), ('100.45', '10.05'), ('12.24', '1.22')]
        for subtotal, esperado in casos:
            with self.subTest(subtotal=subtotal):
                comanda = self._comanda_com_item(subtotal)
                comanda.taxa_servico = True
                self.assertEqual(comanda.valor_taxa_servico, Decimal(esperado))

    def test_total_pago_congela(self):
        comanda = self._comanda_com_item('10.00')
        comanda.fechar(Comanda.FormaPagamento.PIX)
        item = comanda.itens.get()
        item.prato.preco = Decimal('50.00')
        item.prato.save()
        ItemComanda.objects.create(comanda=comanda, prato=item.prato)
        comanda.refresh_from_db()
        self.assertEqual(comanda.status, Comanda.Status.FECHADA)
        self.assertEqual(comanda.total_pago, Decimal('10.00'))

    def test_mesa_ocupada_enquanto_houver_comanda(self):
        mesa = Mesa.objects.create(identificacao='99', capacidade=2)
        comanda = Comanda.objects.create(
            tipo=Comanda.Tipo.MESA, mesa=mesa, responsavel='A'
        )
        ItemComanda.objects.create(comanda=comanda, prato=self.prato, quantidade=1)
        self.assertTrue(mesa.ocupada)
        comanda.fechar(Comanda.FormaPagamento.PIX)
        self.assertFalse(mesa.ocupada)

    def test_comandas_individuais_na_mesma_mesa(self):
        mesa = Mesa.objects.create(identificacao='98', capacidade=4)
        for nome in ['Ana', 'Bruno']:
            Comanda.objects.create(tipo=Comanda.Tipo.MESA, mesa=mesa, responsavel=nome)
        self.assertEqual(mesa.comandas_abertas.count(), 2)

    def test_excluir_prato_vendido_e_recusado(self):
        comanda = self._comanda_com_item('6.00')
        prato = comanda.itens.get().prato
        url = reverse('cardapio:excluir_prato', args=[prato.pk])
        resposta = self.client.post(url, follow=True)
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'não pode ser excluído')
        self.assertTrue(Prato.objects.filter(pk=prato.pk).exists())

    def test_transicoes_da_cozinha(self):
        comanda = self._comanda_com_item('6.00')
        item = comanda.itens.get()
        url = reverse('atendimento:cozinha')

        self.client.post(url, {'item': item.pk, 'status': 'ENTREGUE'})
        item.refresh_from_db()
        self.assertEqual(item.status, ItemComanda.Status.PENDENTE)

        self.client.post(url, {'item': item.pk, 'status': 'EM_PREPARO'})
        item.refresh_from_db()
        self.assertEqual(item.status, ItemComanda.Status.EM_PREPARO)

        for status in ['PRONTO', 'ENTREGUE', 'PENDENTE']:
            self.client.post(url, {'item': item.pk, 'status': status})
        item.refresh_from_db()
        self.assertEqual(item.status, ItemComanda.Status.ENTREGUE)

        outro = ItemComanda.objects.create(comanda=comanda, prato=item.prato)
        comanda.fechar(Comanda.FormaPagamento.PIX)
        self.client.post(url, {'item': outro.pk, 'status': 'CANCELADO'})
        outro.refresh_from_db()
        self.assertEqual(outro.status, ItemComanda.Status.PENDENTE)

    def test_mais_e_menos_so_em_item_pendente(self):
        comanda = self._comanda_com_item('6.00')
        item = comanda.itens.get()
        ItemComanda.objects.filter(pk=item.pk).update(status=ItemComanda.Status.ENTREGUE)
        url = reverse('atendimento:lancar_item', args=[comanda.pk])
        self.client.post(url, {'acao': 'incrementar', 'item': item.pk})
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 1)

class ConstraintsTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nome='Cafés', ordem=1)
        cls.prato = Prato.objects.create(
            nome='Espresso', preco=Decimal('6.00'), categoria=cls.categoria
        )
        cls.mesa = Mesa.objects.create(identificacao='01', capacidade=4)

    def _deve_bloquear(self, funcao):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                funcao()

    def test_preco_negativo_bloqueado(self):
        self._deve_bloquear(lambda: Prato.objects.create(
            nome='Grátis', preco=Decimal('-1'), categoria=self.categoria
        ))

    def test_desconto_negativo_bloqueado(self):
        self._deve_bloquear(lambda: Comanda.objects.create(
            tipo=Comanda.Tipo.MESA, mesa=self.mesa, desconto=Decimal('-5')
        ))

    def test_comanda_mesa_exige_mesa(self):
        self._deve_bloquear(lambda: Comanda.objects.create(tipo=Comanda.Tipo.MESA))

    def test_comanda_viagem_nao_aceita_mesa(self):
        self._deve_bloquear(lambda: Comanda.objects.create(
            tipo=Comanda.Tipo.VIAGEM, mesa=self.mesa
        ))

    def test_capacidade_minima_da_mesa(self):
        self._deve_bloquear(lambda: Mesa.objects.create(
            identificacao='99', capacidade=0
        ))

    def test_estados_legitimos_continuam_passando(self):
        Prato.objects.create(nome='Cortesia', preco=Decimal('0'), categoria=self.categoria)
        Comanda.objects.create(tipo=Comanda.Tipo.VIAGEM, responsavel='Ana')
        Comanda.objects.create(tipo=Comanda.Tipo.MESA, mesa=self.mesa, responsavel='Bruno')
        Comanda.objects.create(tipo=Comanda.Tipo.MESA, mesa=self.mesa, responsavel='Carla')
        self.assertEqual(self.mesa.comandas_abertas.count(), 2)

class ResumoTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cat = Categoria.objects.create(nome='Cafés', ordem=1)
        cls.espresso = Prato.objects.create(
            nome='Espresso', preco=Decimal('6.00'), categoria=cls.cat
        )
        cls.url = reverse('atendimento:resumo')

    def _fechada(self, quantidade, forma=Comanda.FormaPagamento.PIX):
        comanda = Comanda.objects.create(tipo=Comanda.Tipo.VIAGEM, responsavel='x')
        ItemComanda.objects.create(comanda=comanda, prato=self.espresso, quantidade=quantidade)
        comanda.fechar(forma)
        return comanda

    def test_dia_sem_vendas(self):
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['totais']['quantidade'], 0)
        self.assertContains(resposta, 'Nenhuma venda neste dia')

    def test_soma_so_comandas_fechadas(self):
        self._fechada(2)
        self._fechada(1)
        aberta = Comanda.objects.create(tipo=Comanda.Tipo.VIAGEM, responsavel='a')
        ItemComanda.objects.create(comanda=aberta, prato=self.espresso, quantidade=10)
        cancelada = Comanda.objects.create(tipo=Comanda.Tipo.VIAGEM, responsavel='c')
        ItemComanda.objects.create(comanda=cancelada, prato=self.espresso, quantidade=10)
        cancelada.cancelar()
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.context['totais']['faturamento'], Decimal('18.00'))
        self.assertEqual(resposta.context['totais']['quantidade'], 2)
        self.assertEqual(resposta.context['canceladas'], 1)

    def test_mais_vendidos_soma_as_quantidades(self):
        self._fechada(2)
        comanda = self._fechada(3)
        cancelado = ItemComanda.objects.create(
            comanda=comanda, prato=self.espresso, quantidade=7
        )
        ItemComanda.objects.filter(pk=cancelado.pk).update(status=ItemComanda.Status.CANCELADO)
        linha = self.client.get(self.url).context['mais_vendidos'][0]
        self.assertEqual(linha['prato__nome'], 'Espresso')
        self.assertEqual(linha['unidades'], 5)

    def test_data_invalida_cai_em_hoje(self):
        for data in ['abc', '2026-13-45', '']:
            with self.subTest(data=data):
                resposta = self.client.get(self.url, {'data': data})
                self.assertEqual(resposta.status_code, 200)
                self.assertTrue(resposta.context['eh_hoje'])

class PersonalizarItemTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.cat = Categoria.objects.create(nome='Cafés', ordem=1)
        cls.adic = Categoria.objects.create(nome='Adicionais', ordem=9, eh_adicional=True)
        cls.espresso = Prato.objects.create(
            nome='Espresso', preco=Decimal('6.00'), categoria=cls.cat
        )
        cls.leite = Prato.objects.create(
            nome='Leite vegetal', preco=Decimal('3.00'), categoria=cls.adic
        )
        cls.mesa = Mesa.objects.create(identificacao='01', capacidade=4)

    def setUp(self):
        self.comanda = Comanda.objects.create(
            tipo=Comanda.Tipo.MESA, mesa=self.mesa, responsavel='Ana'
        )
        self.url = reverse('atendimento:lancar_item', args=[self.comanda.pk])

    def _tem_painel(self, resposta):
        return b'name="acao" value="personalizar"' in resposta.content

    def test_adicional_entra_no_total_com_snapshot(self):
        self.client.post(self.url, {'acao': 'adicionar', 'prato': self.espresso.pk})
        item = self.comanda.itens.get()
        self.client.post(self.url, {
            'acao': 'personalizar', 'item': item.pk, 'quantidade': 2,
            'observacao': 'sem açúcar', 'adicionais_escolhidos': [self.leite.pk],
        })
        item.refresh_from_db()
        self.assertEqual(item.observacao, 'sem açúcar')
        self.assertEqual(item.total, Decimal('18.00'))

        self.leite.preco = Decimal('99.00')
        self.leite.save()
        item.refresh_from_db()
        self.assertEqual(item.total, Decimal('18.00'))

    def test_item_personalizado_nao_agrupa(self):
        self.client.post(self.url, {'acao': 'adicionar', 'prato': self.espresso.pk})
        item = self.comanda.itens.get()
        self.client.post(self.url, {
            'acao': 'personalizar', 'item': item.pk, 'quantidade': 1,
            'observacao': '', 'adicionais_escolhidos': [self.leite.pk],
        })
        self.client.post(self.url, {'acao': 'adicionar', 'prato': self.espresso.pk})
        self.assertEqual(self.comanda.itens.count(), 2)

    def test_remover_adicional_preserva_o_que_fica(self):
        chantilly = Prato.objects.create(
            nome='Chantilly', preco=Decimal('3.50'), categoria=self.adic
        )
        self.client.post(self.url, {'acao': 'adicionar', 'prato': self.espresso.pk})
        item = self.comanda.itens.get()
        for escolhidos in ([self.leite.pk, chantilly.pk], [self.leite.pk]):
            self.client.post(self.url, {
                'acao': 'personalizar', 'item': item.pk, 'quantidade': 1,
                'observacao': '', 'adicionais_escolhidos': escolhidos,
            })
        item.refresh_from_db()
        self.assertEqual(
            list(item.adicionais.values_list('prato__nome', flat=True)), ['Leite vegetal']
        )

    def test_item_na_cozinha_nao_e_personalizavel(self):
        self.client.post(self.url, {'acao': 'adicionar', 'prato': self.espresso.pk})
        item = self.comanda.itens.get()
        ItemComanda.objects.filter(pk=item.pk).update(status=ItemComanda.Status.PRONTO)
        self.client.post(self.url, {
            'acao': 'personalizar', 'item': item.pk, 'quantidade': 9, 'observacao': 'x',
        })
        item.refresh_from_db()
        self.assertEqual(item.quantidade, 1)
        self.assertEqual(item.observacao, '')
        self.assertFalse(self._tem_painel(self.client.get(f'{self.url}?personalizar={item.pk}')))

    def test_painel_so_abre_para_item_da_propria_comanda(self):
        self.client.post(self.url, {'acao': 'adicionar', 'prato': self.espresso.pk})
        proprio = self.comanda.itens.get()
        outra = Comanda.objects.create(tipo=Comanda.Tipo.VIAGEM, responsavel='Bruno')
        alheio = ItemComanda.objects.create(comanda=outra, prato=self.espresso)

        self.assertTrue(self._tem_painel(self.client.get(f'{self.url}?personalizar={proprio.pk}')))
        for sufixo in [alheio.pk, 99999, 'abc', '']:
            with self.subTest(sufixo=sufixo):
                resposta = self.client.get(f'{self.url}?personalizar={sufixo}')
                self.assertEqual(resposta.status_code, 200)
                self.assertFalse(self._tem_painel(resposta))


class BlindagemTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cat = Categoria.objects.create(nome='Cafés', ordem=1)
        adic = Categoria.objects.create(nome='Adicionais', ordem=9, eh_adicional=True)
        cls.espresso = Prato.objects.create(nome='Espresso', preco=Decimal('6.00'), categoria=cat)
        cls.leite = Prato.objects.create(nome='Leite vegetal', preco=Decimal('3.00'), categoria=adic)
        cls.mesa = Mesa.objects.create(identificacao='01', capacidade=4)

    def setUp(self):
        self.comanda = Comanda.objects.create(
            tipo=Comanda.Tipo.MESA, mesa=self.mesa, responsavel='Ana'
        )
        self.pdv = reverse('atendimento:lancar_item', args=[self.comanda.pk])

    def test_ids_forjados_dao_404(self):
        casos = [
            (self.pdv, {'acao': 'adicionar', 'prato': 'abc'}),
            (self.pdv, {'acao': 'incrementar', 'item': 'abc'}),
            (self.pdv, {'acao': 'personalizar', 'item': 'abc'}),
            (reverse('atendimento:cozinha'), {'item': 'abc', 'status': 'PRONTO'}),
        ]
        for url, dados in casos:
            with self.subTest(dados=dados):
                self.assertEqual(self.client.post(url, dados).status_code, 404)

    def test_adicional_nao_e_lancado_como_item(self):
        resposta = self.client.post(self.pdv, {'acao': 'adicionar', 'prato': self.leite.pk})
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(self.comanda.itens.count(), 0)

    def test_produto_esgotado_mostra_mensagem(self):
        self.espresso.disponivel = False
        self.espresso.save()
        resposta = self.client.post(
            self.pdv, {'acao': 'adicionar', 'prato': self.espresso.pk}, follow=True
        )
        self.assertContains(resposta, 'acabou de ficar indisponível')
        self.assertEqual(self.comanda.itens.count(), 0)

    def test_cancelar_comanda_fechada_redireciona(self):
        ItemComanda.objects.create(comanda=self.comanda, prato=self.espresso)
        self.comanda.fechar(Comanda.FormaPagamento.PIX)
        url = reverse('atendimento:cancelar_comanda', args=[self.comanda.pk])
        self.assertRedirects(
            self.client.get(url),
            reverse('atendimento:detalhe_comanda', args=[self.comanda.pk]),
        )

    def _request_admin(self):
        request = RequestFactory().get('/admin/')
        request.user = User.objects.create_superuser('admin', 'a@a.com', 'senha')
        return request

    def test_admin_status_nunca_e_editavel(self):
        request = self._request_admin()
        campos = ComandaAdmin(Comanda, admin.site).get_readonly_fields(request, self.comanda)
        self.assertIn('status', campos)
        self.assertNotIn('responsavel', campos)

    def test_admin_trava_comanda_fechada(self):
        ItemComanda.objects.create(comanda=self.comanda, prato=self.espresso)
        self.comanda.fechar(Comanda.FormaPagamento.PIX)
        request = self._request_admin()

        comanda_admin = ComandaAdmin(Comanda, admin.site)
        self.assertIn('responsavel', comanda_admin.get_readonly_fields(request, self.comanda))
        self.assertFalse(comanda_admin.has_delete_permission(request, self.comanda))

        item = self.comanda.itens.get()
        item_admin = ItemComandaAdmin(ItemComanda, admin.site)
        self.assertFalse(item_admin.has_change_permission(request, item))
        self.assertFalse(item_admin.has_delete_permission(request, item))