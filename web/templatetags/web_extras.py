from datetime import datetime
from datetime import timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django import template
from django.utils import formats, timezone

from web.etiquetas import TODAS

register = template.Library()


@register.filter
def etiqueta(codigo):
    """Traduce un código de los microservicios ('pagada', 'excelente'...) al idioma activo."""
    return TODAS.get(codigo, codigo)


@register.filter
def moneda(valor, decimales=0):
    """Formatea un número según el idioma activo (separadores de miles y decimales)."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, TypeError, ValueError):
        return valor
    return formats.number_format(numero, decimal_pos=int(decimales), use_l10n=True, force_grouping=True)


@register.filter
def fecha_iso(valor):
    """Convierte la fecha ISO que devuelven los microservicios en datetime local."""
    if not valor:
        return ""
    try:
        fecha = datetime.fromisoformat(valor)
    except (TypeError, ValueError):
        return valor
    if timezone.is_naive(fecha):
        fecha = timezone.make_aware(fecha, dt_timezone.utc)
    return timezone.localtime(fecha)
