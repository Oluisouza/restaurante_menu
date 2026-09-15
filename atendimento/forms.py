from django import forms

from cardapio.models import Combo, Prato

from .models import Comanda, ItemComanda, Mesa

class ComandaForm(forms.ModelForm):

    class Meta:
        model = Comanda
        fields = ['mesa', 'responsavel', 'taxa_servico']
        labels = {
            'mesa': 'Mesa',
            'responsavel': 'Responsável',
            'taxa_servico': 'Cobrar taxa de serviço (10%)',
        }
        help_texts = {
            'responsavel': 'Nome do cliente ou como identificá-lo.',
        }
        widgets = {
            'responsavel': forms.TextInput(attrs={'placeholder': 'Ex.: João, ou camisa azul', 'autofocus': True}),
        }

    def __init__(self, *args, tipo=None, **kwargs):
        super().__init__(*args, **kwargs)
        if tipo == Comanda.Tipo.MESA:
            self.fields['mesa'].queryset = Mesa.objects.filter(ativa=True)
            self.fields['mesa'].required = True
            self.fields['mesa'].empty_label = '- Escolha a mesa -'
        else:
            del self.fields['mesa']
            del self.fields['taxa_servico']

class ItemComandaForm(forms.ModelForm):

    class Meta:
        model = ItemComanda
        fields = ['prato', 'combo', 'quantidade', 'observacao']
        labels = {
            'prato': 'Item do cardápio',
            'combo': 'Combo',
            'quantidade': 'Quantidade',
            'observacao': 'Observação',
        }
        help_texts = {
            'observacao': 'Ex.: sem açucar, leite vegetal, bem passado.',
        }
        widgets = {
            'observacao': forms.TextInput(attrs={'placeholder': 'Opcional'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['prato'].queryset = (
            Prato.objects.filter(disponivel=True, categoria__eh_adicional=False).select_related('categoria')
        )
        self.fields['prato'].required = False
        self.fields['prato'].empty_label = '- escolha um item -'

        self.fields['combo'].queryset = Combo.objects.filter(disponivel=True)
        self.fields['combo'].required = False
        self.fields['combo'].empty_label = '- ou escolha um combo -'

        self.fields['preco_unitario'].required = False

class FechamentoForm(forms.ModelForm):

    class Meta:
        model = Comanda
        fields = ['forma_pagamento', 'taxa_servico', 'desconto']
        labels = {
            'forma_pagamento': 'Forma de Pagamento',
            'taxa_servico': 'Cobrar taxa de serviço (10%)',
            'desconto': 'Desconto (R$)',
        }
        help_texts = {
            'desconto': 'Deixe 0,00 se não houver desconto.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['forma_pagamento'].required = True