from django.contrib import admin
from django.utils.html import format_html

from .models import Categoria, Juego, Pedido
from .templatetags.formatos import clp

# Register your models here.

@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = (
        "miniatura",
        "nombre",
        "mostrar_categorias",
        "estado",
        "precio_formateado",
        "stock",
    )
    search_fields = ('nombre', 'categorias__nombre')
    list_filter = ('categorias', 'disponibilidad',)
    filter_horizontal = ("categorias",)

    @admin.display(description="Categorías")
    def mostrar_categorias(self, obj):
        return ", ".join(categoria.nombre for categoria in obj.categorias.all())

    @admin.display(description="Estado")
    def estado(self, obj):
        if not obj.disponibilidad:
            return "No disponible"
        if obj.stock == 0:
            return "Agotado"
        return "Disponible"

    @admin.display(description="Precio", ordering="precio")
    def precio_formateado(self, obj):
        return f"${clp(obj.precio)}"

    @admin.display(description='vista_previa')
    def miniatura(self, obj):
        if obj.imagen:
            return format_html('<img src="{}" style="height: 60px; border-radius: 4px;" />', obj.imagen.url)
        return '-'

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',) 

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'juego',
        'cantidad_juegos',
        'nombre_cliente',
        'total_pedido',
        'fecha_hora_pedido',
    )
    search_fields = ('nombre_cliente', 'correo_cliente', 'juego__nombre')
    list_filter = ('fecha_hora_pedido', 'juego')
    readonly_fields = ('codigo', 'fecha_hora_pedido')