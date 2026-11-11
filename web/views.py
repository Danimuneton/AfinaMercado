"""
Vistas de la interfaz web. Django ya no tiene la lógica de negocio: cada
vista llama al microservicio correspondiente y se encarga de la experiencia
de usuario (formularios, mensajes, idioma, errores amigables).
"""
import logging
from functools import wraps

from celery.result import AsyncResult
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import Http404, JsonResponse
from django.shortcuts import redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_POST

from afinamercado_project.celery import celery_app

from .forms import BuscarForm, CheckoutForm, InstrumentoForm, RegistroForm
from .integraciones import (
    AliadoNoConfigurado,
    ErrorAliado,
    PrecioService,
    obtener_conversor,
    obtener_servicio_aliado,
)
from .servicios import (
    CarritoServicio,
    CatalogoServicio,
    ErrorMicroservicio,
    MicroservicioNoDisponible,
    OrdenesServicio,
)

logger = logging.getLogger(__name__)


def _con_precio_usd(instrumentos):
    precios = PrecioService(obtener_conversor())
    for instrumento in instrumentos:
        instrumento["precio_usd"] = precios.equivalente(instrumento["precio_base"], "USD")
    return instrumentos


def _actualizar_contador(request, carrito):
    request.session["carrito_cantidad"] = carrito.get("cantidad", 0)


# ---------------------------------------------------------------------------
# Catálogo
# ---------------------------------------------------------------------------
def catalogo(request):
    servicio = CatalogoServicio()
    categorias, instrumentos, servicio_caido = [], [], False
    try:
        categorias = servicio.categorias()
    except MicroservicioNoDisponible:
        servicio_caido = True

    form = BuscarForm(request.GET or None, categorias=categorias)
    texto, categoria_id = "", None
    if form.is_valid():
        texto = form.cleaned_data["q"]
        categoria_id = form.cleaned_data["categoria"]

    if not servicio_caido:
        try:
            instrumentos = _con_precio_usd(servicio.instrumentos(texto=texto, categoria_id=categoria_id))
        except MicroservicioNoDisponible:
            servicio_caido = True

    if servicio_caido:
        messages.error(request, _("El catálogo no está disponible en este momento. Intenta de nuevo en unos minutos."))

    return render(
        request,
        "web/catalogo.html",
        {"form": form, "instrumentos": instrumentos, "filtrando": bool(texto or categoria_id), "servicio_caido": servicio_caido},
    )


def instrumento_detalle(request, instrumento_id):
    try:
        instrumento = CatalogoServicio().instrumento(instrumento_id)
    except MicroservicioNoDisponible as error:
        messages.error(request, error.detalle)
        return redirect("web:catalogo")
    except ErrorMicroservicio as error:
        if error.status == 404:
            raise Http404(error.detalle)
        raise
    _con_precio_usd([instrumento])
    es_propio = request.user.is_authenticated and instrumento["vendedor"].get("usuario_id") == request.user.id
    return render(request, "web/instrumento_detalle.html", {"instrumento": instrumento, "es_propio": es_propio})


@login_required
def publicar(request):
    servicio = CatalogoServicio()
    try:
        categorias = servicio.categorias()
    except MicroservicioNoDisponible as error:
        messages.error(request, error.detalle)
        return redirect("web:catalogo")

    form = InstrumentoForm(request.POST or None, categorias=categorias)
    if request.method == "POST" and form.is_valid():
        usuario = request.user
        try:
            vendedor = servicio.sincronizar_vendedor(
                usuario.id, usuario.get_full_name() or usuario.username, usuario.email
            )
            instrumento = servicio.publicar_instrumento(form.a_payload(vendedor["id"]))
        except MicroservicioNoDisponible as error:
            messages.error(request, error.detalle)
        except ErrorMicroservicio as error:
            form.agregar_errores_servicio(error.campos)
            messages.error(request, error.detalle)
        else:
            messages.success(request, _("¡Tu instrumento quedó publicado!"))
            return redirect("web:instrumento", instrumento_id=instrumento["id"])
    return render(request, "web/publicar.html", {"form": form})


@login_required
def mis_publicaciones(request):
    instrumentos = []
    try:
        instrumentos = CatalogoServicio().instrumentos(vendedor_usuario_id=request.user.id, estado="todos")
    except MicroservicioNoDisponible as error:
        messages.error(request, error.detalle)
    return render(request, "web/mis_publicaciones.html", {"instrumentos": instrumentos})


# ---------------------------------------------------------------------------
# Carrito
# ---------------------------------------------------------------------------
@login_required
def carrito(request):
    datos = {"items": [], "total": 0, "cantidad": 0}
    try:
        datos = CarritoServicio(request.user.id).ver()
        _actualizar_contador(request, datos)
    except MicroservicioNoDisponible as error:
        messages.error(request, error.detalle)
    return render(request, "web/carrito.html", {"carrito": datos})


