from django import forms
from django.core.exceptions import ValidationError

from .models import Pedido


class PedidoPublicoForm(forms.ModelForm):
    cantidad_juegos = forms.IntegerField(
        label="Cantidad de unidades",
        min_value=1,
        error_messages={
            "min_value": "La cantidad debe estar entre 1 y 5.",
        },
        widget=forms.NumberInput(
            attrs={"class": "form-control", "min": 1}
        ),
    )

    class Meta:
        model = Pedido
        fields = (
            "nombre_cliente",
            "correo_cliente",
            "telefono_cliente",
        )
        widgets = {
            "nombre_cliente": forms.TextInput(attrs={"class": "form-control"}),
            "correo_cliente": forms.EmailInput(attrs={"class": "form-control"}),
            "telefono_cliente": forms.TelInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, juego, **kwargs):
        self.juego = juego
        super().__init__(*args, **kwargs)
        cantidad = self.fields["cantidad_juegos"]
        cantidad.widget.attrs["max"] = min(5, juego.stock)
        cantidad.help_text = f"Unidades disponibles: {juego.stock}."

    def clean_cantidad_juegos(self):
        cantidad = self.cleaned_data["cantidad_juegos"]
        if cantidad > self.juego.stock:
            raise ValidationError(
                f"Solo hay {self.juego.stock} unidades disponibles."
            )
        if cantidad > 5:
            raise ValidationError("La cantidad debe estar entre 1 y 5.")
        return cantidad