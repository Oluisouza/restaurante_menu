from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

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
        self.prato.preco = Decimal('99.00')
        self.prato.save()
        comanda.refresh_from_db()
        self.assertEqual(comanda.itens.first().preco_unitario, Decimal('6.00'))

    def test_nao_fecha_sem_itens(self):
        comanda = Comanda.objects.create(tipo=Comanda.Tipo.VIAGEM, responsavel='X')
        with self.assertRaises(Exception):
            comanda.fechar(Comanda.FormaPagamento.PIX)

    def test_desconto_maior_que_conta(self):
        comanda = self._comanda_com_item('6.00')
        comanda.desconto = Decimal('999.00')
        with self.assertRaises(Exception):
            comanda.fechar(Comanda.FormaPagamento.PIX)

    def test_taxa_arredonda_para_cima(self):
        casos = [('12.25', '1.23'), ('0.05', '0.01'), ('100.45', '10.05')]
        for subtotal, esperado in casos:
            with self.subTest(subtotal=subtotal):
                comanda = self._comanda_com_item(subtotal)
                comanda.taxa_servico = True
                self.assertEqual(comanda.valor_taxa_servico, Decimal(esperado))

    def test_total_pago_congela(self):
        comanda = self._comanda_com_item('10.00')
        comanda.fechar(Comanda.FormaPagamento.PIX)
        self.assertEqual(comanda.total_pago, Decimal('10.00'))
        self.assertEqual(comanda.status, Comanda.Status.FECHADA)

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