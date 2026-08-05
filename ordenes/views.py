from django.views import View
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from .models import Carrito
from .services import OrdenService
from .domain.orden_builder import OrdenInvalidaError


@method_decorator(login_required, name="dispatch")
class CrearOrdenView(View):
    def post(self, request):
        carrito = get_object_or_404(Carrito, comprador=request.user)
        service = OrdenService()
        try:
            orden = service.crear_orden_desde_carrito(
                comprador=request.user,
                carrito=carrito,
                direccion_envio=request.POST.get("direccion"),
            )
            return JsonResponse({"ok": True, "total": str(orden.total)})
        except OrdenInvalidaError as e:
            return JsonResponse({"ok": False, "error": str(e)}, status=400)