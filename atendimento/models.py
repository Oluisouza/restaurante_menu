from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.core.validators import MinValueValidator

from cardapio.models import Prato, Combo

class Mesa(models.Model):
    identificacao = models.CharField(max_length=20, unique=True)
    capacidade = models.PositiveIntegerField(default=4)
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "mesa"
        verbose_name_plural = "mesas"
        ordering = ['identificacao']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(capacidade__gte=1),
                name='mesa_capacidade_minima',
                violation_error_message='A mesa precisa ter ao menos um lugar.',
            ),
        ]

    def __str__(self):
        return f'Mesa {self.identificacao}'

    @property
    def comandas_abertas(self):
        return self.comandas.filter(status=Comanda.Status.ABERTA)

    @property
    def ocupada(self):
        return self.comandas_abertas.exists()


class Comanda(models.Model):

    class Tipo(models.TextChoices):
        MESA = 'MESA', 'Mesa'
        VIAGEM = 'VIAGEM', 'Viagem'
        BALCAO = 'BALCAO', 'Balcão'

    class Status(models.TextChoices):
        ABERTA = 'ABERTA', 'Aberta'
        FECHADA = 'FECHADA', 'Fechada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    class FormaPagamento(models.TextChoices):
        DINHEIRO = 'DINHEIRO', 'Dinheiro'
        PIX = 'PIX', 'Pix'
        DEBITO = 'DEBITO', 'Débito'
        CREDITO = 'CREDITO', 'Crédito'
  
    codigo = models.CharField(max_length=20, unique=True, blank=True)
    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        default=Tipo.MESA,
    )
    mesa = models.ForeignKey(
        Mesa,
        on_delete=models.PROTECT,
        related_name='comandas',
        blank=True,
        null=True,
    )
    responsavel = models.CharField(max_length=100, blank=True)

    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ABERTA)
    aberta_em = models.DateTimeField(auto_now_add=True)
    fechada_em = models.DateTimeField(blank=True, null=True)

    taxa_servico = models.BooleanField(default=False)
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    forma_pagamento = models.CharField(max_length=10, choices=FormaPagamento.choices, blank=True)
    total_pago = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = "comanda"
        verbose_name_plural = "comandas"
        ordering = ['-aberta_em']
        constraints = [
            models.CheckConstraint(
                condition=models.Q(desconto__gte=0),
                name='comanda_desconto_nao_negativo',
                violation_error_message='O desconto não pode ser negativo.',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(tipo='MESA', mesa__isnull=False)
                    | (~models.Q(tipo='MESA') & models.Q(mesa__isnull=True))
                ),
                name='comanda_mesa_conforme_tipo',
                violation_error_message=('Comanda de mesa exige uma mesa; viagem e balcão não podem ter mesa'),
            ),
        ]

    def __str__(self):
        if self.mesa:
            return f'{self.codigo} - {self.mesa} - {self.responsavel or "sem nome"}'
        return f'{self.codigo} - {self.get_tipo_display()} - {self.responsavel or "sem nome"}'

    def clean(self):
        if self.tipo == self.Tipo.MESA and not self.mesa:
            raise ValidationError({'mesa': 'Comanda de mesa precisa ter uma mesa associada.'})
        if self.tipo != self.Tipo.MESA and self.mesa:
            raise ValidationError({'mesa': 'Comanda de viagem ou balcão não pode ter uma mesa associada.'})
        if self.desconto < 0:
            raise ValidationError({'desconto': 'Desconto não pode ser negativo.'})

    def save(self, *args, **kwargs):
        criando = self.pk is None
        super().save(*args, **kwargs)
        if criando and not self.codigo:
            self.codigo = f'CMD{self.pk:05d}'
            super().save(update_fields=['codigo'])

    @property
    def itens_validos(self):
        return self.itens.exclude(status=ItemComanda.Status.CANCELADO)

    @property
    def subtotal(self):
        return sum((item.total for item in self.itens_validos), Decimal('0.00'))

    @property
    def valor_taxa_servico(self):
        if not self.taxa_servico:
            return Decimal('0.00')
        return (self.subtotal * Decimal('0.10')).quantize(
            Decimal('0.01'), rounding=ROUND_HALF_UP
        )

    @property
    def total(self):
        return self.subtotal + self.valor_taxa_servico - self.desconto

    @property
    def esta_aberta(self):
        return self.status == self.Status.ABERTA

    def fechar(self, forma_pagamento=None):
        if not self.esta_aberta:
            raise ValidationError('Comanda já está fechada ou cancelada.')
        
        if not self.itens_validos.exists():
            raise ValidationError('Comanda não pode ser fechada sem itens válidos.')

        if forma_pagamento:
            self.forma_pagamento = forma_pagamento

        if not self.forma_pagamento:
            raise ValidationError('Informe a forma de pagamento.')

        if self.desconto > self.subtotal + self.valor_taxa_servico:
            raise ValidationError('O desconto não pode ser maior que o valor da conta')

        self.total_pago = self.total
        self.fechada_em = timezone.now()
        self.status = self.Status.FECHADA
        self.save()

    def cancelar(self):
        if not self.esta_aberta:
            raise ValidationError('Comanda já está fechada ou cancelada.')
        self.status = self.Status.CANCELADA
        self.fechada_em = timezone.now()
        self.save()

