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
    readonly_fields = ('status',)

    def _comanda_aberta(self, obj):
        return obj is None or obj.esta_aberta

    def has_add_permission(self, request, obj=None):
        return self._comanda_aberta(obj) and super().has_add_permission(request, obj)

    def has_change_permission(self, request, obj=None):
        return self._comanda_aberta(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._comanda_aberta(obj) and super().has_delete_permission(request, obj)


@admin.register(Comanda)
class ComandaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'tipo', 'mesa', 'responsavel', 'status', 'valor_total', 'aberta_em')
    list_filter = ('status', 'tipo', 'mesa')
    search_fields = ('codigo', 'responsavel')
    date_hierarchy = 'aberta_em'
    inlines = [ItemComandaInline]

    CONTROLADOS_PELO_SISTEMA = (
        'codigo', 'status', 'aberta_em', 'fechada_em', 'forma_pagamento', 'total_pago',
    )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None and not obj.esta_aberta:
            return [campo.name for campo in obj._meta.fields]
        return self.CONTROLADOS_PELO_SISTEMA

    def has_delete_permission(self, request, obj=None):
        if obj is not None and not obj.esta_aberta:
            return False
        return super().has_delete_permission(request, obj)

    def get_actions(self, request):
        acoes = super().get_actions(request)
        acoes.pop('delete_selected', None)
        return acoes

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
    list_filter = ('status',)
    search_fields = ('comanda__codigo',)
    readonly_fields = ('comanda', 'status')
    inlines = [ItemAdicionalInline]

    def get_actions(self, request):
        acoes = super().get_actions(request)
        acoes.pop('delete_selected', None)
        return acoes

    def _comanda_aberta(self, obj):
        return obj is None or obj.comanda.esta_aberta

    def has_change_permission(self, request, obj=None):
        return self._comanda_aberta(obj) and super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self._comanda_aberta(obj) and super().has_delete_permission(request, obj)