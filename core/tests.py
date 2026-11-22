from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .para_testes import TesteComRestaurante


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
            reverse('login'), {'username': 'atendente', 'password': 'senha-teste'}
        )
        self.assertRedirects(resposta, reverse('atendimento:salao'))
        self.assertContains(self.client.get(reverse('atendimento:salao')), 'atendente')

        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertEqual(self.client.get(reverse('atendimento:salao')).status_code, 302)


class SemPerfilTest(TestCase):

    def test_usuario_sem_perfil_recebe_403(self):
        self.client.force_login(User.objects.create_user('sem_perfil', password='x'))
        self.assertEqual(self.client.get(reverse('cardapio:lista_pratos')).status_code, 403)