from django.urls import path

from .api_views import PratoDetail, PratoListCreate

app_name = 'cardapio_api'

urlpatterns = [
    path('pratos/', PratoListCreate.as_view(), name='lista_pratos'),
    path('pratos/<int:pk>/', PratoDetail.as_view(), name='detalhe_prato'),
]