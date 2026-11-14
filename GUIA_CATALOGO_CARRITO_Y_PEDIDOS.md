# Guía: catálogo, carrito y pedidos

Esta guía resume cómo mostrar los juegos cargados desde Django Admin y describe cómo incorporar un carrito y guardar pedidos. Home y el detalle ya comparten `templates/base.html`; las indicaciones de catálogo sirven como referencia y el flujo de compra sigue siendo trabajo futuro.

## 1. Cómo está organizado ahora

- `juegosmesa/models.py` define `Juego`, `Categoria` y `Pedido`.
- Cada juego puede tener varias categorías; se eligen en Django Admin.
- `juegosmesa/admin.py` registra esos modelos para administrarlos desde `/admin/`.
- `juegosmesa/views.py` consulta los juegos disponibles y ofrece búsqueda por nombre y categoría; también tiene la vista de detalle.
- `templates/index.html` muestra el buscador, las categorías y las tarjetas de juegos.
- `config/settings.py` ya configura `MEDIA_URL` y `MEDIA_ROOT`.
- `config/urls.py` ya sirve archivos de `MEDIA_ROOT` durante `DEBUG` y tiene `/` como ruta de Home.
- `requirements.txt` incluye Pillow, que Django necesita para procesar `ImageField`.

El modelo `Juego` permite asignar varias categorías. Si acabas de actualizar el proyecto, ejecuta `python manage.py migrate` para actualizar la base de datos. Esa migración también corrige las columnas de `Pedido` que no coincidían con el modelo.

El objetivo es una tienda para clientes, no otra pantalla para administrar juegos:

```text
Django Admin ── crear/editar Juego ──> base de datos
                                         │
Home ── consultar juegos disponibles ───┘
  ├── detalle ──> pedido público de un juego ──> Pedido ──> comprobante
  └── agregar al carrito ──> carrito de sesión ──> confirmar compra
                                                    ├── Pedido
                                                    ├── Detalles del pedido
                                                    └── actualizar stock
```

`/admin/` sigue siendo el lugar donde el administrador carga juegos. Home solo presenta el catálogo y los flujos de compra públicos. El pedido desde el detalle corresponde a un juego; el carrito puede reunir varios juegos y necesita los detalles de pedido descritos más adelante.

## 2. Mostrar los juegos en Home

### Paso 2.1: consultar, buscar y filtrar en la vista

En `juegosmesa/views.py`, modifica `Home` para consultar el catálogo y entregar al template tanto los juegos como las categorías que alimentan el filtro. La lógica puede seguir esta estructura (conserva los imports y las otras vistas que ya tienes):

```python
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
```

**Por qué va en la vista:** la vista conecta la base de datos con la página. El template presenta lo que recibe y no debería ser responsable de construir consultas.

- `stock__gte=1` cumple el requisito de no mostrar juegos agotados. Si se usa `stock__gt=0`, el resultado es equivalente para un campo entero.
- `nombre__icontains` busca por coincidencia parcial y no distingue mayúsculas/minúsculas.
- El filtro `categorias__id` encuentra juegos que tienen la categoría seleccionada; `.distinct()` evita repetir un juego si coincide con más de una categoría.
- `prefetch_related("categorias")` carga las categorías asociadas sin hacer una consulta extra por juego.
- Se pasan todas las categorías para llenar el selector, aunque algún resultado no tenga juegos disponibles.

El modelo también tiene `disponibilidad`. El filtro anterior muestra cualquier juego con stock de al menos uno, tal como se pide. Si el administrador debe poder ocultar del catálogo un juego que sí tiene stock, añade también `disponibilidad=True`; en ese caso el stock y el interruptor deben estar activos para que aparezca.

Si la vista no pasa `juegos`, la lista no tendrá elementos que mostrar. Si no pasa `categorias`, el menú de filtro no podrá construirse.

### Paso 2.2: búsqueda, filtro y tarjetas clickeables

