from django import forms

from .models import Pedido

class PedidoPublicoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = (
            "nombre_cliente",
            "correo_cliente",
            "telefono_cliente",
        )