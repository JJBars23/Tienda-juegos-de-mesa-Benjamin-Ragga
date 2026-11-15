from django.contrib import admin
from django.db.models import IntegerField, Sum, Value
from django.db.models.functions import Coalesce
from django.utils.html import format_html

from .models import Categoria, DetallePedido, Juego, Pedido

# Register your models here.

@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = ("miniatura", "nombre", "mostrar_categorias", "disponibilidad", "precio", "stock")
    search_fields = ('nombre', 'categorias__nombre')
    list_filter = ('categorias', 'disponibilidad',)
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

class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 1
    min_num = 1
    validate_min = True


class JuegoPedidoFilter(admin.SimpleListFilter):
    title = "juego"
    parameter_name = "juego"

    def lookups(self, request, model_admin):
        return Juego.objects.filter(
            detalles_pedido__pedido__isnull=False,
        ).distinct().order_by("nombre").values_list("pk", "nombre")

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(
                detalles__juego_id=self.value(),
            ).distinct()
        return queryset


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        'codigo',
        'mostrar_juegos',
        'nombre_cliente',
        'cantidad_total',
        'fecha_hora_pedido',
    )
    search_fields = ('nombre_cliente', 'correo_cliente')
    list_filter = ('fecha_hora_pedido', JuegoPedidoFilter)
    readonly_fields = ('codigo', 'fecha_hora_pedido', 'total_pedido')
    inlines = (DetallePedidoInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _cantidad_total=Coalesce(
                Sum('detalles__cantidad_juegos'),
                Value(0),
                output_field=IntegerField(),
            )
        ).prefetch_related('detalles__juego')

    @admin.display(description='Juegos')
    def mostrar_juegos(self, obj):
        return ', '.join(
            f'{detalle.juego.nombre} ({detalle.cantidad_juegos})'
            for detalle in obj.detalles.all()
        )

    @admin.display(description='Cantidad')
    def cantidad_total(self, obj):
        return obj._cantidad_total