class ItemComanda(models.Model):

    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        EM_PREPARO = 'EM_PREPARO', 'Em preparo'
        PRONTO = 'PRONTO', 'Pronto'
        ENTREGUE = 'ENTREGUE', 'Entregue'
        CANCELADO = 'CANCELADO', 'Cancelado'

    comanda = models.ForeignKey(
        Comanda,
        on_delete=models.CASCADE,
        related_name='itens',
    )
    prato = models.ForeignKey(
        Prato,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    combo = models.ForeignKey(
        Combo,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    quantidade = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1, 'A quantidade mínima é 1.')])
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    observacao = models.CharField(max_length=200, blank=True)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDENTE)
    criado_em = models.DateTimeField(auto_now_add=True)
    motivo_cancelamento = models.CharField(max_length=200, blank=True)
    cancelado_em = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "item da comanda"
        verbose_name_plural = "itens da comanda"
        ordering = ['criado_em']
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(prato__isnull=False, combo__isnull=True) |
                    models.Q(prato__isnull=True, combo__isnull=False)
                ),
                name='item_prato_ou_combo',
            ),
            models.CheckConstraint(
                condition=models.Q(quantidade__gte=1),
                name='item_quantidade_minima',
            ),
            models.CheckConstraint(
                condition=models.Q(preco_unitario__isnull=True) |
                models.Q(preco_unitario__gte=0),
                name='item_preco_nao_negativo',
            ),
            models.CheckConstraint(
                condition=~models.Q(status='CANCELADO') | ~models.Q(motivo_cancelamento=''),
                name='item_cancelado_tem_motivo',
                violation_error_message='Item cancelado precisa de um motivo.',
            ),
        ]

    def __str__(self):
        return f'{self.quantidade}x {self.descricao_produto}'

    @property
    def produto(self):
        return self.prato or self.combo

    @property
    def descricao_produto(self):
        return self.produto.nome if self.produto else '(vazio)'

    @property
    def total_adicionais(self):
        return sum((ad.preco_unitario for ad in self.adicionais.all()), Decimal('0.00'))

    @property
    def total(self):
        return (self.preco_unitario + self.total_adicionais) * self.quantidade

    def clean(self):
        if bool(self.prato) == bool(self.combo):
            raise ValidationError('Informe exatamente um: prato ou combo.')

    @property
    def esta_pendente(self):
        return self.status == self.Status.PENDENTE

    def cancelar(self, motivo):
        motivo = (motivo or '').strip()
        if not self.comanda.esta_aberta:
            raise ValidationError('A comanda deste item já foi encerrada.')
        if self.status == self.Status.CANCELADO:
            raise ValidationError('Este item já foi cancelado.')
        if not motivo:
            raise ValidationError('Informe o motivo do cancelamento.')
        self.status = self.Status.CANCELADO
        self.motivo_cancelamento = motivo
        self.cancelado_em = timezone.now()
        self.save(update_fields=['status', 'motivo_cancelamento', 'cancelado_em'])

    @classmethod
    def from_db(cls, db, field_names, values):
        instance = super().from_db(db, field_names, values)
        if 'prato_id' in field_names and 'combo_id' in field_names:
            instance._produto_carregado = (instance.prato_id, instance.combo_id)
        return instance

    def refresh_from_db(self, using=None, fields=None, from_queryset=None):
        super().refresh_from_db(using, fields, from_queryset)
        self._produto_carregado = (self.prato_id, self.combo_id)

    def save(self, *args, **kwargs):
        carregado = getattr(self, '_produto_carregado', None)
        produto_mudou = (
            carregado is not None and (self.prato_id, self.combo_id) != carregado
        )
        if self.produto and (self.preco_unitario is None or produto_mudou):
            self.preco_unitario = self.produto.preco
        super().save(*args, **kwargs)
        self._produto_carregado = (self.prato_id, self.combo_id)

class ItemAdicional(models.Model):
    item_comanda = models.ForeignKey(
        ItemComanda,
        on_delete=models.CASCADE,
        related_name='adicionais',
    )
    prato = models.ForeignKey(
        Prato,
        on_delete=models.PROTECT,
    )
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

    class Meta:
        verbose_name = 'adicional'
        verbose_name_plural = 'adicionais'

    def __str__(self):
        return self.prato.nome

    def save(self, *args, **kwargs):
        if self.preco_unitario is None:
            self.preco_unitario = self.prato.preco
        super().save(*args, **kwargs)