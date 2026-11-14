from django.contrib import admin
from django.utils.html import format_html
from .models import Juego, Categoria, Pedido

# Register your models here.

@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = ("miniatura", "nombre", "mostrar_categorias", "precio", "stock")
    search_fields = ('nombre', 'categorias__nombre')
    list_filter = ('categorias',)
    filter_horizontal = ("categorias",)

    @admin.display(description="Categorías")
    def mostrar_categorias(self, obj):
        return ", ".join(categoria.nombre for categoria in obj.categorias.all())

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
    list_display = ('nombre_cliente', 'fecha_hora_pedido', 'total_pedido')
    search_fields = ('nombre_cliente',)
    list_filter = ('fecha_hora_pedido',)