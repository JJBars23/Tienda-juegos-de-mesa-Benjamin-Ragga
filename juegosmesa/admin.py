from django.contrib import admin
from .models import Juego, Categoria, Pedido

# Register your models here.

@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio', 'stock')
    search_fields = ('nombre', 'categoria__nombre')
    list_filter = ('categoria',)

    

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nombre',)
    search_fields = ('nombre',) 

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('nombre_cliente', 'fecha_hora_pedido', 'total_pedido')
    search_fields = ('nombre_cliente',)
    list_filter = ('fecha_hora_pedido',)