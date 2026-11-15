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
        Juego.objects.create(
            nombre="Juego disponible",
            cantidad_jugadores=2,
            edad_minima=8,
            precio=5000,
            stock=1,
        )
        Juego.objects.create(
            nombre="Juego agotado",
            cantidad_jugadores=2,
            edad_minima=8,
            precio=5000,
            stock=0,
        )
        Juego.objects.create(
            nombre="Juego no disponible",
            cantidad_jugadores=2,
            edad_minima=8,
            precio=5000,
            stock=3,
            disponibilidad=False,
        )
        response = self.client.get(reverse("home"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "base.html")
        self.assertContains(response, 'lang="es-CL"')
        self.assertContains(response, "Saltar al contenido")
        self.assertContains(response, "Juego disponible")
        self.assertNotContains(response, "Juego agotado")
        self.assertNotContains(response, "Juego no disponible")

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

    def test_juegos_agotados_o_no_disponibles_responden_404_en_detalle(self):
        juegos_no_publicos = [
            Juego.objects.create(
                nombre="Juego agotado",
                cantidad_jugadores=2,
                edad_minima=8,
                precio=5000,
                stock=0,
            ),
            Juego.objects.create(
                nombre="Juego no disponible",
                cantidad_jugadores=2,
                edad_minima=8,
                precio=5000,
                stock=3,
                disponibilidad=False,
            ),
        ]

        for juego in juegos_no_publicos:
            with self.subTest(juego=juego.nombre):
                url = reverse("detalle_juego", args=[juego.pk])
                self.assertEqual(self.client.get(url).status_code, 404)
                self.assertEqual(
                    self.client.post(url, {"cantidad_juegos": 1}).status_code,
                    404,
                )
                self.assertEqual(Pedido.objects.count(), 0)


class PublicOrderTests(TestCase):
    def setUp(self):
        self.juego = Juego.objects.create(
            nombre="Juego para pedido",
            cantidad_jugadores=4,
            edad_minima=8,
            precio=12990,
            stock=4,
        )
        self.checkout_url = reverse("confirmar_pedido")
        self.datos_checkout = {
            "nombre_cliente": "Cliente de prueba",
            "correo_cliente": "cliente@example.com",
            "telefono_cliente": "123456789",
        }

    def agregar_juego(self, juego=None, cantidad=2):
        juego = juego or self.juego
        return self.client.post(
            reverse("detalle_juego", args=[juego.pk]),
            {"cantidad_juegos": cantidad},
        )

    def test_visitante_puede_enviar_un_pedido_y_se_descontar_el_stock(self):
        respuesta_agregar = self.agregar_juego()
        self.assertRedirects(respuesta_agregar, reverse("carrito"))
        self.assertEqual(Pedido.objects.count(), 0)

        response = self.client.post(
            self.checkout_url,
            self.datos_checkout,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "juegos/pedido_confirmado.html")
        pedido = Pedido.objects.get(nombre_cliente="Cliente de prueba")
        detalle = pedido.detalles.get()
        self.assertEqual(detalle.juego, self.juego)
        self.assertEqual(detalle.cantidad_juegos, 2)
        self.assertEqual(pedido.total_pedido, 25980)
        self.assertContains(response, str(pedido.codigo))
        self.assertContains(response, "Juego para pedido")
        self.assertContains(response, "Cliente de prueba")
        self.assertContains(response, "2 unidad(es)")
        self.assertContains(response, "$25.980 CLP")
        self.assertContains(response, "Fecha:")

        response_recargada = self.client.get(response.redirect_chain[0][0])
        self.assertEqual(response_recargada.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 1)

        self.juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 2)

    def test_no_permite_pedir_mas_unidades_que_el_stock_disponible(self):
        response = self.agregar_juego(cantidad=5)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Solo hay 4 unidades disponibles.")
        self.assertEqual(Pedido.objects.count(), 0)
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 4)

    def test_cantidad_debe_estar_entre_1_y_5(self):
        self.juego.stock = 10
        self.juego.save(update_fields=["stock"])

        for cantidad in (0, 6):
            with self.subTest(cantidad=cantidad):
                response = self.agregar_juego(cantidad=cantidad)

                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response,
                    "La cantidad debe estar entre 1 y 5.",
                )
                self.assertEqual(Pedido.objects.count(), 0)

        self.juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 10)

    def test_correo_invalido_no_guarda_el_pedido(self):
        self.agregar_juego()
        datos_checkout = {
            **self.datos_checkout,
            "correo_cliente": "correo-invalido",
        }

        response = self.client.post(self.checkout_url, datos_checkout)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "juegos/carrito.html")
        self.assertIn("correo_cliente", response.context["pedido_form"].errors)
        self.assertEqual(Pedido.objects.count(), 0)
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 4)

    def test_no_acepta_pedido_si_juego_esta_agotado(self):
        self.juego.stock = 0
        self.juego.save(update_fields=["stock"])

        response = self.client.post(
            reverse("detalle_juego", args=[self.juego.pk]),
            {"cantidad_juegos": 1},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(Pedido.objects.count(), 0)
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 0)

    def test_pedido_puede_incluir_varios_juegos(self):
        otro_juego = Juego.objects.create(
            nombre="Otro juego para pedido",
            cantidad_jugadores=2,
            edad_minima=10,
            precio=5000,
            stock=2,
        )
        self.agregar_juego()
        respuesta_segundo_juego = self.agregar_juego(otro_juego, cantidad=1)
        self.assertRedirects(respuesta_segundo_juego, reverse("carrito"))

        response = self.client.post(
            self.checkout_url,
            self.datos_checkout,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        pedido = Pedido.objects.get()
        self.assertEqual(pedido.detalles.count(), 2)
        self.assertEqual(pedido.total_pedido, 30980)
        self.assertContains(response, "Juego para pedido")
        self.assertContains(response, "Otro juego para pedido")
        self.juego.refresh_from_db()
        otro_juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 2)
        self.assertEqual(otro_juego.stock, 1)

    def test_stock_se_revalida_al_confirmar_el_carrito(self):
        self.agregar_juego()
        self.juego.stock = 1
        self.juego.save(update_fields=["stock"])

        response = self.client.post(self.checkout_url, self.datos_checkout)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "juegos/carrito.html")
        self.assertContains(response, "Solo hay 1 unidad disponible.")
        self.assertEqual(Pedido.objects.count(), 0)
        self.juego.refresh_from_db()
        self.assertEqual(self.juego.stock, 1)

    def test_carrito_permite_actualizar_y_quitar_juegos(self):
        self.agregar_juego()

        response = self.client.post(
            reverse("actualizar_carrito", args=[self.juego.pk]),
            {"cantidad_juegos": 3},
        )
        self.assertRedirects(response, reverse("carrito"))
        self.assertEqual(
            self.client.get(reverse("carrito")).context["carrito_items"][0]["cantidad"],
            3,
        )

        response = self.client.post(
            reverse("quitar_del_carrito", args=[self.juego.pk]),
        )
        self.assertRedirects(response, reverse("carrito"))
        self.assertContains(
            self.client.get(reverse("carrito")),
            "Aún no has agregado juegos",
        )


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

    def test_admin_muestra_si_el_juego_esta_agotado_o_no_disponible(self):
        Juego.objects.create(
            nombre="Juego agotado",
            cantidad_jugadores=2,
            edad_minima=8,
            precio=5000,
            stock=0,
        )
        Juego.objects.create(
            nombre="Juego no disponible",
            cantidad_jugadores=2,
            edad_minima=8,
            precio=5000,
            stock=3,
            disponibilidad=False,
        )

        response = self.client.get(reverse("admin:juegosmesa_juego_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Agotado")
        self.assertContains(response, "No disponible")

    def test_admin_muestra_el_precio_en_pesos_chilenos(self):
        response = self.client.get(reverse("admin:juegosmesa_juego_changelist"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "$12.990")


class PedidoAdminTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test-password",
        )
        self.client.force_login(self.user)

    def crear_juego(self, nombre):
        return Juego.objects.create(
            nombre=nombre,
            cantidad_jugadores=4,
            edad_minima=8,
            precio=12990,
            stock=3,
        )

    def crear_pedido(self, juego, nombre, correo):
        pedido = Pedido.objects.create(
            nombre_cliente=nombre,
            correo_cliente=correo,
            telefono_cliente="123456789",
        )
        DetallePedido.objects.create(
            pedido=pedido,
            juego=juego,
            cantidad_juegos=1,
        )
        return pedido

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

    def test_admin_filtra_pedidos_por_juego(self):
        juego = self.crear_juego("Juego filtrado")
        otro_juego = self.crear_juego("Otro juego")
        pedido = self.crear_pedido(juego, "Cliente A", "a@example.com")
        self.crear_pedido(otro_juego, "Cliente B", "b@example.com")

        response = self.client.get(
            reverse("admin:juegosmesa_pedido_changelist"),
            {"juego": juego.pk},
        )

        self.assertEqual(response.status_code, 200)
        pedidos_mostrados = list(response.context["cl"].queryset)
        self.assertEqual([item.pk for item in pedidos_mostrados], [pedido.pk])

    def test_admin_busca_pedidos_por_nombre_o_correo(self):
        juego = self.crear_juego("Juego de búsqueda")
        pedido = self.crear_pedido(
            juego,
            "Cliente Buscable",
            "correo-buscable@example.com",
        )
        url = reverse("admin:juegosmesa_pedido_changelist")

        for termino in ("Cliente Buscable", "correo-buscable@example.com"):
            with self.subTest(termino=termino):
                response = self.client.get(url, {"q": termino})

                self.assertEqual(response.status_code, 200)
                self.assertContains(response, str(pedido.codigo))