`templates/index.html` ya extiende `templates/base.html` y contiene el formulario `GET` de búsqueda y filtro, además de las tarjetas enlazadas al detalle. Los parámetros en la URL permiten compartir o recargar los resultados:

```html
<form method="get" action="{% url 'home' %}">
    <label for="busqueda">Buscar por nombre</label>
    <input
        id="busqueda"
        type="search"
        name="nombre"
        value="{{ nombre_busqueda }}"
    >

    <label for="categoria">Categoría</label>
    <select id="categoria" name="categoria">
        <option value="">Todas las categorías</option>
        {% for categoria in categorias %}
        <option
            value="{{ categoria.pk }}"
            {% if categoria.pk|stringformat:"s" == categoria_seleccionada %}selected{% endif %}
        >
            {{ categoria.nombre }}
        </option>
        {% endfor %}
    </select>

    <button type="submit">Buscar</button>
    <a href="{% url 'home' %}">Limpiar</a>
</form>
```

Luego, en la misma página, muestra los juegos. El enlace de la foto y el del nombre llevan al detalle:

```html
{% load formatos %}

<div class="row">
    {% for juego in juegos %}
    <div class="col-md-4 mb-3">
        <article class="card h-100">
            <a href="{% url 'detalle_juego' juego.pk %}">
                {% if juego.imagen %}
                <img
                    src="{{ juego.imagen.url }}"
                    class="card-img-top"
                    alt="{{ juego.nombre }}"
                >
                {% else %}
                <div class="card-body">Imagen no disponible</div>
                {% endif %}
            </a>

            <div class="card-body">
                <h2 class="card-title">
                    <a href="{% url 'detalle_juego' juego.pk %}">
                        {{ juego.nombre }}
                    </a>
                </h2>
                <p>
                    Categorías:
                    {% for categoria in juego.categorias.all %}
                        {{ categoria.nombre }}{% if not forloop.last %}, {% endif %}
                    {% empty %}
                        Sin categoría
                    {% endfor %}
                </p>
                <p>Precio: ${{ juego.precio|clp }}</p>

            </div>
        </article>
    </div>
    {% empty %}
    <p>No hay juegos disponibles que coincidan con la búsqueda.</p>
    {% endfor %}
</div>
```

La plantilla usa `{% url 'detalle_juego' juego.pk %}`; esa ruta debe existir o Django mostrará `NoReverseMatch` al renderizar el catálogo. Por ahora, las tarjetas no incluyen una acción de carrito. El `{% empty %}` sí es válido y muestra un mensaje si no hay resultados.

#### Formato chileno del precio

Para mostrar pesos chilenos sin centavos, por ejemplo `$22.990`, el proyecto usa el filtro `clp` definido en `juegosmesa/templatetags/formatos.py`. En la plantilla carga `{% load formatos %}` y escribe el símbolo `$` antes del filtro:

```python
{% load formatos %}
Precio: ${{ juego.precio|clp }}
```

El filtro agrupa los miles con punto sin depender del separador regional del sistema; así evita que aparezca un espacio en vez de un punto. Para un comprobante, usa la misma forma: `Total: ${{ pedido.total_pedido|clp }}`. El filtro solo cambia cómo se muestra el número, no el valor guardado.

### Paso 2.3: mostrar una miniatura en la tabla de Django Admin

En `juegosmesa/admin.py`, configura el formulario de juegos para permitir seleccionar varias categorías. `filter_horizontal` muestra dos listas para pasar categorías al juego; no hay un límite de dos categorías. La columna `mostrar_categorias` resume las categorías en la lista.

Inclúyelo como primer elemento de la tupla:

```python
@admin.register(Juego)
class JuegoAdmin(admin.ModelAdmin):
    list_display = ("miniatura", "nombre", "mostrar_categorias", "precio", "stock")
    search_fields = ("nombre", "categorias__nombre")
    list_filter = ("categorias",)
    filter_horizontal = ("categorias",)

    @admin.display(description="Categorías")
    def mostrar_categorias(self, obj):
        return ", ".join(categoria.nombre for categoria in obj.categorias.all())

    @admin.display(description="Imagen")
    def miniatura(self, obj):
        if obj.imagen:
            return format_html(
                '<img src="{}" style="height: 60px; border-radius: 4px;" />',
                obj.imagen.url,
            )
        return "-"
```

