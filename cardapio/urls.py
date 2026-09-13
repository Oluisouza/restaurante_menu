from django.urls import path

from . import views

app_name = 'cardapio'

urlpatterns = [
    path('', views.lista_cardapio, name='lista_cardapio'),
]