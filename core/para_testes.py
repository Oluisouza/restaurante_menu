from django.contrib.auth.models import User
from django.test import TestCase

from .models import Perfil, Restaurante


def criar_usuario(username, restaurante, papel=Perfil.Papel.GERENTE):
    usuario = User.objects.create_user(username, password='senha-teste')
    Perfil.objects.create(usuario=usuario, restaurante=restaurante, papel=papel)
    return usuario


class TesteComRestaurante(TestCase):
    """Base dos testes: um restaurante e um gerente logado nele."""

    @classmethod
    def setUpTestData(cls):
        cls.restaurante = Restaurante.objects.create(nome='Restaurante Teste')
        cls.usuario = criar_usuario('gerente', cls.restaurante)

    def setUp(self):
        self.client.force_login(self.usuario)