from django.contrib import admin
from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, DetallePedido, Juego, Pedido


class CategoriaUniquenessTests(TestCase):
    def test_categoria_nombre_no_admite_duplicados_sin_distinguir_mayusculas(self):
        Categoria.objects.create(nombre="Clásico")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Categoria.objects.create(nombre="CLÁSICO")


class CategoryDeletionTests(TestCase):
    def create_game(self, nombre):
        return Juego.objects.create(
            nombre=nombre,
            cantidad_jugadores=4,
            edad_minima=8,
            precio=12990,
            stock=1,
        )

    def create_order(self, juego):
        pedido = Pedido.objects.create(
            nombre_cliente="Cliente de prueba",
            correo_cliente="cliente@example.com",
            telefono_cliente="123456789",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            juego=juego,
            cantidad_juegos=1,
        )
        return pedido

    def test_eliminar_categoria_elimina_juegos_que_solo_la_tienen_y_sus_pedidos(self):
        categoria = Categoria.objects.create(nombre="Estrategia")
        juego = self.create_game("Juego de estrategia")
        juego.categorias.add(categoria)
        pedido = self.create_order(juego)

        categoria.delete()

        self.assertFalse(Juego.objects.filter(pk=juego.pk).exists())
        self.assertFalse(Pedido.objects.filter(pk=pedido.pk).exists())

    def test_eliminar_categoria_conserva_juegos_con_otras_categorias(self):
        categoria = Categoria.objects.create(nombre="Estrategia")
        otra_categoria = Categoria.objects.create(nombre="Aventura")
        juego = self.create_game("Juego mixto")
        juego.categorias.add(categoria, otra_categoria)
        pedido = self.create_order(juego)

        Categoria.objects.filter(pk=categoria.pk).delete()

        juego.refresh_from_db()
        self.assertEqual(list(juego.categorias.all()), [otra_categoria])
        self.assertTrue(Pedido.objects.filter(pk=pedido.pk).exists())

    def test_eliminar_juego_elimina_solo_sus_pedidos(self):
        juego_a_eliminar = self.create_game("Juego eliminado")
        juego_del_mismo_pedido = self.create_game("Otro juego del pedido")
        juego_en_otro_pedido = self.create_game("Juego de otro pedido")
        pedido_a_eliminar = self.create_order(juego_a_eliminar)
        DetallePedido.objects.create(
            pedido=pedido_a_eliminar,
            juego=juego_del_mismo_pedido,
            cantidad_juegos=2,
        )
        otro_pedido = self.create_order(juego_en_otro_pedido)

        juego_a_eliminar.delete()

        pedido_a_eliminar.refresh_from_db()
        self.assertEqual(
            list(pedido_a_eliminar.detalles.values_list("juego__nombre", flat=True)),
            ["Otro juego del pedido"],
        )
        self.assertEqual(pedido_a_eliminar.total_pedido, 25980)
        self.assertTrue(Pedido.objects.filter(pk=otro_pedido.pk).exists())

    def test_eliminar_unico_juego_elimina_el_pedido(self):
        juego = self.create_game("Único juego")
        pedido = self.create_order(juego)

        juego.delete()

        self.assertFalse(Pedido.objects.filter(pk=pedido.pk).exists())


class PedidoCodeTests(TestCase):
    def test_codigo_se_genera_unico_al_crear_cada_pedido(self):
        pedido_a = Pedido.objects.create(
            nombre_cliente="Cliente A",
            correo_cliente="a@example.com",
            telefono_cliente="111111111",
        )
        pedido_b = Pedido.objects.create(
            nombre_cliente="Cliente B",
            correo_cliente="b@example.com",
            telefono_cliente="222222222",
        )

        self.assertIsNotNone(pedido_a.codigo)
        self.assertNotEqual(pedido_a.codigo, pedido_b.codigo)


class ChileanPriceFormatTests(TestCase):
    def test_formats_price_with_periods_as_thousand_separators(self):
        template = Template("{% load formatos %}${{ precio|clp }}")

        for precio, esperado in ((22990, "$22.990"), (1234567, "$1.234.567")):
            with self.subTest(precio=precio):
                self.assertEqual(
                    template.render(Context({"precio": precio})),
                    esperado,
                )


class StorefrontTemplateTests(TestCase):
    def test_home_uses_shared_base_template(self):
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, 'lang="es-CL"')
        self.assertContains(response, "Saltar al contenido")

    def test_game_detail_uses_shared_base_template(self):
        juego = Juego.objects.create(
            nombre="Juego de prueba",
            cantidad_jugadores=4,
            edad_minima=8,
            precio=12990,
            stock=1,
        )

        response = self.client.get(reverse("detalle_juego", args=[juego.pk]))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, "Juego de prueba")


class JuegoCategoriaAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)
        self.categorias = [
            Categoria.objects.create(nombre=f"Categoría {numero}")
            for numero in range(1, 4)
        ]
        self.juego = Juego.objects.create(
            nombre="Juego de prueba",
            cantidad_jugadores=4,
            edad_minima=8,
            precio=12990,
            stock=3,
        )
        self.juego.categorias.set(self.categorias)

    def test_juego_puede_tener_mas_de_dos_categorias(self):
        self.assertEqual(self.juego.categorias.count(), 3)

    def test_admin_permite_seleccionar_varias_categorias(self):
        response = self.client.get(reverse("admin:juegosmesa_juego_change", args=[self.juego.pk]))

        self.assertEqual(response.status_code, 200)
        campo = response.context["adminform"].form.fields["categorias"]
        self.assertEqual(len(campo.choices), 3)
        self.assertIn("categorias", admin.site._registry[Juego].filter_horizontal)


class PedidoAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

    def test_admin_de_pedidos_carga_con_los_campos_del_modelo(self):
        categoria = Categoria.objects.create(nombre="Estrategia")
        juego = Juego.objects.create(
            nombre="Juego de prueba",
            cantidad_jugadores=4,
            edad_minima=8,
            precio=12990,
            stock=3,
        )
        juego.categorias.add(categoria)
        pedido = Pedido.objects.create(
            nombre_cliente="Cliente de prueba",
            correo_cliente="cliente@example.com",
            telefono_cliente="123456789",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            juego=juego,
            cantidad_juegos=2,
        )
        otro_juego = Juego.objects.create(
            nombre="Otro juego de prueba",
            cantidad_jugadores=2,
            edad_minima=10,
            precio=5000,
            stock=1,
        )
        DetallePedido.objects.create(
            pedido=pedido,
            juego=otro_juego,
            cantidad_juegos=3,
        )

        response = self.client.get(reverse("admin:juegosmesa_pedido_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, str(pedido.codigo))
        self.assertContains(response, "Juego de prueba (2)")
        self.assertContains(response, "Otro juego de prueba (3)")
        self.assertContains(response, "Cliente de prueba")
        self.assertContains(response, "5")
        self.assertIn("fecha_hora_pedido", admin.site._registry[Pedido].list_display)
