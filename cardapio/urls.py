from django.urls import path

from . import views

app_name = 'cardapio'

urlpatterns = [
    path('', views.lista_cardapio, name='lista_cardapio'),
    path('pratos/', views.lista_pratos, name='lista_pratos'),
    path('pratos/novo/', views.form_prato, name='novo_prato'),
    path('pratos/<int:pk>/editar/', views.form_prato, name='editar_prato'),
    path('pratos/<int:pk>/excluir/', views.excluir_prato, name='excluir_prato'),
]