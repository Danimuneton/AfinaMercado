from decimal import Decimal

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _

from .etiquetas import CONDICIONES, METODOS_PAGO


class EstiloBootstrapMixin:
    """Agrega las clases de Bootstrap y marca los campos con error (accesibilidad)."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            widget = campo.widget
            clase = "form-select" if isinstance(widget, forms.Select) else "form-control"
            if isinstance(widget, forms.RadioSelect):
                clase = "form-check-input"
            widget.attrs.setdefault("class", clase)

    def _marcar_invalido(self, nombre):
        widget = self.fields[nombre].widget
        if "is-invalid" not in widget.attrs.get("class", ""):
            widget.attrs["class"] = f"{widget.attrs.get('class', '')} is-invalid".strip()
        widget.attrs["aria-invalid"] = "true"

    def full_clean(self):
        # Se marca después de validar (no en __init__, donde aún no están las opciones dinámicas).
        super().full_clean()
        for nombre in self.errors:
            if nombre in self.fields:
                self._marcar_invalido(nombre)

    def agregar_errores_servicio(self, campos):
        """Muestra en el formulario los errores por campo que devolvió el microservicio."""
        mapa = {"categoria_id": "categoria"}
        for campo, mensaje in (campos or {}).items():
            nombre = mapa.get(campo, campo)
            if nombre in self.fields:
                self.add_error(nombre, mensaje)
                self._marcar_invalido(nombre)
            else:
                self.add_error(None, mensaje)


class BuscarForm(EstiloBootstrapMixin, forms.Form):
    q = forms.CharField(
        label=_("Buscar"),
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={"placeholder": _("Marca o modelo, ej. Yamaha"), "type": "search"}),
    )
    categoria = forms.TypedChoiceField(label=_("Categoría"), required=False, coerce=int, empty_value=None)

    def __init__(self, *args, categorias=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].choices = [("", _("Todas las categorías"))] + [
            (c["id"], c["nombre"]) for c in categorias
        ]


class InstrumentoForm(EstiloBootstrapMixin, forms.Form):
    marca = forms.CharField(label=_("Marca"), max_length=100, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    modelo = forms.CharField(label=_("Modelo"), max_length=100)
    categoria = forms.TypedChoiceField(label=_("Categoría"), coerce=int)
    precio_base = forms.DecimalField(
        label=_("Precio (COP)"),
        min_value=Decimal("1000"),
        max_value=Decimal("10000000000"),
        decimal_places=2,
        help_text=_("Precio en pesos colombianos, sin puntos ni comas."),
        widget=forms.NumberInput(attrs={"step": "1000", "min": "1000", "inputmode": "numeric"}),
    )
    estado_condicion = forms.ChoiceField(label=_("Condición"), choices=list(CONDICIONES.items()))
    descripcion = forms.CharField(
        label=_("Descripción"),
        required=False,
        max_length=2000,
        widget=forms.Textarea(attrs={"rows": 4}),
        help_text=_("Opcional. Cuenta el estado, accesorios incluidos, etc."),
    )

    def __init__(self, *args, categorias=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["categoria"].choices = [("", _("Selecciona una categoría"))] + [
            (c["id"], c["nombre"]) for c in categorias
        ]

    def clean_marca(self):
        return self.cleaned_data["marca"].strip()

    def clean_modelo(self):
        return self.cleaned_data["modelo"].strip()

    def a_payload(self, vendedor_id):
        datos = self.cleaned_data
        return {
            "vendedor_id": vendedor_id,
            "categoria_id": datos["categoria"],
            "marca": datos["marca"],
            "modelo": datos["modelo"],
            "precio_base": str(datos["precio_base"]),
            "estado_condicion": datos["estado_condicion"],
            "descripcion": datos.get("descripcion", ""),
        }


class CheckoutForm(EstiloBootstrapMixin, forms.Form):
    direccion_envio = forms.CharField(
        label=_("Dirección de envío"),
        min_length=5,
        max_length=255,
        widget=forms.TextInput(attrs={"autocomplete": "street-address", "placeholder": _("Ej. Calle 10 # 20-30, Medellín")}),
    )
    metodo_pago = forms.ChoiceField(
        label=_("Método de pago"), choices=list(METODOS_PAGO.items()), widget=forms.RadioSelect
    )
    email = forms.EmailField(
        label=_("Correo para la confirmación"),
        required=False,
        help_text=_("Te enviaremos el resumen de la compra en segundo plano."),
    )


class RegistroForm(EstiloBootstrapMixin, UserCreationForm):
    email = forms.EmailField(label=_("Correo electrónico"), required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_("Ya existe una cuenta con este correo."))
        return email


class LoginForm(EstiloBootstrapMixin, AuthenticationForm):
    pass
