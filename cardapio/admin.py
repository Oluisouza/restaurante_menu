from django.contrib import admin

from .models import Categoria, Prato, Combo, ComboItem

admin.site.site_header = 'Comanda Digital'
admin.site.site_title = 'Comanda Digital'
admin.site.index_title = 'Administração do Restaurante'

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ordem', 'eh_adicional')
    list_editable = ('ordem', 'eh_adicional')
    search_fields = ('nome',)

@admin.register(Prato)
class PratoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'categoria', 'disponivel')
    list_editable = ('preco', 'categoria', 'disponivel')
    search_fields = ('nome', 'descricao')
    list_per_page = 25

class ComboItemInline(admin.TabularInline):
    model = ComboItem
    extra = 2
    autocomplete_fields = ('prato',)

@admin.register(Combo)
class ComboAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'preco_avulso', 'economia', 'disponivel')
    list_filter = ('disponivel',)
    search_fields = ('nome', )
    inlines = [ComboItemInline]