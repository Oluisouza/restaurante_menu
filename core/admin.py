from django.contrib import admin

from .models import Perfil, Restaurante


@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'criado_em')
    search_fields = ('nome',)


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'restaurante', 'papel')
    list_filter = ('restaurante', 'papel')