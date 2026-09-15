from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from cardapio.models import Categoria, Prato

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