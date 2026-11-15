from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
import juegosmesa.views as views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.Home, name='home'),
    path("juegos/<int:pk>/", views.detalle_juego, name="detalle_juego"),
    path("carrito/", views.carrito, name="carrito"),
    path(
        "carrito/<int:pk>/actualizar/",
        views.actualizar_carrito,
        name="actualizar_carrito",
    ),
    path(
        "carrito/<int:pk>/quitar/",
        views.quitar_del_carrito,
        name="quitar_del_carrito",
    ),
    path(
        "carrito/confirmar/",
        views.confirmar_pedido,
        name="confirmar_pedido",
    ),
    path(
        "pedidos/<uuid:codigo>/confirmado/",
        views.pedido_confirmado,
        name="pedido_confirmado",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += staticfiles_urlpatterns()