from django.urls import path

from . import views

app_name = 'atendimento'

urlpatterns = [
    path('', views.salao, name='salao'),
    path('comandas/', views.lista_comandas, name='lista_comandas'),
    path('comandas/<int:pk>/', views.detalhe_comanda, name='detalhe_comanda'),
    path('mesas/<int:pk>/', views.detalhe_mesa, name='detalhe_mesa'),
]