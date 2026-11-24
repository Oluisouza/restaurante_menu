from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import Perfil
from .para_testes import TesteComRestaurante, criar_usuario

class LoginTest(TestCase):
    """Nenhuma tela abre sem login: quem não entrou vai para a tela de login."""

    def test_telas_redirecionam_para_o_login(self):
        login = reverse('login')
        for nome in [
            'atendimento:salao',
            'atendimento:lista_comandas',
            'atendimento:cozinha',
            'atendimento:resumo',
            'cardapio:lista_cardapio',
            'cardapio:lista_pratos',
        ]:
            with self.subTest(rota=nome):
                url = reverse(nome)
                self.assertRedirects(self.client.get(url), f'{login}?next={url}')

    def test_tela_de_login_abre_sem_login(self):
        self.assertEqual(self.client.get(reverse('login')).status_code, 200)


class EntrarESairTest(TesteComRestaurante):

    def setUp(self):
        pass  # sem force_login: aqui o login é feito pela tela

    def test_login_leva_ao_salao_e_logout_volta_ao_login(self):
        resposta = self.client.post(
            reverse('login'), {'username': 'gerente', 'password': 'senha-teste'}
        )
        self.assertRedirects(resposta, reverse('atendimento:salao'))
        self.assertContains(self.client.get(reverse('atendimento:salao')), 'gerente')

        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertEqual(self.client.get(reverse('atendimento:salao')).status_code, 302)


class SemPerfilTest(TestCase):

    def test_usuario_sem_perfil_recebe_403(self):
        self.client.force_login(User.objects.create_user('sem_perfil', password='x'))
        self.assertEqual(self.client.get(reverse('cardapio:lista_pratos')).status_code, 403)



class PapelTest(TesteComRestaurante):
    """O gerente faz tudo; o atendente opera o salão, mas não mexe na gestão."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.atendente = criar_usuario('atendente', cls.restaurante, papel=Perfil.Papel.ATENDENTE)

    def test_atendente_recebe_403_nas_telas_de_gestao(self):
        self.client.force_login(self.atendente)
        for url in [
            reverse('cardapio:lista_pratos'),
            reverse('cardapio:novo_prato'),
            reverse('atendimento:exportar_csv'),
        ]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_atendente_continua_operando_o_salao(self):
        self.client.force_login(self.atendente)
        for nome in ['atendimento:salao', 'atendimento:lista_comandas', 'atendimento:cozinha', 'cardapio:lista_cardapio']:
            with self.subTest(rota=nome):
                self.assertEqual(self.client.get(reverse(nome)).status_code, 200)

    def test_gerente_abre_as_telas_de_gestao(self):
        for url in [reverse('cardapio:lista_pratos'), reverse('atendimento:exportar_csv')]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_dashboard_do_atendente_sem_serie_e_sem_exportar(self):
        self.client.force_login(self.atendente)
        resposta = self.client.get(reverse('atendimento:dashboard'))
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('serie', resposta.context)
        self.assertNotContains(resposta, 'id="dados-serie"')
        self.assertNotContains(resposta, 'Exportar CSV')

    def test_menu_esconde_a_gestao_do_atendente(self):
        self.client.force_login(self.atendente)
        self.assertNotContains(self.client.get(reverse('atendimento:salao')), 'Gerenciar cardápio')
        self.client.force_login(self.usuario)
        self.assertContains(self.client.get(reverse('atendimento:salao')), 'Gerenciar cardápio')