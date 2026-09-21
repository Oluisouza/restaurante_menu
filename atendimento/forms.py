from django import forms
from django.db.models import Q

from cardapio.models import Combo, Prato

from .models import Comanda, ItemAdicional, ItemComanda, Mesa

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

        disponiveis = Q(disponivel=True, categoria__eh_adicional=False)
        if self.instance.pk and self.instance.prato_id:
            disponiveis |= Q(pk=self.instance.prato_id)

        self.fields['prato'].queryset = (
            Prato.objects.filter(disponiveis).select_related('categoria').distinct()
        )
        self.fields['prato'].required = False
        self.fields['prato'].empty_label = '— escolha um item —'

        combos = Q(disponivel=True)
        if self.instance.pk and self.instance.combo_id:
            combos |= Q(pk=self.instance.combo_id)

        self.fields['combo'].queryset = Combo.objects.filter(combos).distinct()
        self.fields['combo'].required = False
        self.fields['combo'].empty_label = '— ou escolha um combo —'

class PersonalizarItemForm(forms.ModelForm):
    adicionais_escolhidos = forms.ModelMultipleChoiceField(
        queryset=Prato.objects.none(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label='Adicionais',
    )

    class Meta:
        model = ItemComanda
        fields = ['quantidade', 'observacao']
        labels = {'quantidade': 'Quantidade', 'observacao': 'Observação'}
        widgets = {
            'observacao': forms.TextInput(
                attrs={'placeholder': 'Ex.: sem açúcar', 'autofocus': True}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['adicionais_escolhidos'].queryset = Prato.objects.filter(
            disponivel=True, categoria__eh_adicional=True
        )
        if self.instance.pk:
            self.initial['adicionais_escolhidos'] = list(
                self.instance.adicionais.values_list('prato_id', flat=True)
            )

    def save(self, commit=True):
        item = super().save(commit=commit)
        if commit:
            self.sincronizar_adicionais(item)
        return item

    def sincronizar_adicionais(self, item):
        escolhidos = {p.pk: p for p in self.cleaned_data['adicionais_escolhidos']}
        atuais = {a.prato_id: a for a in item.adicionais.all()}
        for prato_id, adicional in atuais.items():
            if prato_id not in escolhidos:
                adicional.delete()
        for prato_id, prato in escolhidos.items():
            if prato_id not in atuais:
                ItemAdicional.objects.create(item_comanda=item, prato=prato)

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
        if self.instance.tipo != Comanda.Tipo.MESA:
            del self.fields['taxa_servico']