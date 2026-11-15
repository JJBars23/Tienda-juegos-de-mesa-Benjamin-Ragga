import uuid

from django.db import migrations, models
import django.db.models.deletion


def convertir_pedidos_existentes(apps, schema_editor):
    Pedido = apps.get_model("juegosmesa", "Pedido")
    DetallePedido = apps.get_model("juegosmesa", "DetallePedido")
    base_datos = schema_editor.connection.alias

    pedidos = Pedido.objects.using(base_datos).select_related("juegos")
    for pedido in pedidos.iterator():
        pedido.codigo = uuid.uuid4()
        pedido.save(using=base_datos, update_fields=["codigo"])
        DetallePedido.objects.using(base_datos).create(
            pedido_id=pedido.pk,
            juego_id=pedido.juegos_id,
            cantidad_juegos=pedido.cantidad_juegos,
            precio_unitario=pedido.juegos.precio,
        )


class Migration(migrations.Migration):

    dependencies = [
        ("juegosmesa", "0003_categoria_nombre_normalizado"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="codigo",
            field=models.UUIDField(
                editable=False,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="pedido",
            name="total_pedido",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                max_digits=10,
            ),
        ),
        migrations.CreateModel(
            name="DetallePedido",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("cantidad_juegos", models.PositiveIntegerField()),
                (
                    "precio_unitario",
                    models.DecimalField(
                        blank=True,
                        decimal_places=0,
                        max_digits=10,
                        null=True,
                    ),
                ),
                (
                    "juego",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="detalles_pedido",
                        to="juegosmesa.juego",
                    ),
                ),
                (
                    "pedido",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="detalles",
                        to="juegosmesa.pedido",
                    ),
                ),
            ],
        ),
        migrations.RunPython(
            convertir_pedidos_existentes,
            migrations.RunPython.noop,
        ),
        migrations.RemoveField(
            model_name="pedido",
            name="juegos",
        ),
        migrations.RemoveField(
            model_name="pedido",
            name="cantidad_juegos",
        ),
        migrations.AlterField(
            model_name="pedido",
            name="codigo",
            field=models.UUIDField(
                default=uuid.uuid4,
                editable=False,
                unique=True,
            ),
        ),
    ]
