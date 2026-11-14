import django.db.models.deletion
from django.db import migrations, models


def copiar_categoria_a_relacion_multiple(apps, schema_editor):
    Juego = apps.get_model("juegosmesa", "Juego")
    base_datos = schema_editor.connection.alias
    through = Juego.categorias.through

    through.objects.using(base_datos).bulk_create(
        [
            through(juego_id=juego_id, categoria_id=categoria_id)
            for juego_id, categoria_id in Juego.objects.using(base_datos)
            .exclude(categoria_legacy__isnull=True)
            .values_list("pk", "categoria_legacy_id")
        ],
        ignore_conflicts=True,
    )


def restaurar_una_categoria(apps, schema_editor):
    Juego = apps.get_model("juegosmesa", "Juego")
    base_datos = schema_editor.connection.alias

    for juego in Juego.objects.using(base_datos).all().iterator():
        categoria_id = (
            juego.categorias.using(base_datos)
            .values_list("pk", flat=True)
            .first()
        )
        if categoria_id is not None:
            Juego.objects.using(base_datos).filter(pk=juego.pk).update(
                categoria_legacy_id=categoria_id
            )


def completar_totales_pedidos(apps, schema_editor):
    Pedido = apps.get_model("juegosmesa", "Pedido")
    base_datos = schema_editor.connection.alias

    for pedido in Pedido.objects.using(base_datos).select_related("juegos").iterator():
        pedido.total_pedido = pedido.juegos.precio * pedido.cantidad_juegos
        pedido.save(using=base_datos, update_fields=["total_pedido"])


class Migration(migrations.Migration):
    dependencies = [
        ("juegosmesa", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="juego",
            old_name="categoria",
            new_name="categoria_legacy",
        ),
        migrations.AlterField(
            model_name="juego",
            name="categoria_legacy",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                to="juegosmesa.categoria",
            ),
        ),
        migrations.AddField(
            model_name="juego",
            name="categorias",
            field=models.ManyToManyField(
                related_name="juegos",
                to="juegosmesa.categoria",
            ),
        ),
        migrations.RunPython(
            copiar_categoria_a_relacion_multiple,
            restaurar_una_categoria,
        ),
        migrations.RemoveField(
            model_name="juego",
            name="categoria_legacy",
        ),
        migrations.RenameField(
            model_name="pedido",
            old_name="fecha_pedido",
            new_name="fecha_hora_pedido",
        ),
        migrations.RemoveField(
            model_name="pedido",
            name="hora_pedido",
        ),
        migrations.AddField(
            model_name="pedido",
            name="total_pedido",
            field=models.DecimalField(
                decimal_places=0,
                default=0,
                max_digits=10,
            ),
            preserve_default=False,
        ),
        migrations.RunPython(
            completar_totales_pedidos,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="juego",
            name="imagen",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="juegos/",
            ),
        ),
        migrations.AlterField(
            model_name="juego",
            name="precio",
            field=models.DecimalField(
                decimal_places=0,
                max_digits=10,
            ),
        ),
    ]