La lista del admin solo muestra columnas declaradas en `list_display`; definir los métodos por sí solos no basta. Mantén `format_html` para construir HTML seguro y revisa que el recorrido de archivos de medios descrito en la sección siguiente funcione. Si falta la imagen, la columna mostrará `-`; si el archivo o la configuración de medios están mal, puede aparecer una imagen rota.

### Paso 2.4: crear una página de detalle

El catálogo oculta juegos con stock cero, pero un enlace guardado o una visita directa aún puede llegar al detalle de un juego existente. Para mostrarlo como agotado allí, busca por identificador sin filtrar el stock:

```python
from django.shortcuts import get_object_or_404

def detalle_juego(request, pk):
    juego = get_object_or_404(Juego, pk=pk)
    return render(request, "juegos/detalle.html", {"juego": juego})
```

En `config/urls.py`, define el nombre que usa el enlace del catálogo:

```python
path("juegos/<int:pk>/", views.detalle_juego, name="detalle_juego"),
```

`get_object_or_404` responde con HTTP 404 si el identificador no existe. Por decisión para esta guía, los juegos con stock cero se ocultan del catálogo, pero el detalle de un juego existente muestra “Agotado” en vez de responder 404. Esto reemplaza la indicación anterior de responder 404 también por falta de stock. Si además se debe ocultar un juego cuando `disponibilidad=False`, añade esa condición a la consulta.

Crea `templates/juegos/detalle.html` y muestra los campos del modelo: nombre, categoría, descripción, imagen (si existe), precio, cantidad de jugadores, edad mínima, disponibilidad y stock. Si el stock es cero, presenta “Agotado” y no muestres el formulario de pedido. Si no se registra la ruta, los enlaces producen `NoReverseMatch`.

El 404 debe ser una respuesta HTTP, no solo un mensaje dentro de una página con estado 200. Para personalizarlo visualmente, crea `templates/404.html`. Django muestra la página técnica de depuración cuando `DEBUG=True`; la plantilla 404 personalizada se usa con `DEBUG=False`. No dejes `DEBUG=False` en desarrollo sin configurar `ALLOWED_HOSTS`.

### Paso 2.5: pedidos públicos desde el detalle

Este flujo permite pedir un solo juego desde su página de detalle y no requiere iniciar sesión. No pongas `@login_required` ni `@staff_member_required` en la vista pública. El formulario debe incluir nombre, correo, teléfono y cantidad; agrega `{% csrf_token %}` y muestra los errores junto a los campos.

El modelo `Pedido` actual ya tiene los campos de cliente, el juego, la cantidad y el total, así que sirve para guardar un pedido de un juego. Crea `juegosmesa/forms.py` y define ahí un `ModelForm` que permita editar únicamente los campos del cliente y la cantidad:

```python
from django import forms
from django.core.exceptions import ValidationError

from .models import Pedido

class PedidoPublicoForm(forms.ModelForm):
    class Meta:
        model = Pedido
        fields = (
            "nombre_cliente",
            "correo_cliente",
            "telefono_cliente",
            "cantidad_juegos",
        )
        widgets = {
            "cantidad_juegos": forms.NumberInput(attrs={"min": 1, "max": 5}),
        }

    def clean_cantidad_juegos(self):
        cantidad = self.cleaned_data["cantidad_juegos"]
        if not 1 <= cantidad <= 5:
            raise ValidationError("La cantidad debe estar entre 1 y 5.")
        return cantidad
```

`EmailField` valida el formato del correo. La validación personalizada limita la cantidad en el servidor; los atributos `min="1"` y `max="5"` del HTML ayudan al usuario, pero no reemplazan esa validación. Si el formulario no es válido, vuelve a renderizar el detalle con `form.errors` y no guardes nada.

