from django.contrib import admin

from .models import Mesa, Comanda, ItemComanda, ItemAdicional

@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('identificacao', 'capacidade', 'ativa', 'esta_ocupada')
    list_filter = ('ativa',)
    search_fields = ('identificacao',)

    @admin.display(boolean=True, description='Ocupada')
    def esta_ocupada(self, obj):
        return obj.ocupada

class ItemComandaInline(admin.TabularInline):
    model = ItemComanda
    extra = 1
    autocomplete_fields = ('prato', 'combo')
    fields = ('prato', 'combo', 'quantidade', 'preco_unitario', 'observacao', 'status')

@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'tipo', 'mesa', 'responsavel', 'status', 'valor_total', 'aberta_em',)
    list_filter = ('status', 'tipo', 'mesa')
    search_fields = ('codigo', 'responsavel',)
    readonly_fields = ('codigo', 'aberta_em', 'fechada_em', 'total_pago')
    date_hierarchy = 'aberta_em'
    inlines = [ItemComandaInline]

    @admin.display(description='Total')
    def valor_total(self, obj):
        return f'R$ {obj.total:.2f}'

class ItemAdicionalInline(admin.TabularInline):
    model = ItemAdicional
    extra = 1
    autocomplete_fields = ('prato',)

@admin.register(ItemComanda)
class ItemComandaAdmin(admin.ModelAdmin):
    list_display = ('comanda', 'descricao_produto', 'quantidade', 'preco_unitario', 'status', 'criado_em')
    list_filter = ('status', )
    inlines = [ItemAdicionalInline]
    actions = ['marcar_em_preparo', 'marcar_pronto', 'marcar_entregue']

    @admin.action(description='Marcar como em preparo')
    def marcar_em_preparo(self, request, queryset):
        atualizados = queryset.update(status=ItemComanda.Status.EM_PREPARO)
        self.message_user(request, f'{atualizados} item(ns) em preparo.')

    @admin.action(description='Marcar como Pronto')
    def marcar_pronto(self, request, queryset):
        atualizados = queryset.update(status=ItemComanda.Status.PRONTO)
        self.message_user(request, f'{atualizados} item(ns) pronto(s).')

    @admin.action(description='Marcar como Entregue')
    def marcar_entregue(self, request, queryset):
        atualizados = queryset.update(status=ItemComanda.Status.ENTREGUE)
        self.message_user(request, f'{atualizados} item(ns) entregue(s).')