from django.db import models
from django.db.models.functions import Lower

class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    ordem = models.PositiveIntegerField(default=0)
    eh_adicional = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        ordering = ['ordem', 'nome']
        constraints = [
            models.UniqueConstraint(
                Lower('nome'),
                name='categoria_nome_unico_ci',
                violation_error_message='Já existe uma categoria com esse nome.',
            )
        ]

    def save(self, *args, **kwargs):
        self.nome = self.nome.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome

class Prato(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.PROTECT,
        related_name='pratos',
    )
    imagem = models.ImageField(upload_to='pratos/', blank=True, null=True)
    disponivel = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "item do cardápio"
        verbose_name_plural = "itens do cardápio"
        ordering = ['categoria__ordem', 'nome']
        constraints = [
            models.UniqueConstraint(
                Lower('nome'),
                name='prato_nome_unico_ci',
                violation_error_message='Já existe um item do cardápio com esse nome.',
            ),
        ]

    def save(self, *args, **kwargs):
        self.nome = self.nome.strip()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.nome} - R$ {self.preco}'

class Combo(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    disponivel = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "combo"
        verbose_name_plural = "combos"
        ordering = ['nome']

    def __str__(self):
        return self.nome

    @property
    def preco_avulso(self):
        return sum(item.prato.preco * item.quantidade for item in self.itens.all())

    @property
    def economia(self):
        return self.preco_avulso - self.preco

class ComboItem(models.Model):
    combo = models.ForeignKey(
        Combo, 
        on_delete=models.CASCADE,
        related_name='itens',
    )
    prato = models.ForeignKey(
        Prato, 
        on_delete=models.PROTECT,
        related_name='combos',
    )
    quantidade = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "item do combo"
        verbose_name_plural = "itens do combo"
        constraints = [
            models.UniqueConstraint(fields=['combo', 'prato'], name='combo_prato_unico'),
        ]

    def __str__(self):
        return f'{self.quantidade}x {self.prato.nome}'