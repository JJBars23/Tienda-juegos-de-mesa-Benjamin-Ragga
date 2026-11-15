from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CantidadPedidoForm, PedidoPublicoForm
from .models import Categoria, DetallePedido, Juego, Pedido


CARRITO_SESSION_KEY = "carrito_pedido"


class StockActualizadoError(Exception):
    pass


def _cantidades_carrito(request):
    carrito = request.session.get(CARRITO_SESSION_KEY, {})
    if not isinstance(carrito, dict):
        request.session.pop(CARRITO_SESSION_KEY, None)
        messages.warning(
            request,
            "El carrito anterior no era válido y se ha vaciado.",
        )
        return {}

    carrito_valido = {
        str(juego_id): cantidad
        for juego_id, cantidad in carrito.items()
        if str(juego_id).isdecimal()
        and isinstance(cantidad, int)
        and not isinstance(cantidad, bool)
        and cantidad > 0
    }
    if carrito_valido != carrito:
        request.session[CARRITO_SESSION_KEY] = carrito_valido
        messages.warning(
            request,
            "Se quitaron datos no válidos del carrito.",
        )
    return carrito_valido


def _contexto_carrito(request, pedido_form=None):
    cantidades = _cantidades_carrito(request)
    juegos = {
        str(juego.pk): juego
        for juego in Juego.objects.filter(
            pk__in=[int(juego_id) for juego_id in cantidades]
        )
    }
    items = []
    total = 0
    juegos_eliminados = False

    for juego_id, cantidad in list(cantidades.items()):
        juego = juegos.get(juego_id)
        if juego is None:
            cantidades.pop(juego_id)
            juegos_eliminados = True
            continue

        error = None
        if not juego.disponibilidad:
            error = "Este juego ya no está disponible para la venta."
        elif juego.stock == 0:
            error = "Este juego está agotado."
        elif cantidad > 5:
            error = "La cantidad máxima es 5 unidades por juego."
        elif cantidad > juego.stock:
            unidad = "unidad" if juego.stock == 1 else "unidades"
            disponible = "disponible" if juego.stock == 1 else "disponibles"
            error = f"Solo hay {juego.stock} {unidad} {disponible}."

        items.append({
            "juego": juego,
            "cantidad": cantidad,
            "subtotal": juego.precio * cantidad,
            "error": error,
            "puede_actualizar": juego.disponibilidad and juego.stock > 0,
            "cantidad_form": CantidadPedidoForm(
                initial={"cantidad_juegos": cantidad},
                juego=juego,
            ),
        })
        total += juego.precio * cantidad

    if juegos_eliminados:
        request.session[CARRITO_SESSION_KEY] = cantidades
        messages.warning(
            request,
            "Se quitaron del carrito juegos que ya no existen.",
        )

    return {
        "carrito_items": items,
        "total_carrito": total,
        "carrito_valido": bool(items) and all(
            item["error"] is None for item in items
        ),
        "pedido_form": pedido_form or PedidoPublicoForm(),
    }


