from decimal import Decimal
from django.db import IntegrityError, transaction
from django.contrib.auth.models import User
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
        self.assertIn('maior que zero', form.non_field_errors()[0])

    def test_preco_positivo_e_aceito(self):
        self.assertTrue(PratoForm(self.dados('0.01')).is_valid())

    def test_post_com_preco_zero_nao_grava(self):
        resposta = self.client.post(reverse('cardapio:novo_prato'), self.dados('0'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'maior que zero')
        self.assertFalse(Prato.objects.exists())        

    def test_banco_recusa_preco_zero(self):
        tentativas = {
            'prato': lambda: Prato.objects.create(nome='Água', preco=Decimal('0'), categoria=self.categoria),
            'combo': lambda: Combo.objects.create(nome='Combo grátis', preco=Decimal('0')),
        }
        for nome, criar in tentativas.items():
            with self.subTest(nome):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        criar()

class PratoApiTest(TestCase):
    """A API herda as regras do model: mesma validação, resposta em JSON."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nome='Bebidas')
        self.usuario = User.objects.create_user('ana', password='senha-teste')
        self.client.force_login(self.usuario)
        self.lista = reverse('cardapio_api:lista_pratos')

    def criar(self, **dados):
        base = {'nome': 'Café', 'preco': '6.00', 'categoria': self.categoria.pk}
        return self.client.post(self.lista, {**base, **dados}, content_type='application/json')

    def test_sem_login_e_recusado(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.lista).status_code, 403)
        self.assertEqual(self.criar().status_code, 403)

    def test_cria_e_lista_em_json(self):
        resposta = self.criar()
        self.assertEqual(resposta.status_code, 201)
        self.assertEqual(resposta.json()['nome'], 'Café')
        nomes = [p['nome'] for p in self.client.get(self.lista).json()]
        self.assertEqual(nomes, ['Café'])

    def test_regras_do_model_viram_400(self):
        Prato.objects.create(nome='Chá', preco=Decimal('5.00'), categoria=self.categoria)
        casos = {
            'preco zero': ({'preco': '0'}, 'maior que zero'),
            'nome repetido ignorando maiusculas': ({'nome': 'CHÁ'}, 'Já existe'),
        }
        for nome, (dados, mensagem) in casos.items():
            with self.subTest(nome):
                resposta = self.criar(**dados)
                self.assertEqual(resposta.status_code, 400)
                self.assertIn(mensagem, str(resposta.json()))
        self.assertEqual(Prato.objects.count(), 1)

    def test_patch_tambem_passa_pelas_regras(self):
        prato = Prato.objects.create(nome='Chá', preco=Decimal('5.00'), categoria=self.categoria)
        url = reverse('cardapio_api:detalhe_prato', args=[prato.pk])
        ok = self.client.patch(url, {'preco': '5.50'}, content_type='application/json')
        self.assertEqual(ok.status_code, 200)
        recusado = self.client.patch(url, {'preco': '0'}, content_type='application/json')
        self.assertEqual(recusado.status_code, 400)
        prato.refresh_from_db()
        self.assertEqual(prato.preco, Decimal('5.50'))

    def test_excluir_prato_usado_em_combo_volta_400(self):
        prato = Prato.objects.create(nome='Chá', preco=Decimal('5.00'), categoria=self.categoria)
        combo = Combo.objects.create(nome='Combo tarde', preco=Decimal('9.00'))
        ComboItem.objects.create(combo=combo, prato=prato, quantidade=1)
        resposta = self.client.delete(reverse('cardapio_api:detalhe_prato', args=[prato.pk]))
        self.assertEqual(resposta.status_code, 400)
        self.assertTrue(Prato.objects.filter(pk=prato.pk).exists())