En la vista de detalle, procesa el formulario con `POST`. Dentro de una transacción, vuelve a consultar el juego y compara el stock actual con la cantidad pedida: el stock pudo cambiar mientras el cliente completaba el formulario. Si no alcanza, agrega un error al campo de cantidad que indique las unidades disponibles y vuelve a mostrar el detalle. Si alcanza, asigna el juego, calcula `total_pedido` en el servidor (`juego.precio * cantidad`), guarda el pedido, descuenta la cantidad del stock y redirige al comprobante. No confíes en precios ni totales enviados por el navegador.

En el template, recorre los campos y sus errores; así los errores de correo y cantidad se ven junto al formulario:

```html
{% if juego.stock > 0 %}
<form method="post">
    {% csrf_token %}
    {% for campo in form %}
        <div>
            {{ campo.label_tag }}
            {{ campo }}
            {% for error in campo.errors %}
                <p class="text-danger">{{ error }}</p>
            {% endfor %}
        </div>
    {% endfor %}
    {{ form.non_field_errors }}
    <button type="submit">Hacer pedido</button>
</form>
{% else %}
<p>Agotado</p>
{% endif %}
```

`EmailField` comprueba el formato sintáctico del correo; no confirma que la dirección exista ni que la persona pueda recibir mensajes allí.

La lógica esencial del control de stock es:

```python
if juego.stock < cantidad:
    form.add_error(
        "cantidad_juegos",
        f"Solo quedan {juego.stock} unidades disponibles.",
    )
else:
    pedido = form.save(commit=False)
    pedido.juegos = juego
    pedido.total_pedido = juego.precio * cantidad
    pedido.save()

    juego.stock -= cantidad
    juego.save(update_fields=["stock"])
```

Coloca esta lógica de guardado y descuento dentro de `transaction.atomic()` y vuelve a cargar el juego dentro de la transacción (por ejemplo, con `select_for_update()` en bases de datos que soportan bloqueos de fila). La transacción hace que los cambios se confirmen o reviertan juntos si ocurre un error. SQLite no aplica bloqueos de fila con `select_for_update()`; para un sistema con compras concurrentes se necesita además una actualización condicional y comprobar cuántas filas fueron actualizadas, o usar una base de datos que soporte los bloqueos requeridos. En cualquier caso, la transacción no reemplaza la validación del stock.

En `juegos/detalle.html`, muestra el formulario solo cuando `juego.stock > 0`; en caso contrario muestra “Agotado”. La vista debe volver a comprobar el stock en el `POST`, porque una página abierta antes de agotarse puede seguir teniendo un formulario visible. Si el pedido excede el stock, el error puede decir “Solo quedan N unidades disponibles” y el pedido no se crea.

### Paso 2.6: comprobante y recarga segura

Después de guardar un pedido, redirige a una vista que solo lo consulta y presenta un comprobante. Para que el comprobante tenga un código difícil de adivinar y la URL pública no exponga un ID secuencial, agrega a `Pedido` un campo de código UUID:

```python
import uuid

class Pedido(models.Model):
    codigo = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )
```

Integra `codigo` en la clase `Pedido` existente; no declares una segunda clase con el mismo nombre. Es un cambio de modelo: crea y revisa la migración, luego ejecuta `migrate`. Si ya hay pedidos en la base de datos, no asumas que una migración directa puede asignar automáticamente un UUID distinto a cada fila. Hazlo por etapas: agrega primero el campo permitiendo `NULL`, crea una migración de datos que asigne un UUID distinto a cada pedido existente, y luego cambia el campo a obligatorio con `default=uuid.uuid4` y `unique=True`. Si no hay pedidos que conservar en una base local de práctica, se puede simplificar el proceso, pero no borres datos sin confirmarlo. El UUID funciona como identificador público del comprobante; quien tenga el enlace podrá verlo, así que no incluyas datos personales innecesarios.

