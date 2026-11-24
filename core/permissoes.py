from rest_framework.permissions import SAFE_METHODS, BasePermission


class GerenteAltera(BasePermission):
    """Na API, todos leem; só o gerente cria, altera ou apaga."""

    message = 'Só o gerente pode alterar estes dados.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:  # GET, HEAD e OPTIONS
            return True
        perfil = getattr(request.user, 'perfil', None)
        return perfil is not None and perfil.eh_gerente