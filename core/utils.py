from django.core.exceptions import ObjectDoesNotExist, PermissionDenied


def restaurante_atual(request):
    """O restaurante do usuário logado. Sem perfil, sem acesso."""
    try:
        return request.user.perfil.restaurante
    except ObjectDoesNotExist:
        raise PermissionDenied('Seu usuário não está vinculado a nenhum restaurante.')