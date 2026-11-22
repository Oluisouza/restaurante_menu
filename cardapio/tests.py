from decimal import Decimal
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.urls import reverse

from core.models import Restaurante
from core.para_testes import TesteComRestaurante

from .forms import PratoForm
from .models import Categoria, Combo, ComboItem, Prato


class BuscaFiltroPratosTest(TesteComRestaurante):
    def setUp(self):
        super().setUp()
        self.bebidas = Categoria.objects.create(restaurante=self.restaurante, nome='Bebidas', ordem=1)
        self.doces = Categoria.objects.create(restaurante=self.restaurante, nome='Doces', ordem=2)
        Prato.objects.create(restaurante=self.restaurante, nome='Café expresso', preco=Decimal('6.00'), categoria=self.bebidas)
        Prato.objects.create(restaurante=self.restaurante, nome='Bolo de café', preco=Decimal('9.00'), categoria=self.doces)
        Prato.objects.create(restaurante=self.restaurante, nome='Suco de laranja', descricao='Natural, feito na hora',
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

class VitrineFiltroTest(TesteComRestaurante):
    def setUp(self):
        super().setUp()
        self.bebidas = Categoria.objects.create(restaurante=self.restaurante, nome='Bebidas', ordem=1)
        self.doces = Categoria.objects.create(restaurante=self.restaurante, nome='Doces', ordem=2)
        Prato.objects.create(restaurante=self.restaurante, nome='Café expresso', preco=Decimal('6.00'), categoria=self.bebidas)
        Prato.objects.create(restaurante=self.restaurante, nome='Bolo de café', preco=Decimal('9.00'), categoria=self.doces)
        self.url = reverse('cardapio:lista_cardapio')

    def test_filtro_por_categoria_na_vitrine(self):
        resposta = self.client.get(self.url, {'categoria': self.doces.pk})
        self.assertContains(resposta, 'Bolo de café')
        self.assertNotContains(resposta, 'Café expresso')

    def test_vitrine_sem_resultado_mostra_mensagem(self):
        resposta = self.client.get(self.url, {'q': 'pizza'})
        self.assertContains(resposta, 'Nenhum item encontrado com esses filtros')

class ComboFiltroTest(TesteComRestaurante):
    def setUp(self):
        super().setUp()
        bebidas = Categoria.objects.create(restaurante=self.restaurante, nome='Bebidas', ordem=1)
        self.doces = Categoria.objects.create(restaurante=self.restaurante, nome='Doces', ordem=2)
        self.salgados = Categoria.objects.create(restaurante=self.restaurante, nome='Salgados', ordem=3)
        cafe = Prato.objects.create(restaurante=self.restaurante, nome='Café expresso', preco=Decimal('6.00'), categoria=bebidas)
        bolo = Prato.objects.create(restaurante=self.restaurante, nome='Bolo de cenoura', preco=Decimal('9.00'), categoria=self.doces)
        pao = Prato.objects.create(restaurante=self.restaurante, nome='Pão de queijo', preco=Decimal('5.00'), categoria=self.salgados)

        manha = Combo.objects.create(restaurante=self.restaurante, nome='Combo manhã', preco=Decimal('13.00'))
        ComboItem.objects.create(combo=manha, prato=cafe, quantidade=1)
        ComboItem.objects.create(combo=manha, prato=bolo, quantidade=1)

        lanche = Combo.objects.create(restaurante=self.restaurante, nome='Combo lanche', preco=Decimal('10.00'))
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

class ValidacaoPrecoTest(TesteComRestaurante):
    def setUp(self):
        super().setUp()
        self.categoria = Categoria.objects.create(restaurante=self.restaurante, nome='Bebidas')

    def dados(self, preco):
        return {'nome': 'Café', 'preco': preco, 'categoria': self.categoria.pk, 'disponivel': True}

    def test_preco_zero_e_recusado(self):
        form = PratoForm(self.dados('0'), restaurante=self.restaurante)
        self.assertFalse(form.is_valid())
        self.assertIn('maior que zero', form.non_field_errors()[0])

    def test_preco_positivo_e_aceito(self):
        self.assertTrue(PratoForm(self.dados('0.01'), restaurante=self.restaurante).is_valid())

    def test_post_com_preco_zero_nao_grava(self):
        resposta = self.client.post(reverse('cardapio:novo_prato'), self.dados('0'))
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'maior que zero')
        self.assertFalse(Prato.objects.exists())

    def test_banco_recusa_preco_zero(self):
        tentativas = {
            'prato': lambda: Prato.objects.create(restaurante=self.restaurante, nome='Água', preco=Decimal('0'), categoria=self.categoria),
            'combo': lambda: Combo.objects.create(restaurante=self.restaurante, nome='Combo grátis', preco=Decimal('0')),
        }
        for nome, criar in tentativas.items():
            with self.subTest(nome):
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        criar()


