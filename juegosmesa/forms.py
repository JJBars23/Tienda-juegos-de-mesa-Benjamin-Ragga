from django import forms
from django.core.exceptions import ValidationError

from .models import Pedido

class PedidoPublicoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = (
            "nombre_cliente",
            "correo_cliente",
            "telefono_cliente",
            "cantidad_juegos",
        )
        widgets = {
            "cantidad_juegos": forms.NumberInput(attrs={"min": 1, "max": 5}),
        }

    def clean_cantidad_juegos(self):
        cantidad = self.cleaned_data["cantidad_juegos"]
        if not 1 <= cantidad <= 5:
            raise ValidationError("La cantidad debe estar entre 1 y 5.")
        return cantidad