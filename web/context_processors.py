def carrito(request):
    """Cantidad de ítems del carrito para el menú (se guarda en sesión para no llamar al servicio en cada página)."""
    return {"carrito_cantidad": request.session.get("carrito_cantidad", 0) if hasattr(request, "session") else 0}
