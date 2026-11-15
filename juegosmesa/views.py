from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render

from .forms import PedidoPublicoForm
from .models import Categoria, DetallePedido, Juego, Pedido

def Home(request):
    nombre = request.GET.get("nombre", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()

    juegos = Juego.objects.all().prefetch_related("categorias")

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
            )
            form = PedidoPublicoForm(request.POST, juego=juego)
            if form.is_valid():
                cantidad = form.cleaned_data["cantidad_juegos"]
                stock_actualizado = Juego.objects.filter(
                    pk=juego.pk,
                    stock__gte=cantidad,
                ).update(stock=F("stock") - cantidad)

                if stock_actualizado:
                    pedido = form.save()
                    DetallePedido.objects.create(
                        pedido=pedido,
                        juego=juego,
                        cantidad_juegos=cantidad,
                    )
                    return redirect(
                        "pedido_confirmado",
                        codigo=pedido.codigo,
                    )

                juego.refresh_from_db()
                form.add_error(
                    "cantidad_juegos",
                    f"Solo hay {juego.stock} unidades disponibles.",
                )
    else:
        juego = get_object_or_404(Juego, pk=pk)
        form = PedidoPublicoForm(juego=juego)

    return render(
        request,
        "juegos/detalle.html",
        {"juego": juego, "pedido_form": form},
    )


def pedido_confirmado(request, codigo):
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related("detalles__juego"),
        codigo=codigo,
    )
    return render(request, "juegos/pedido_confirmado.html", {"pedido": pedido})