import uuid

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Count
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
    juego = models.ForeignKey(Juego, on_delete=models.CASCADE)
    cantidad_juegos = models.PositiveIntegerField()
    nombre_cliente = models.CharField(max_length=100)
    correo_cliente = models.EmailField()
    telefono_cliente = models.CharField(max_length=20)
    fecha_hora_pedido = models.DateTimeField(auto_now_add=True)
    total_pedido = models.DecimalField(max_digits=10, decimal_places=0, default=0)

    def __str__(self):
        return f"Pedido {self.codigo} - {self.nombre_cliente}"

@receiver(pre_delete, sender=Categoria)
def eliminar_juegos_sin_categorias(sender, instance, using, **kwargs):
    Juego.objects.using(using).annotate(
        cantidad_categorias=Count("categorias")
    ).filter(
        categorias=instance,
        cantidad_categorias=1,
    ).delete()