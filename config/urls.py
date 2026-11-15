from django.contrib import admin
from django.urls import path
from django.conf.urls.static import static
from django.conf import settings
import juegosmesa.views as views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.Home, name='home'),
    path("juegos/<int:pk>/", views.detalle_juego, name="detalle_juego"),
    path(
        "pedidos/<uuid:codigo>/confirmado/",
        views.pedido_confirmado,
        name="pedido_confirmado",
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)