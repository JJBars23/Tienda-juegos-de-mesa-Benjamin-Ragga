from django.contrib import admin
from django.contrib.auth import get_user_model
from django.template import Context, Template
from django.test import TestCase
from django.urls import reverse

from .models import Categoria, Juego, Pedido


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
        Pedido.objects.create(
            nombre_cliente="Cliente de prueba",
            correo_cliente="cliente@example.com",
            telefono_cliente="123456789",
            juegos=juego,
            cantidad_juegos=1,
            total_pedido=12990,
        )

        response = self.client.get(reverse("admin:juegosmesa_pedido_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cliente de prueba")
