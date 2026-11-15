from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import CantidadPedidoForm, PedidoPublicoForm
from .models import Categoria, Juego, Pedido


CARRITO_SESSION_KEY = "carrito_pedido"


class StockActualizadoError(Exception):
    pass


def _carrito_actual(request):
    carrito = request.session.get(CARRITO_SESSION_KEY)
    if not isinstance(carrito, dict):
        if carrito is None:
            return None
        request.session.pop(CARRITO_SESSION_KEY, None)
        messages.warning(
            request,
            "El carrito anterior no era válido y se ha vaciado.",
        )
        return None

    juego_id = carrito.get("juego_id")
    cantidad = carrito.get("cantidad")
    if (
        str(juego_id).isdecimal()
        and isinstance(cantidad, int)
        and not isinstance(cantidad, bool)
        and cantidad > 0
    ):
        carrito_actual = {"juego_id": str(juego_id), "cantidad": cantidad}
        if carrito_actual != carrito:
            request.session[CARRITO_SESSION_KEY] = carrito_actual
        return carrito_actual

    if len(carrito) == 1:
        juego_id, cantidad = next(iter(carrito.items()))
        if (
            str(juego_id).isdecimal()
            and isinstance(cantidad, int)
            and not isinstance(cantidad, bool)
            and cantidad > 0
        ):
            carrito_actual = {"juego_id": str(juego_id), "cantidad": cantidad}
            request.session[CARRITO_SESSION_KEY] = carrito_actual
            return carrito_actual

    request.session.pop(CARRITO_SESSION_KEY, None)
    messages.warning(
        request,
        "El carrito anterior no era válido y se ha vaciado.",
    )
    return None


def _contexto_carrito(request, pedido_form=None):
    carrito = _carrito_actual(request)
    contexto = {
        "carrito_juego": None,
        "carrito_cantidad": 0,
        "subtotal_carrito": 0,
        "carrito_error": None,
        "puede_actualizar": False,
        "cantidad_form": None,
        "carrito_valido": False,
        "pedido_form": pedido_form or PedidoPublicoForm(),
    }
    if carrito is None:
        return contexto

    cantidad = carrito["cantidad"]
    juego = Juego.objects.filter(pk=int(carrito["juego_id"])).first()
    if juego is None:
        request.session.pop(CARRITO_SESSION_KEY, None)
        messages.warning(request, "El juego ya no existe y se quitó del pedido.")
        return contexto

    error = None
    if not juego.disponibilidad:
        error = "Este juego ya no está disponible para la venta."
    elif juego.stock == 0:
        error = "Este juego está agotado."
    elif cantidad > 5:
        error = "La cantidad máxima es 5 unidades."
    elif cantidad > juego.stock:
        unidad = "unidad" if juego.stock == 1 else "unidades"
        disponible = "disponible" if juego.stock == 1 else "disponibles"
        error = f"Solo hay {juego.stock} {unidad} {disponible}."

    contexto.update({
        "carrito_juego": juego,
        "carrito_cantidad": cantidad,
        "subtotal_carrito": juego.precio * cantidad,
        "carrito_error": error,
        "puede_actualizar": juego.disponibilidad and juego.stock > 0,
        "cantidad_form": CantidadPedidoForm(
            initial={"cantidad_juegos": cantidad},
            juego=juego,
        ),
        "carrito_valido": error is None,
    })
    return contexto


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
                carrito = _carrito_actual(request)
                if carrito and carrito["juego_id"] != str(juego.pk):
                    messages.error(
                        request,
                        (
                            "Solo puedes incluir un juego por pedido. "
                            "Quita el juego actual antes de elegir otro."
                        ),
                    )
                    return redirect("carrito")
                cantidad_actual = carrito["cantidad"] if carrito else 0
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
                    request.session[CARRITO_SESSION_KEY] = {
                        "juego_id": str(juego.pk),
                        "cantidad": cantidad_nueva,
                    }
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
    carrito = _carrito_actual(request)
    juego_id = str(pk)
    if carrito is None or carrito["juego_id"] != juego_id:
        messages.warning(request, "Ese juego ya no está en tu pedido.")
        return redirect("carrito")

    juego = Juego.objects.filter(pk=pk).first()
    if juego is None:
        request.session.pop(CARRITO_SESSION_KEY, None)
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

    request.session[CARRITO_SESSION_KEY] = {
        "juego_id": juego_id,
        "cantidad": form.cleaned_data["cantidad_juegos"],
    }
    messages.success(request, "Se actualizó la cantidad del juego.")
    return redirect("carrito")


@require_POST
def quitar_del_carrito(request, pk):
    carrito = _carrito_actual(request)
    if carrito and carrito["juego_id"] == str(pk):
        request.session.pop(CARRITO_SESSION_KEY, None)
    messages.success(request, "Se quitó el juego de tu pedido.")
    return redirect("carrito")


@require_POST
def confirmar_pedido(request):
    pedido_form = PedidoPublicoForm(request.POST)
    contexto = _contexto_carrito(request, pedido_form)
    juego = contexto["carrito_juego"]
    cantidad = contexto["carrito_cantidad"]

    if juego is None:
        pedido_form.add_error(
            None,
            "Agrega un juego antes de confirmar el pedido.",
        )
        return render(request, "juegos/carrito.html", contexto)

    if not pedido_form.is_valid() or not contexto["carrito_valido"]:
        return render(request, "juegos/carrito.html", contexto)

    try:
        with transaction.atomic():
            juego_actual = Juego.objects.select_for_update().filter(
                pk=juego.pk,
                disponibilidad=True,
            ).first()
            if juego_actual is None:
                raise StockActualizadoError(
                    f"{juego.nombre} ya no está disponible."
                )
            if juego_actual.stock < cantidad:
                unidad = "unidad" if juego_actual.stock == 1 else "unidades"
                raise StockActualizadoError(
                    f"Solo quedan {juego_actual.stock} {unidad} de "
                    f"{juego_actual.nombre}."
                )

            actualizadas = Juego.objects.filter(
                pk=juego_actual.pk,
                disponibilidad=True,
                stock__gte=cantidad,
            ).update(stock=F("stock") - cantidad)
            if not actualizadas:
                raise StockActualizadoError(
                    f"El stock de {juego_actual.nombre} cambió. "
                    "Revisa las unidades disponibles."
                )

            pedido = pedido_form.save(commit=False)
            pedido.juego = juego_actual
            pedido.cantidad_juegos = cantidad
            pedido.total_pedido = juego_actual.precio * cantidad
            pedido.save()
    except StockActualizadoError as error:
        messages.error(request, str(error))
        return redirect("carrito")

    request.session.pop(CARRITO_SESSION_KEY, None)
    return redirect("pedido_confirmado", codigo=pedido.codigo)


def pedido_confirmado(request, codigo):
    pedido = get_object_or_404(
        Pedido.objects.select_related("juego"),
        codigo=codigo,
    )
    return render(request, "juegos/pedido_confirmado.html", {"pedido": pedido})
