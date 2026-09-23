from decimal import Decimal

from django.test import TestCase
from django.urls import reverse

from .forms import PratoForm
from .models import Categoria, Prato


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