class PratoApiTest(TesteComRestaurante):
    """A API herda as regras do model: mesma validação, resposta em JSON."""

    def setUp(self):
        super().setUp()
        self.categoria = Categoria.objects.create(restaurante=self.restaurante, nome='Bebidas')
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
        Prato.objects.create(restaurante=self.restaurante, nome='Chá', preco=Decimal('5.00'), categoria=self.categoria)
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
        prato = Prato.objects.create(restaurante=self.restaurante, nome='Chá', preco=Decimal('5.00'), categoria=self.categoria)
        url = reverse('cardapio_api:detalhe_prato', args=[prato.pk])
        ok = self.client.patch(url, {'preco': '5.50'}, content_type='application/json')
        self.assertEqual(ok.status_code, 200)
        recusado = self.client.patch(url, {'preco': '0'}, content_type='application/json')
        self.assertEqual(recusado.status_code, 400)
        prato.refresh_from_db()
        self.assertEqual(prato.preco, Decimal('5.50'))

    def test_excluir_prato_usado_em_combo_volta_400(self):
        prato = Prato.objects.create(restaurante=self.restaurante, nome='Chá', preco=Decimal('5.00'), categoria=self.categoria)
        combo = Combo.objects.create(restaurante=self.restaurante, nome='Combo tarde', preco=Decimal('9.00'))
        ComboItem.objects.create(combo=combo, prato=prato, quantidade=1)
        resposta = self.client.delete(reverse('cardapio_api:detalhe_prato', args=[prato.pk]))
        self.assertEqual(resposta.status_code, 400)
        self.assertTrue(Prato.objects.filter(pk=prato.pk).exists())

