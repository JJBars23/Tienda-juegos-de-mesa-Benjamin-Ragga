from django.db import models

# Create your models here.
class Juego(models.Model):
    nombre = models.CharField(max_length=100)
    cantidad_jugadores = models.PositiveIntegerField()
    edad_minima = models.PositiveIntegerField()
    imagen = models.ImageField(upload_to='juegos/', blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    categoria = models.ForeignKey('Categoria', on_delete=models.CASCADE)
    disponibilidad = models.BooleanField(default=True)
    stock = models.PositiveIntegerField(default=0)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class Categoria(models.Model):
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre

class Pedido(models.Model):
    nombre_cliente = models.CharField(max_length=100)
    correo_cliente = models.EmailField()
    telefono_cliente = models.CharField(max_length=20)
    fecha_hora_pedido = models.DateTimeField(auto_now_add=True)
    juegos = models.ForeignKey(Juego, on_delete=models.CASCADE)
    cantidad_juegos = models.PositiveIntegerField()
    total_pedido = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"Pedido de {self.nombre_cliente} - {self.fecha_hora_pedido}"