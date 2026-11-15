from django.db import migrations, models


def normalizar_nombres_categoria(apps, schema_editor):
    Categoria = apps.get_model("juegosmesa", "Categoria")
    base_datos = schema_editor.connection.alias

    for categoria in Categoria.objects.using(base_datos).all().iterator():
        categoria.nombre_normalizado = categoria.nombre.casefold()
        categoria.save(using=base_datos, update_fields=["nombre_normalizado"])


class Migration(migrations.Migration):

    dependencies = [
        ("juegosmesa", "0002_fix_pedidos_and_multiple_categories"),
    ]

    operations = [
        migrations.AddField(
            model_name="categoria",
            name="nombre_normalizado",
            field=models.CharField(
                editable=False,
                max_length=300,
                null=True,
            ),
        ),
        migrations.RunPython(
            normalizar_nombres_categoria,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="categoria",
            name="nombre_normalizado",
            field=models.CharField(
                editable=False,
                max_length=300,
                unique=True,
            ),
        ),
    ]