@login_required
@require_POST
def carrito_agregar(request, instrumento_id):
    try:
        datos = CarritoServicio(request.user.id).agregar(instrumento_id)
    except ErrorMicroservicio as error:
        messages.warning(request, error.detalle)
        return redirect("web:instrumento", instrumento_id=instrumento_id)
    _actualizar_contador(request, datos)
    messages.success(request, _("Instrumento agregado a tu carrito."))
    return redirect("web:carrito")


@login_required
@require_POST
def carrito_quitar(request, instrumento_id):
    try:
        datos = CarritoServicio(request.user.id).quitar(instrumento_id)
        _actualizar_contador(request, datos)
        messages.info(request, _("Instrumento eliminado del carrito."))
    except ErrorMicroservicio as error:
        messages.warning(request, error.detalle)
    return redirect("web:carrito")


# ---------------------------------------------------------------------------
# Compra y órdenes
# ---------------------------------------------------------------------------
@login_required
def checkout(request):
    try:
        datos_carrito = CarritoServicio(request.user.id).ver()
    except MicroservicioNoDisponible as error:
        messages.error(request, error.detalle)
        return redirect("web:carrito")
    if not datos_carrito["items"]:
        messages.info(request, _("Tu carrito está vacío."))
        return redirect("web:catalogo")

    form = CheckoutForm(request.POST or None, initial={"email": request.user.email, "metodo_pago": "tarjeta"})
    if request.method == "POST" and form.is_valid():
        try:
            orden = OrdenesServicio(request.user.id).crear(**form.cleaned_data)
        except ErrorMicroservicio as error:
            form.agregar_errores_servicio(error.campos)
            messages.error(request, error.detalle)
        else:
            request.session["carrito_cantidad"] = 0
            messages.success(request, _("¡Compra realizada! Tu orden #%(id)s quedó pagada.") % {"id": orden["id"]})
            if orden.get("notificacion_encolada"):
                messages.info(request, _("Estamos enviando la confirmación a tu correo en segundo plano."))
            return redirect("web:orden", orden_id=orden["id"])

    return render(request, "web/checkout.html", {"form": form, "carrito": datos_carrito})


@login_required
def ordenes(request):
    lista = []
    try:
        lista = OrdenesServicio(request.user.id).listar()
    except MicroservicioNoDisponible as error:
        messages.error(request, error.detalle)
    return render(request, "web/ordenes.html", {"ordenes": lista})


@login_required
def orden_detalle(request, orden_id):
    try:
        orden = OrdenesServicio(request.user.id).detalle(orden_id)
    except MicroservicioNoDisponible as error:
        messages.error(request, error.detalle)
        return redirect("web:ordenes")
    except ErrorMicroservicio as error:
        raise Http404(error.detalle)
    return render(request, "web/orden_detalle.html", {"orden": orden})


# ---------------------------------------------------------------------------
# Servicio del equipo aliado
# ---------------------------------------------------------------------------
def aliado(request):
    contexto = {"resultado": None, "no_configurado": False, "error": False}
    try:
        contexto["resultado"] = obtener_servicio_aliado().obtener()
    except AliadoNoConfigurado:
        contexto["no_configurado"] = True
    except ErrorAliado:
        contexto["error"] = True
    return render(request, "web/aliado.html", contexto)


# ---------------------------------------------------------------------------
# Reportes asíncronos (Celery + Redis)
# ---------------------------------------------------------------------------
def solo_staff(vista):
    """Exige sesión iniciada y rol de administrador (403 si no lo es)."""

    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied
        return vista(request, *args, **kwargs)

    return envoltura


@solo_staff
def reportes(request):
    if request.method == "POST":
        try:
            tarea = celery_app.send_task(
                "reportes.generar_reporte_ventas",
                kwargs={"idioma": translation.get_language()},
                retry=False,
            )
        except Exception:
            logger.exception("No se pudo encolar el reporte")
            messages.error(request, _("El sistema de tareas en segundo plano no está disponible."))
            return redirect("web:reportes")
        messages.info(request, _("Generando el reporte en segundo plano. Puedes seguir navegando."))
        return redirect("web:reporte_estado", tarea_id=tarea.id)
    return render(request, "web/reportes.html")


@solo_staff
def reporte_estado(request, tarea_id):
    resultado = AsyncResult(tarea_id, app=celery_app)
    contexto = {"tarea_id": tarea_id, "estado": "PENDING", "reporte": None}
    try:
        contexto["estado"] = resultado.state
        if resultado.successful():
            contexto["reporte"] = resultado.result
    except Exception:
        logger.exception("No se pudo consultar el estado del reporte")
        contexto["estado"] = "UNKNOWN"
    return render(request, "web/reporte_estado.html", contexto)


# ---------------------------------------------------------------------------
# Healthcheck (Docker / monitoreo)
# ---------------------------------------------------------------------------
def salud(request):
    return JsonResponse({"status": "ok", "servicio": "django_web"})


# ---------------------------------------------------------------------------
# Cuentas
# ---------------------------------------------------------------------------
def registro(request):
    if request.user.is_authenticated:
        return redirect("web:catalogo")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, _("¡Bienvenido a AfinaMercado, %(nombre)s!") % {"nombre": usuario.username})
        return redirect("web:catalogo")
    return render(request, "web/registro.html", {"form": form})


