from django.urls import path

from . import views

app_name = 'atendimento'

urlpatterns = [
    path('', views.salao, name='salao'),
    path('cozinha/', views.cozinha, name='cozinha'),

    path('comandas/', views.lista_comandas, name='lista_comandas'),
    path('comandas/nova/<str:tipo>', views.nova_comanda, name='nova_comanda'),
    path('comandas/<int:pk>/', views.detalhe_comanda, name='detalhe_comanda'),
    path('comandas/<int:pk>/itens/novo/', views.lancar_item, name='lancar_item'),
    path('comandas/<int:pk>/fechar/', views.fechar_comanda, name='fechar_comanda'),
    path('comandas/<int:pk>/cancelar/', views.cancelar_comanda, name='cancelar_comanda'),

    path('itens/<int:pk>/editar/', views.editar_item, name='editar_item'),
    path('itens/<int:pk>/excluir/', views.excluir_item, name='excluir_item'),

    path('mesas/<int:pk>/', views.detalhe_mesa, name='detalhe_mesa'),
]