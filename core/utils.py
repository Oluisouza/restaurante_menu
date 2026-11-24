from functools import wraps

from django.core.exceptions import ObjectDoesNotExist, PermissionDenied


def restaurante_atual(request):
    """O restaurante do usuário logado. Sem perfil, sem acesso."""
    try:
        return request.user.perfil.restaurante
    except ObjectDoesNotExist:
        raise PermissionDenied('Seu usuário não está vinculado a nenhum restaurante.')


def gerente_requerido(view):
    """Deixa a view passar só para quem tem papel de gerente. Os demais recebem 403."""

    @wraps(view)
    def envolvida(request, *args, **kwargs):
        restaurante_atual(request)  # sem perfil, o 403 sai daqui
        if not request.user.perfil.eh_gerente:
            raise PermissionDenied('Esta área é só para gerentes.')
        return view(request, *args, **kwargs)

    return envolvida