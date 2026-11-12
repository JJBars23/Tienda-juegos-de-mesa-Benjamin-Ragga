from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render

from .models import Categoria, Juego, Pedido

def Home(request):
    nombre = request.GET.get("nombre", "").strip()
    categoria_id = request.GET.get("categoria", "").strip()

    juegos = Juego.objects.filter(
        stock__gte=1,
    ).select_related("categoria")

    if nombre:
        juegos = juegos.filter(nombre__icontains=nombre)

    if categoria_id.isdecimal():
        juegos = juegos.filter(categoria_id=int(categoria_id))

    contexto = {
        "juegos": juegos,
        "categorias": Categoria.objects.all().order_by("nombre"),
        "nombre_busqueda": nombre,
        "categoria_seleccionada": categoria_id,
    }
    return render(request, "index.html", contexto)