Agrega una ruta y vista de solo lectura:

```python
path(
    "pedidos/<uuid:codigo>/",
    views.comprobante,
    name="comprobante",
)
```

La vista busca el pedido por `codigo` y renderiza `comprobante.html`; si ese código no existe, responde 404. Su responsabilidad es consultar, no crear ni modificar pedidos:

```python
def comprobante(request, codigo):
    pedido = get_object_or_404(
        Pedido.objects.select_related("juegos"),
        codigo=codigo,
    )
    return render(request, "comprobante.html", {"pedido": pedido})
```

En el template muestra código, juego, nombre del cliente, cantidad, total con `{{ pedido.total_pedido|clp }}` y fecha/hora, por ejemplo `{{ pedido.fecha_hora_pedido|date:"d/m/Y H:i" }}`. Carga `{% load formatos %}` al principio de la plantilla para usar `clp`.

El flujo después de un `POST` exitoso debe ser **guardar y redirigir** (`redirect("comprobante", codigo=pedido.codigo)`). El navegador entonces muestra el comprobante mediante una petición `GET`. Recargar esa página solo vuelve a leer el pedido guardado: no ejecuta el formulario de compra ni descuenta stock otra vez. Si se renderiza directamente el comprobante como respuesta al `POST`, el navegador puede volver a enviar el formulario al recargar y crear pedidos duplicados.

El `UUID` protege frente a enumerar fácilmente comprobantes, pero no equivale a autenticación: trata el enlace como privado y evita exponer correo/teléfono si no es necesario. Si el requerimiento exige evitar duplicados incluso ante doble clic o reintentos del `POST`, agrega además una clave de idempotencia por formulario; la redirección/GET cubre específicamente la recarga del comprobante.

`Pedido.juegos` actualmente usa `on_delete=models.CASCADE`. Si se elimina un juego, Django podría borrar también sus pedidos y comprobantes. Para preservar el historial, evalúa cambiar esa relación a `models.PROTECT`; eso requiere migración y el admin ya no permitirá borrar un juego asociado a pedidos.

Este pedido desde detalle es de un juego por compra, que coincide con el `Pedido` actual. Si el requisito del carrito es confirmar varios juegos en un solo pedido, usa el diseño `Pedido` + `DetallePedido` explicado más adelante y guarda/descuenta cada línea dentro de la misma transacción.

### Paso 2.7: compartir el menú con una plantilla base

Actualmente `index.html` contiene su propio documento HTML y Bootstrap. Para que las páginas públicas tengan el mismo menú y estructura, crea `templates/base.html` con el `<html>`, `<head>`, Bootstrap, menú, pie de página y un bloque para el contenido:

```html
<!doctype html>
<html lang="es-cl">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{% block titulo %}Tienda de Juegos de Mesa{% endblock %}</title>
    <!-- Carga aquí Bootstrap y los estilos comunes -->
</head>
<body>
    <nav>
        <a href="{% url 'home' %}">Inicio</a>
        <a href="{% url 'ver_carrito' %}">Carrito</a>
    </nav>

    <main>
        {% block contenido %}{% endblock %}
    </main>

    <footer>Tienda de Juegos de Mesa</footer>
</body>
</html>
```

Convierte `index.html`, `juegos/detalle.html`, el carrito, la confirmación y `comprobante.html` en páginas hijas. Cada una debe empezar con `{% extends "base.html" %}` y poner su contenido dentro de `{% block contenido %}...{% endblock %}`. La etiqueta `extends` debe ir antes de cualquier otro tag de template. Así el menú se cambia una vez y todas las páginas públicas lo heredan; si una página no extiende `base.html`, puede quedar sin menú o con una copia desactualizada.

Esta plantilla base es para las páginas de la tienda. `/admin/` usa las plantillas y navegación propias de Django Admin; no se recomienda reemplazarlas para compartir el menú público.

