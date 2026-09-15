from decimal import Decimal

from django.core.management.base import BaseCommand

from atendimento.models import Mesa
from cardapio.models import Categoria, Combo, ComboItem, Prato

CATEGORIAS = [
    ('Cafés', 1, False),
    ('Bebidas geladas', 2, False),
    ('Salgados', 3, False),
    ('Doces', 4, False),
    ('Adicionais', 5, True),
]

PRATOS = [
    ('Espresso', 'Cafés', '6.00'),
    ('Espresso duplo', 'Cafés', '9.00'),
    ('Coado 200ml', 'Cafés', '7.00'),
    ('Cappuccino', 'Cafés', '12.00'),
    ('Latte', 'Cafés', '11.00'),
    ('Mocha', 'Cafés', '13.50'),
    ('Suco de laranja 300ml', 'Bebidas geladas', '10.00'),
    ('Limonada suíça', 'Bebidas geladas', '11.00'),
    ('Chá gelado de pêssego', 'Bebidas geladas', '9.00'),
    ('Água com gás', 'Bebidas geladas', '5.00'),
    ('Pão de queijo (unidade)', 'Salgados', '5.50'),
    ('Croissant de presunto e queijo', 'Salgados', '14.00'),
    ('Torrada com manteiga', 'Salgados', '8.00'),
    ('Quiche de alho-poró', 'Salgados', '16.00'),
    ('Bolo de cenoura com chocolate', 'Doces', '9.50'),
    ('Cookie de gotas de chocolate', 'Doces', '7.00'),
    ('Cheesecake de frutas vermelhas', 'Doces', '18.00'),
    ('Leite vegetal', 'Adicionais', '3.00'),
    ('Dose extra de espresso', 'Adicionais', '4.00'),
    ('Chantilly', 'Adicionais', '3.50'),
    ('Calda de caramelo', 'Adicionais', '2.50'),
    ('Tamanho grande', 'Adicionais', '4.00'),
]

COMBOS = [
    ('Combo Café da Manhã', '20.00', [
        ('Cappuccino', 1),
        ('Pão de queijo (unidade)', 2),
    ]),
    ('Combo Tarde Doce', '17.00', [
        ('Latte', 1),
        ('Cookie de gotas de chocolate', 1),
    ]),
]


class Command(BaseCommand):
    help = 'Carrega o cardápio inicial e as mesas do restaurante.'

    def handle(self, *args, **options):
        self.stdout.write('Carregando dados iniciais...\n')

        categorias = {}
        for nome, ordem, eh_adicional in CATEGORIAS:
            categoria, criada = Categoria.objects.get_or_create(
                nome=nome,
                defaults={'ordem': ordem, 'eh_adicional': eh_adicional},
            )
            categorias[nome] = categoria
            self._relatar('Categoria', nome, criada)

        for nome, categoria_nome, preco in PRATOS:
            _, criado = Prato.objects.get_or_create(
                nome=nome,
                defaults={
                    'categoria': categorias[categoria_nome],
                    'preco': Decimal(preco),
                },
            )
            self._relatar('Prato', nome, criado)

        for nome, preco, itens in COMBOS:
            combo, criado = Combo.objects.get_or_create(
                nome=nome,
                defaults={'preco': Decimal(preco)},
            )
            self._relatar('Combo', nome, criado)
            for prato_nome, quantidade in itens:
                ComboItem.objects.get_or_create(
                    combo=combo,
                    prato=Prato.objects.get(nome=prato_nome),
                    defaults={'quantidade': quantidade},
                )

        for numero in range(1, 13):
            identificacao = f'{numero:02d}'
            _, criada = Mesa.objects.get_or_create(
                identificacao=identificacao,
                defaults={'capacidade': 4},
            )
            self._relatar('Mesa', identificacao, criada)

        for identificacao, capacidade in [('Varanda 1', 6), ('Varanda 2', 2)]:
            _, criada = Mesa.objects.get_or_create(
                identificacao=identificacao,
                defaults={'capacidade': capacidade},
            )
            self._relatar('Mesa', identificacao, criada)

        self.stdout.write(
            self.style.SUCCESS(
                f'\nPronto: {Categoria.objects.count()} categorias, '
                f'{Prato.objects.count()} pratos, '
                f'{Combo.objects.count()} combos, '
                f'{Mesa.objects.count()} mesas.'
            )
        )

    def _relatar(self, tipo, nome, criado):
        if criado:
            self.stdout.write(self.style.SUCCESS(f'  + {tipo}: {nome}'))
        else:
            self.stdout.write(f'  = {tipo}: {nome} (já existia)')