class IsolamentoCardapioTest(TesteComRestaurante):
    """O cardápio de um restaurante não aparece nem se altera pelo outro."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.categoria = Categoria.objects.create(restaurante=cls.restaurante, nome='Bebidas')
        Prato.objects.create(restaurante=cls.restaurante, nome='Meu prato', preco=Decimal('5.00'), categoria=cls.categoria)

        cls.outro = Restaurante.objects.create(nome='Restaurante Vizinho')
        cls.categoria_outra = Categoria.objects.create(restaurante=cls.outro, nome='Sobremesas do vizinho')
        cls.prato_outro = Prato.objects.create(
            restaurante=cls.outro, nome='Prato do vizinho', preco=Decimal('9.00'), categoria=cls.categoria_outra
        )
        Combo.objects.create(restaurante=cls.outro, nome='Combo do vizinho', preco=Decimal('12.00'))

    def test_listas_mostram_so_o_proprio_restaurante(self):
        gerenciar = self.client.get(reverse('cardapio:lista_pratos'))
        self.assertEqual([p.nome for p in gerenciar.context['pratos']], ['Meu prato'])
        self.assertNotContains(gerenciar, 'Sobremesas do vizinho')

        vitrine = self.client.get(reverse('cardapio:lista_cardapio'))
        self.assertContains(vitrine, 'Meu prato')
        self.assertNotContains(vitrine, 'Prato do vizinho')
        self.assertNotContains(vitrine, 'Combo do vizinho')

    def test_prato_de_outro_restaurante_da_404(self):
        editar = reverse('cardapio:editar_prato', args=[self.prato_outro.pk])
        excluir = reverse('cardapio:excluir_prato', args=[self.prato_outro.pk])
        tentativas = {
            'abrir edicao': lambda: self.client.get(editar),
            'salvar edicao': lambda: self.client.post(editar, {
                'nome': 'Invadido', 'preco': '1.00', 'categoria': self.categoria.pk,
            }),
            'abrir exclusao': lambda: self.client.get(excluir),
            'confirmar exclusao': lambda: self.client.post(excluir),
        }
        for nome, tentar in tentativas.items():
            with self.subTest(nome):
                self.assertEqual(tentar().status_code, 404)
        self.prato_outro.refresh_from_db()
        self.assertEqual(self.prato_outro.nome, 'Prato do vizinho')

    def test_prato_novo_nasce_no_restaurante_do_usuario(self):
        self.client.post(reverse('cardapio:novo_prato'), {
            'nome': 'Suco', 'preco': '7.00', 'categoria': self.categoria.pk, 'disponivel': True,
        })
        self.assertEqual(Prato.objects.get(nome='Suco').restaurante, self.restaurante)

    def test_categoria_de_outro_restaurante_e_recusada(self):
        resposta = self.client.post(reverse('cardapio:novo_prato'), {
            'nome': 'Intruso', 'preco': '7.00', 'categoria': self.categoria_outra.pk,
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertIn('categoria', resposta.context['form'].errors)
        self.assertFalse(Prato.objects.filter(nome='Intruso').exists())

class IsolamentoApiTest(TesteComRestaurante):
    """A API segue o mesmo isolamento das telas."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.categoria = Categoria.objects.create(restaurante=cls.restaurante, nome='Bebidas')
        Prato.objects.create(restaurante=cls.restaurante, nome='Meu prato', preco=Decimal('5.00'), categoria=cls.categoria)

        cls.outro = Restaurante.objects.create(nome='Restaurante Vizinho')
        cls.categoria_outra = Categoria.objects.create(restaurante=cls.outro, nome='Bebidas do vizinho')
        cls.prato_outro = Prato.objects.create(
            restaurante=cls.outro, nome='Prato do vizinho', preco=Decimal('9.00'), categoria=cls.categoria_outra
        )

    def setUp(self):
        super().setUp()
        self.lista = reverse('cardapio_api:lista_pratos')

    def test_lista_so_o_proprio_restaurante(self):
        nomes = [p['nome'] for p in self.client.get(self.lista).json()]
        self.assertEqual(nomes, ['Meu prato'])

    def test_prato_de_outro_restaurante_da_404(self):
        url = reverse('cardapio_api:detalhe_prato', args=[self.prato_outro.pk])
        tentativas = {
            'ler': lambda: self.client.get(url),
            'alterar': lambda: self.client.patch(url, {'nome': 'Invadido'}, content_type='application/json'),
            'apagar': lambda: self.client.delete(url),
        }
        for nome, tentar in tentativas.items():
            with self.subTest(nome):
                self.assertEqual(tentar().status_code, 404)
        self.prato_outro.refresh_from_db()
        self.assertEqual(self.prato_outro.nome, 'Prato do vizinho')

    def test_criacao_nasce_no_restaurante_e_recusa_categoria_alheia(self):
        recusado = self.client.post(self.lista, {
            'nome': 'Intruso', 'preco': '5.00', 'categoria': self.categoria_outra.pk,
        }, content_type='application/json')
        self.assertEqual(recusado.status_code, 400)
        self.assertIn('categoria', recusado.json())

        criado = self.client.post(self.lista, {
            'nome': 'Suco', 'preco': '7.00', 'categoria': self.categoria.pk,
        }, content_type='application/json')
        self.assertEqual(criado.status_code, 201)
        self.assertEqual(Prato.objects.get(pk=criado.json()['id']).restaurante, self.restaurante)

    def test_usuario_sem_perfil_recebe_403(self):
        self.client.force_login(User.objects.create_user('sem_perfil', password='x'))
        self.assertEqual(self.client.get(self.lista).status_code, 403)