Los nombres usados en los enlaces del menú también tienen que existir en `config/urls.py`. Por ejemplo, `ver_carrito` no existe en el estado actual: agrega esa ruta cuando implementes la vista del carrito, o deja temporalmente el enlace fuera del menú. Si se hereda una base con un `{% url %}` inexistente, puede fallar el renderizado de todas las páginas que la extiendan.

La página personalizada `templates/404.html` también puede extender `base.html` para conservar el menú cuando se muestre un 404. Recuerda que Django no usa esa página personalizada mientras `DEBUG=True`.

## 3. Verificar el recorrido de las imágenes

La imagen no se guarda dentro del HTML: `ImageField` guarda una referencia en la base de datos y el archivo en el almacenamiento de medios.

1. El administrador sube la imagen al editar un juego.
2. Django la guarda bajo `MEDIA_ROOT`, usando la carpeta `juegos/` definida en `upload_to`.
3. `juego.imagen.url` produce una dirección bajo `MEDIA_URL`.
4. En desarrollo, la ruta de medios de `config/urls.py` sirve esos archivos cuando `DEBUG` está activado.

Si una imagen no aparece, revisa que el juego tenga un archivo cargado, que exista el archivo dentro de `media/juegos/`, y que `MEDIA_URL`, `MEDIA_ROOT` y la ruta para medios coincidan. `MEDIA_ROOT` no es lo mismo que `STATICFILES_DIRS`: las imágenes subidas por usuarios son medios. En producción, el servidor web o el almacenamiento configurado debe servir los medios; `static(..., document_root=...)` es para desarrollo.

## 4. Crear el carrito

Un carrito no es lo mismo que un pedido. El carrito es temporal y se puede modificar; un pedido es el registro persistente de una compra confirmada.

Para un proyecto pequeño, una opción sencilla es guardar en la sesión solo los identificadores y cantidades:

```text
request.session["carrito"] = {
    "12": 2,
    "19": 1,
}
```

Esto significa dos unidades del juego 12 y una del juego 19. Al mostrar o confirmar el carrito, vuelve a consultar los juegos en la base de datos y calcula los precios en el servidor; nunca aceptes como válido un precio o total enviado en un formulario desde el navegador.

### Pasos del carrito

1. Crea una vista para agregar un juego. Recibe el ID desde la URL, busca el `Juego` en la base de datos y comprueba que esté disponible y tenga stock.
2. Solo acepta `POST` para modificar el carrito. El formulario del catálogo debe incluir `{% csrf_token %}`.
3. Valida la cantidad: debe ser un entero positivo y no exceder el stock.
4. Guarda o incrementa esa cantidad en `request.session["carrito"]`.
5. Crea una vista de carrito que vuelva a cargar cada juego y muestre nombre, imagen, precio actual, cantidad y subtotal.
6. Agrega acciones para cambiar cantidades y quitar juegos. Valida de nuevo el stock en esas acciones.
7. Define rutas con nombres estables para ver, actualizar y quitar elementos del carrito.

La sesión está habilitada en la configuración actual: están instaladas las aplicaciones y el middleware de sesiones. Si se quitan, `request.session` deja de estar disponible. Un carrito de sesión normalmente pertenece a ese navegador/sesión; no se sincroniza entre dispositivos. Para carritos persistentes asociados a cuentas, se necesita un modelo de carrito y una relación con el usuario.

Si el ID no corresponde a un juego, la vista debe responder de forma controlada (por ejemplo, 404). No debe confiar en que un botón oculto o desactivado garantiza que el producto siga disponible: el servidor debe validar cada acción.

## 5. Representar un pedido con varios juegos

El modelo `Pedido` actual tiene una sola relación `juegos = ForeignKey(Juego)` y una sola `cantidad_juegos`. Por eso representa **un juego por pedido**. No representa correctamente un carrito con varios tipos de juego dentro de un mismo pedido.

Hay dos opciones:

### Opción A: conservar un juego por pedido

