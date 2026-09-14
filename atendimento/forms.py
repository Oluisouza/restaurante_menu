from django import forms

from cardapio.models import Combo, Prato

from .models import Comanda, ItemComanda, Mesa

class ComandaForm(forms.ModelForm):

    class Meta:
        model = Comanda
        fields = ['tipo', 'mesa', 'responsavel', 'taxa_servico']
        labels = {
            'tipo': 'Tipo de Atendimento',
            'mesa': 'Mesa',
            'responsavel': 'Responsável',
            'taxa_servico': 'Cobrar taxa de serviço (10%)',
        }
        help_texts = {
            'responsavel': 'Nome do cliente ou como identificá-lo.',
            'mesa': 'Obrigatório apenas para comanda de mesa.',        
        }
        widgets = {
            'responsavel': forms.TextInput(attrs={'placeholder': 'Ex.: João, ou camisa azul'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['mesa'].queryset = Mesa.objects.filter(ativa=True)
        self.fields['mesa'].required = False
        self.fields['mesa'].empty_label = 'Sem mesa (viagem ou balcao)'

class ItemComandaForm(forms.ModelForm):

    class Meta:
        model = ItemComanda
        fields = ['prato', 'combo', 'quantidade', 'observacao', 'preco_unitario']
        labels = {
            'prato': 'Item do cardápio',
            'combo': 'Combo',
            'quantidade': 'Quantidade',
            'observacao': 'Observação',
            'preco_unitario': 'Preço unitário',
        }
        help_texts = {
            'preco_unitario': 'Deixe em branco para usar o preço de tabela',
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