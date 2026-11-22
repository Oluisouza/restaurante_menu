from django import forms

from .models import Categoria, Prato

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

    def __init__(self, *args, restaurante, **kwargs):
        super().__init__(*args, **kwargs)
        self.instance.restaurante = restaurante
        self.fields['categoria'].queryset = Categoria.objects.filter(restaurante=restaurante)

    def _get_validation_exclusions(self):
        # O Django pula as constraints que envolvem campos fora do formulário,
        # e o restaurante fica fora de propósito: quem define é o __init__, não o usuário.
        # Como ele já foi carimbado, pedimos que "nome único no restaurante" seja conferido.
        exclusoes = super()._get_validation_exclusions()
        exclusoes.discard('restaurante')
        return exclusoes