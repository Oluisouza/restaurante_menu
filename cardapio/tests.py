from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .forms import PratoForm
from .models import Categoria, Prato
from .models import Categoria, Combo, ComboItem, Prato


class BuscaFiltroPratosTest(TestCase):
    def setUp(self):
        self.bebidas = Categoria.objects.create(nome='Bebidas', ordem=1)
        self.doces = Categoria.objects.create(nome='Doces', ordem=2)
        Prato.objects.create(nome='Café expresso', preco=Decimal('6.00'), categoria=self.bebidas)
        Prato.objects.create(nome='Bolo de café', preco=Decimal('9.00'), categoria=self.doces)
        Prato.objects.create(nome='Suco de laranja', descricao='Natural, feito na hora',
                             preco=Decimal('8.00'), categoria=self.bebidas)
        self.url = reverse('cardapio:lista_pratos')

    def nomes(self, **params):
        resposta = self.client.get(self.url, params)
        self.assertEqual(resposta.status_code, 200)
        return {p.nome for p in resposta.context['pratos']}

    def test_busca_ignora_maiusculas(self):
        self.assertEqual(self.nomes(q='CAF'), {'Café expresso', 'Bolo de café'})

    def test_busca_tambem_olha_a_descricao(self):
        self.assertEqual(self.nomes(q='natural'), {'Suco de laranja'})

    def test_filtro_por_categoria(self):
        self.assertEqual(self.nomes(categoria=self.doces.pk), {'Bolo de café'})

    def test_busca_e_categoria_juntas(self):
        self.assertEqual(self.nomes(q='café', categoria=self.bebidas.pk), {'Café expresso'})

    def test_categoria_invalida_nao_derruba_a_pagina(self):
        self.assertEqual(len(self.nomes(categoria='abc')), 3)

    def test_sem_resultado_mostra_mensagem(self):
        resposta = self.client.get(self.url, {'q': 'pizza'})
        self.assertContains(resposta, 'Nenhum item encontrado com esses filtros')
        self.assertContains(resposta, 'value="pizza"')

class VitrineFiltroTest(TestCase):
    def setUp(self):
        self.bebidas = Categoria.objects.create(nome='Bebidas', ordem=1)
        self.doces = Categoria.objects.create(nome='Doces', ordem=2)
        Prato.objects.create(nome='Café expresso', preco=Decimal('6.00'), categoria=self.bebidas)
        Prato.objects.create(nome='Bolo de café', preco=Decimal('9.00'), categoria=self.doces)
        self.url = reverse('cardapio:lista_cardapio')

    def test_filtro_por_categoria_na_vitrine(self):
        resposta = self.client.get(self.url, {'categoria': self.doces.pk})
        self.assertContains(resposta, 'Bolo de café')
        self.assertNotContains(resposta, 'Café expresso')

    def test_vitrine_sem_resultado_mostra_mensagem(self):
        resposta = self.client.get(self.url, {'q': 'pizza'})
        self.assertContains(resposta, 'Nenhum item encontrado com esses filtros')

class ComboFiltroTest(TestCase):
    def setUp(self):
        bebidas = Categoria.objects.create(nome='Bebidas', ordem=1)
        self.doces = Categoria.objects.create(nome='Doces', ordem=2)
        self.salgados = Categoria.objects.create(nome='Salgados', ordem=3)
        cafe = Prato.objects.create(nome='Café expresso', preco=Decimal('6.00'), categoria=bebidas)
        bolo = Prato.objects.create(nome='Bolo de cenoura', preco=Decimal('9.00'), categoria=self.doces)
        pao = Prato.objects.create(nome='Pão de queijo', preco=Decimal('5.00'), categoria=self.salgados)

        manha = Combo.objects.create(nome='Combo manhã', preco=Decimal('13.00'))
        ComboItem.objects.create(combo=manha, prato=cafe, quantidade=1)
        ComboItem.objects.create(combo=manha, prato=bolo, quantidade=1)

        lanche = Combo.objects.create(nome='Combo lanche', preco=Decimal('10.00'))
        ComboItem.objects.create(combo=lanche, prato=cafe, quantidade=1)
        ComboItem.objects.create(combo=lanche, prato=pao, quantidade=1)

        self.url = reverse('cardapio:lista_cardapio')

    def combos(self, **params):
        resposta = self.client.get(self.url, params)
        return [c.nome for c in resposta.context['combos']]

    def test_busca_encontra_combo_pelo_item(self):
        self.assertEqual(self.combos(q='bolo'), ['Combo manhã'])

    def test_combo_com_item_da_categoria(self):
        self.assertEqual(self.combos(categoria=self.salgados.pk), ['Combo lanche'])

    def test_combo_nao_se_repete(self):
        self.assertEqual(sorted(self.combos(q='combo')), ['Combo lanche', 'Combo manhã'])

class ValidacaoPrecoTest(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Bebidas')

    def dados(self, preco):
        return {'nome': 'Café', 'preco': preco, 'categoria': self.categoria.pk, 'disponivel': True}

    def test_preco_zero_e_recusado(self):
        form = PratoForm(self.dados('0'))
        self.assertFalse(form.is_valid())
        self.assertIn('maior que zero', form.errors['preco'][0])

    def test_preco_positivo_e_aceito(self):
        self.assertTrue(PratoForm(self.dados('0.01')).is_valid())

    def test_post_com_preco_zero_nao_grava(self):
        resposta = self.client.post(reverse('cardapio:novo_prato'), self.dados('0'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'maior que zero')
        self.assertFalse(Prato.objects.exists())        