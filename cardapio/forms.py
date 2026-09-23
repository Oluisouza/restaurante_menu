from django import forms
from decimal import Decimal

from .models import Prato

class PratoForm(forms.ModelForm):
    preco = forms.DecimalField(
        label='Preço (R$)', min_value=0, max_digits=10, decimal_places=2
    )
    
    class Meta:
        model = Prato
        fields = ['nome', 'descricao', 'preco', 'categoria', 'imagem', 'disponivel']
        labels = {
            'nome': 'Nome do Item',
            'descricao': 'Descrição',
            'preco': 'Preço (R$)',
            'categoria': 'Categoria',
            'imagem': 'Foto',
            'disponivel': 'Disponivel para venda',
        }
        help_texts = {
            'disponivel': 'Desmarque quando o item acabar, sem precisar excluí-lo.',
        }

    def clean_preco(self):
        preco = self.cleaned_data.get('preco')
        if preco is not None and preco <= Decimal('0'):
            raise forms.ValidationError(
                '⚠︎ O preço deve ser maior que zero. Item de cortesia se registra como desconto no fechamento da comanda.'
            )
        return preco