Puedes crear un `Pedido` por cada juego del carrito. Es lo menos invasivo para el esquema actual, pero repite nombre, correo y teléfono del cliente en varias filas y no hay un registro único que agrupe toda la compra. Conviene solo si los requisitos del curso aceptan explícitamente ese significado.

### Opción B: pedido y líneas de detalle (recomendado para un carrito)

Un pedido contiene los datos del cliente y varias líneas. Cada línea relaciona un pedido con un juego y guarda cantidad y precio unitario al momento de comprar. Conceptualmente:

```python
class Pedido(models.Model):
    nombre_cliente = models.CharField(max_length=100)
    correo_cliente = models.EmailField()
    telefono_cliente = models.CharField(max_length=20)
    fecha_hora_pedido = models.DateTimeField(auto_now_add=True)
    total_pedido = models.DecimalField(max_digits=10, decimal_places=2)

class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        related_name="detalles",
        on_delete=models.CASCADE,
    )
    juego = models.ForeignKey(Juego, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
```

Este es un ejemplo de diseño; antes de implementarlo, confirma si el profesor requiere conservar el modelo actual. `PROTECT` impide borrar un juego que aparece en pedidos, lo que ayuda a conservar el historial. El precio unitario guardado evita que editar el precio del catálogo cambie el total de una compra anterior.

Cambiar el modelo afecta la base de datos. El flujo normal es:

1. Añadir el modelo nuevo y planear qué hacer con `Pedido.juegos` y `Pedido.cantidad_juegos`.
2. Ejecutar `python manage.py makemigrations` y revisar la migración generada.
3. Si ya hay pedidos que conservar, copiar cada pedido antiguo a un `DetallePedido` mediante una migración de datos antes de quitar los campos viejos.
4. Ejecutar `python manage.py migrate`.
5. Actualizar las vistas y cualquier template o configuración del admin que lea los campos antiguos.

No elimines los campos viejos ni borres la base de datos sin decidir primero si hay datos que preservar. Al quitar un campo, las consultas o templates que todavía lo usen fallarán.

## 6. Confirmar el pedido y descontar stock

La vista de confirmación debe recibir los datos del cliente mediante un formulario validado. Al confirmar:

1. Vuelve a cargar los juegos y precios actuales desde la base de datos.
2. Comprueba disponibilidad y stock para cada línea. El stock pudo cambiar desde que el cliente agregó el juego.
3. Calcula subtotales y total en el servidor; nunca aceptes el total enviado por el navegador.
4. Crea el `Pedido` y sus detalles.
5. Descuenta stock solo después de comprobar que alcanza.
6. Vacía el carrito solo si el pedido se guardó correctamente.

Conviene envolver el guardado del pedido, los detalles y el descuento de stock en `transaction.atomic()`. Así, si falla una parte, la base de datos no queda con un pedido sin detalles o con stock descontado a medias. Si se permiten compras simultáneas, hay que considerar bloqueos/actualizaciones atómicas para evitar vender más unidades que las existentes.

Si no se vuelve a validar el stock al confirmar, dos clientes podrían comprar la última unidad. Si el total se acepta desde el navegador, alguien podría modificarlo. Si se vacía el carrito antes de guardar el pedido, un error puede hacer que el cliente pierda su selección.

## 7. Qué partes afectan a cuáles

