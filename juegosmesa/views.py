from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.shortcuts import get_object_or_404


from .models import Categoria, Juego, Pedido

def Home(request):
    nombre = request.GET.get("nombre", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()

    juegos = Juego.objects.filter(
        stock__gte=1,
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
    juego = get_object_or_404(Juego, pk=pk)
    return render(request, "juegos/detalle.html", {"juego": juego})