import uuid

import django.db.models.deletion
from django.db import migrations, models


def separar_pedidos_por_juego(apps, schema_editor):
    Pedido = apps.get_model("juegosmesa", "Pedido")
    DetallePedido = apps.get_model("juegosmesa", "DetallePedido")
    base_datos = schema_editor.connection.alias
    pedidos_nuevos = []

    pedido_ids = list(
        Pedido.objects.using(base_datos).order_by("pk").values_list("pk", flat=True)
    )
    for pedido_id in pedido_ids:
        pedido = Pedido.objects.using(base_datos).get(pk=pedido_id)
        detalles = list(
            DetallePedido.objects.using(base_datos)
            .filter(pedido_id=pedido_id)
            .order_by("pk")
            .select_related("juego")
        )
        if not detalles:
            pedido.delete(using=base_datos)
            continue

        for indice, detalle in enumerate(detalles):
            precio = detalle.precio_unitario
            if precio is None:
                precio = detalle.juego.precio
            total = precio * detalle.cantidad_juegos

            if indice == 0:
                Pedido.objects.using(base_datos).filter(pk=pedido_id).update(
                    juego_id=detalle.juego_id,
                    cantidad_juegos=detalle.cantidad_juegos,
                    total_pedido=total,
                )
            else:
                pedidos_nuevos.append(
                    Pedido(
                        codigo=uuid.uuid4(),
                        juego_id=detalle.juego_id,
                        cantidad_juegos=detalle.cantidad_juegos,
                        nombre_cliente=pedido.nombre_cliente,
                        correo_cliente=pedido.correo_cliente,
                        telefono_cliente=pedido.telefono_cliente,
                        fecha_hora_pedido=pedido.fecha_hora_pedido,
                        total_pedido=total,
                    )
                )

    Pedido.objects.using(base_datos).bulk_create(pedidos_nuevos)


def reconstruir_detalles(apps, schema_editor):
    Pedido = apps.get_model("juegosmesa", "Pedido")
    DetallePedido = apps.get_model("juegosmesa", "DetallePedido")
    base_datos = schema_editor.connection.alias

    for pedido in Pedido.objects.using(base_datos).select_related("juego").iterator():
        precio = pedido.total_pedido
        if pedido.cantidad_juegos:
            precio /= pedido.cantidad_juegos
        else:
            precio = pedido.juego.precio
        DetallePedido.objects.using(base_datos).create(
            pedido_id=pedido.pk,
            juego_id=pedido.juego_id,
            cantidad_juegos=pedido.cantidad_juegos,
            precio_unitario=precio,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("juegosmesa", "0004_pedido_codigo_detalles"),
    ]

    operations = [
        migrations.AddField(
            model_name="pedido",
            name="juego",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="juegosmesa.juego",
            ),
        ),
        migrations.AddField(
            model_name="pedido",
            name="cantidad_juegos",
            field=models.PositiveIntegerField(null=True),
        ),
        migrations.RunPython(
            separar_pedidos_por_juego,
            reconstruir_detalles,
        ),
        migrations.AlterField(
            model_name="pedido",
            name="juego",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                to="juegosmesa.juego",
            ),
        ),
        migrations.AlterField(
            model_name="pedido",
            name="cantidad_juegos",
            field=models.PositiveIntegerField(),
        ),
        migrations.DeleteModel(
            name="DetallePedido",
        ),
    ]