| Parte | Responsabilidad | Si falta o no coincide |
|---|---|---|
| `Juego` en `models.py` | Datos del catálogo e imagen | El admin no puede guardar o la vista no encuentra los campos esperados. |
| `JuegoAdmin.list_display` | Decide qué columnas se ven en la lista de juegos del admin | Aunque exista `miniatura`, no aparece si no se agrega a `list_display`. |
| `Home` en `views.py` | Consulta juegos, búsqueda, categoría y entrega contexto | Sin contexto faltan catálogo y opciones de filtro; una consulta mal validada puede fallar. |
| Bucle de `index.html` | Presenta tarjetas y enlaces al detalle | Los datos existen, pero no se presentan; una URL nombrada inexistente causa `NoReverseMatch`. |
| Configuración y URL de medios | Entrega los archivos cargados | La tarjeta o miniatura del admin aparece sin imagen o con enlace roto. |
| Formato de precio | Presenta CLP agrupando miles | Sin `humanize`/formato, se muestran decimales o separadores que no corresponden al formato esperado. |
| Vista y ruta de detalle | Carga un juego existente y muestra su estado | Si busca por stock, no puede mostrar “Agotado”; sin validar stock al enviar, puede aceptar pedidos imposibles. |
| `base.html` y bloques | Comparte menú y estructura entre páginas públicas | Si una página no extiende la base, queda sin menú o duplica una versión desactualizada. |
| Formulario público de pedido | Valida cliente, correo y cantidad de 1 a 5 | Sin validación de servidor se pueden guardar datos inválidos; sin mostrar errores, el usuario no entiende por qué no se guardó. |
| Transacción y comprobante | Guarda pedido, descuenta stock y muestra el resultado | Sin transacción los datos pueden quedar inconsistentes; sin redirección después del POST, recargar puede duplicar el pedido. |
| Código UUID del pedido | Identifica el comprobante público sin ID secuencial | Si se agrega sin una migración de datos para pedidos existentes, la migración puede fallar o asignar códigos no únicos. |
| Rutas del carrito | Conectan formularios con vistas | Un nombre de URL incorrecto produce `NoReverseMatch`; una ruta ausente da 404. |
| Sesión del carrito | Conserva selección entre peticiones | El carrito se pierde o `request.session` no funciona. |
| Modelos del pedido | Guardan compra y productos | Sin detalle de pedido no se puede representar un carrito con varios juegos correctamente. |
| Validación de servidor | Protege precios, cantidades y stock | Se pueden registrar cantidades inválidas, totales manipulados o sobreventa. |
| Migraciones | Mantienen modelos y base de datos sincronizados | Errores como `no such column` o tablas inexistentes al consultar. |

## 8. Cómo probarlo por etapas

1. Crea en `/admin/` una categoría y un juego con precio, stock mayor que cero y una imagen.
2. Verifica que la imagen aparece en la columna de la tabla de juegos del admin.
3. Implementa Home y comprueba que muestra categoría, imagen, nombre y precio como CLP.
4. Crea otro juego con stock cero y confirma que no aparece en Home, pero que su detalle directo muestra “Agotado” y no presenta el formulario. Una URL de un ID inexistente debe responder 404.
5. Prueba buscar por una parte del nombre, filtrar por categoría y combinar ambos filtros. Comprueba también el mensaje para resultados vacíos.
6. Prueba el pedido público sin iniciar sesión: correo inválido, cantidad cero, cantidad mayor que cinco y cantidad mayor que stock deben mostrar errores y no crear pedidos.
7. Completa un pedido válido. Comprueba que se guarda una vez, baja el stock por la cantidad y el comprobante muestra código, juego, cliente, cantidad, total CLP y fecha/hora.
8. Recarga el comprobante y confirma que no se crea otro pedido ni se descuenta stock otra vez.
9. Recorre Home, detalle, carrito, confirmación y comprobante; verifica que todas las páginas públicas conservan el mismo menú.
10. Prueba también un juego sin imagen y comprueba que se muestra el texto alternativo previsto, no una imagen rota.
11. Implementa agregar, ver, actualizar y quitar del carrito; comprueba cantidades inválidas y stock insuficiente.
12. Ejecuta `python manage.py check`. Si cambiaste modelos, ejecuta además `makemigrations` y `migrate`.

La ruta `/gestion/` y el template `templates/admin/tablas.html` corresponden a una tabla personalizada de consulta administrativa; no son necesarios para mostrar el catálogo a clientes. Puedes dejarlos mientras desarrollas y decidir luego si eliminarlos, comprobando antes que ninguna URL, enlace o prueba los use. No hace falta duplicar la administración de juegos: Django Admin ya cubre esa tarea.
