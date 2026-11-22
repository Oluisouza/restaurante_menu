from django.contrib.auth.models import User
from django.db import models


class Restaurante(models.Model):
    nome = models.CharField(max_length=120)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']

    def __str__(self):
        return self.nome


class DoRestaurante(models.Model):
    """Base abstrata: todo dado de negócio pertence a um restaurante."""

    restaurante = models.ForeignKey(Restaurante, on_delete=models.PROTECT)

    class Meta:
        abstract = True


class Perfil(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    restaurante = models.ForeignKey(Restaurante, on_delete=models.PROTECT, related_name='perfis')

    class Meta:
        verbose_name_plural = 'perfis'

    def __str__(self):
        return f'{self.usuario.username} ({self.restaurante})'