from django.urls import path

from .api_views import DashboardApi

app_name = 'atendimento_api'

urlpatterns = [
    path('dashboard/', DashboardApi.as_view(), name='dashboard'),
]