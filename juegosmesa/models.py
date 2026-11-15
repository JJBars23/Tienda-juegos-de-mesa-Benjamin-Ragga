import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count, F, Sum
from django.db.models.signals import pre_delete
from django.dispatch import receiver

# Create your models here.
class Juego(models.Model):
    nombre = models.CharField(max_length=100)
    cantidad_jugadores = models.PositiveIntegerField()
    edad_minima = models.PositiveIntegerField()
    imagen = models.ImageField(upload_to='juegos/', blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=0)
    categorias = models.ManyToManyField('Categoria', related_name='juegos')
    disponibilidad = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)
    nombre_normalizado = models.CharField(
        max_length=300,
        editable=False,
        unique=True,
    )

    def __str__(self):
        return self.nombre

    def clean(self):
        super().clean()
        self.nombre_normalizado = self.nombre.casefold()
        if Categoria.objects.filter(
            nombre_normalizado=self.nombre_normalizado
        ).exclude(pk=self.pk).exists():
            raise ValidationError(
                {"nombre": "Ya existe una categoría con este nombre."}
            )

    def save(self, *args, **kwargs):
        self.nombre_normalizado = self.nombre.casefold()
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {"nombre_normalizado"}
        super().save(*args, **kwargs)

class Pedido(models.Model):
    codigo = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    nombre_cliente = models.CharField(max_length=100)
    correo_cliente = models.EmailField()
    telefono_cliente = models.CharField(max_length=20)
    fecha_hora_pedido = models.DateTimeField(auto_now_add=True)
    total_pedido = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    def __str__(self):
        return f"Pedido {self.codigo} - {self.nombre_cliente}"

    def recalcular_total(self, using=None):
        using = using or self._state.db
        total = self.detalles.using(using).aggregate(
            total=Sum(
                F("cantidad_juegos") * F("precio_unitario"),
                output_field=models.DecimalField(max_digits=20, decimal_places=0),
            )
        )["total"] or 0
        Pedido.objects.using(using).filter(pk=self.pk).update(total_pedido=total)
        self.total_pedido = total


class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        related_name="detalles",
        on_delete=models.CASCADE,
    )
    juego = models.ForeignKey(
        Juego,
        related_name="detalles_pedido",
        on_delete=models.CASCADE,
    )
    cantidad_juegos = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        blank=True,
        null=True,
    )

    def save(self, *args, **kwargs):
        using = kwargs.get("using") or self._state.db
        if self.precio_unitario is None:
            self.precio_unitario = Juego.objects.using(using).values_list(
                "precio",
                flat=True,
            ).get(pk=self.juego_id)
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"precio_unitario"}
        super().save(*args, **kwargs)
        Pedido.objects.using(using).get(pk=self.pedido_id).recalcular_total(using)

    def delete(self, *args, **kwargs):
        using = kwargs.get("using") or self._state.db
        pedido_id = self.pedido_id
        result = super().delete(*args, **kwargs)
        pedido = Pedido.objects.using(using).filter(pk=pedido_id).first()
        if pedido is not None:
            pedido.recalcular_total(using)
        return result

    @property
    def subtotal(self):
        return (self.precio_unitario or 0) * self.cantidad_juegos

    def __str__(self):
        return f"{self.juego} x {self.cantidad_juegos}"


@receiver(pre_delete, sender=Categoria)
def eliminar_juegos_sin_categorias(sender, instance, using, **kwargs):
    Juego.objects.using(using).annotate(
        cantidad_categorias=Count("categorias")
    ).filter(
        categorias=instance,
        cantidad_categorias=1,
    ).delete()


@receiver(pre_delete, sender=Juego)
def quitar_juego_de_pedidos(sender, instance, using, **kwargs):
    detalles = DetallePedido.objects.using(using).filter(juego_id=instance.pk)
    pedido_ids = list(detalles.values_list("pedido_id", flat=True).distinct())
    detalles.delete()

    for pedido in Pedido.objects.using(using).filter(pk__in=pedido_ids):
        if pedido.detalles.using(using).exists():
            pedido.recalcular_total(using)
        else:
            pedido.delete(using=using)