def Home(request):
    nombre = request.GET.get("nombre", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()

    juegos = Juego.objects.filter(
        disponibilidad=True,
        stock__gt=0,
    ).prefetch_related("categorias")

    if nombre:
        juegos = juegos.filter(nombre__icontains=nombre)

    if categoria_id.isdecimal():
        juegos = juegos.filter(categorias__id=int(categoria_id)).distinct()

    contexto = {
        "juegos": juegos,
        "categorias": Categoria.objects.all().order_by("nombre"),
        "nombre_busqueda": nombre,
        "categoria_seleccionada": categoria_id,
    }
    return render(request, "index.html", contexto)


def detalle_juego(request, pk):
    if request.method == "POST":
        with transaction.atomic():
            juego = get_object_or_404(
                Juego.objects.select_for_update(),
                pk=pk,
                disponibilidad=True,
                stock__gt=0,
            )
            form = CantidadPedidoForm(request.POST, juego=juego)
            if form.is_valid():
                cantidades = _cantidades_carrito(request)
                cantidad_actual = cantidades.get(str(juego.pk), 0)
                cantidad_nueva = (
                    cantidad_actual + form.cleaned_data["cantidad_juegos"]
                )
                maximo = min(5, juego.stock)
                if cantidad_nueva > maximo:
                    form.add_error(
                        "cantidad_juegos",
                        (
                            f"El total de este juego en el pedido no puede "
                            f"superar {maximo} unidades."
                        ),
                    )
                else:
                    cantidades[str(juego.pk)] = cantidad_nueva
                    request.session[CARRITO_SESSION_KEY] = cantidades
                    messages.success(
                        request,
                        f"{juego.nombre} se agregó a tu pedido.",
                    )
                    return redirect("carrito")
    else:
        juego = get_object_or_404(
            Juego,
            pk=pk,
            disponibilidad=True,
            stock__gt=0,
        )
        form = CantidadPedidoForm(juego=juego)

    return render(
        request,
        "juegos/detalle.html",
        {"juego": juego, "pedido_form": form},
    )


def carrito(request):
    return render(
        request,
        "juegos/carrito.html",
        _contexto_carrito(request),
    )


@require_POST
def actualizar_carrito(request, pk):
    cantidades = _cantidades_carrito(request)
    juego_id = str(pk)
    if juego_id not in cantidades:
        messages.warning(request, "Ese juego ya no está en tu pedido.")
        return redirect("carrito")

    juego = Juego.objects.filter(pk=pk).first()
    if juego is None:
        cantidades.pop(juego_id)
        request.session[CARRITO_SESSION_KEY] = cantidades
        messages.warning(request, "Ese juego ya no existe y se quitó del pedido.")
        return redirect("carrito")

    if not juego.disponibilidad or juego.stock == 0:
        messages.error(request, "Ese juego ya no está disponible.")
        return redirect("carrito")

    form = CantidadPedidoForm(request.POST, juego=juego)
    if not form.is_valid():
        messages.error(
            request,
            form.errors["cantidad_juegos"][0],
        )
        return redirect("carrito")

    cantidades[juego_id] = form.cleaned_data["cantidad_juegos"]
    request.session[CARRITO_SESSION_KEY] = cantidades
    messages.success(request, "Se actualizó la cantidad del juego.")
    return redirect("carrito")


@require_POST
def quitar_del_carrito(request, pk):
    cantidades = _cantidades_carrito(request)
    cantidades.pop(str(pk), None)
    request.session[CARRITO_SESSION_KEY] = cantidades
    messages.success(request, "Se quitó el juego de tu pedido.")
    return redirect("carrito")


@require_POST
def confirmar_pedido(request):
    pedido_form = PedidoPublicoForm(request.POST)
    contexto = _contexto_carrito(request, pedido_form)
    items = contexto["carrito_items"]

    if not items:
        pedido_form.add_error(
            None,
            "Agrega al menos un juego antes de confirmar el pedido.",
        )
        return render(request, "juegos/carrito.html", contexto)

    if not pedido_form.is_valid() or not contexto["carrito_valido"]:
        return render(request, "juegos/carrito.html", contexto)

    try:
        with transaction.atomic():
            juego_ids = [item["juego"].pk for item in items]
            juegos_actuales = {
                juego.pk: juego
                for juego in Juego.objects.select_for_update().filter(
                    pk__in=juego_ids
                )
            }

            for item in items:
                juego = juegos_actuales.get(item["juego"].pk)
                if juego is None or not juego.disponibilidad:
                    raise StockActualizadoError(
                        f"{item['juego'].nombre} ya no está disponible."
                    )
                if juego.stock < item["cantidad"]:
                    unidad = "unidad" if juego.stock == 1 else "unidades"
                    raise StockActualizadoError(
                        f"Solo quedan {juego.stock} {unidad} de "
                        f"{juego.nombre}."
                    )

            for item in items:
                juego = item["juego"]
                actualizadas = Juego.objects.filter(
                    pk=juego.pk,
                    disponibilidad=True,
                    stock__gte=item["cantidad"],
                ).update(stock=F("stock") - item["cantidad"])
                if not actualizadas:
                    raise StockActualizadoError(
                        f"El stock de {juego.nombre} cambió. "
                        "Revisa las unidades disponibles."
                    )

            pedido = pedido_form.save()
            for item in items:
                DetallePedido.objects.create(
                    pedido=pedido,
                    juego=item["juego"],
                    cantidad_juegos=item["cantidad"],
                )
    except StockActualizadoError as error:
        messages.error(request, str(error))
        return redirect("carrito")

    request.session.pop(CARRITO_SESSION_KEY, None)
    return redirect("pedido_confirmado", codigo=pedido.codigo)


def pedido_confirmado(request, codigo):
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("detalles__juego"),
        codigo=codigo,
    )
    return render(request, "juegos/pedido_confirmado.html", {"pedido": pedido})
