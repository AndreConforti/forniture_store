from django.contrib import admin
from django.urls import path, include
from django.conf import settings


urlpatterns = [
    path('', include('apps.showroom.urls')),
    path('admin/', admin.site.urls),
    path('auth/', include('apps.employees.urls')),
    path('customers/', include('apps.customers.urls')),
    path('docs/', include('apps.docs.urls')),
    # path('products', include('apps.products.urls')),
    path('reports/', include('apps.reports.urls')),
    path('suppliers/', include('apps.suppliers.urls')),
]

if settings.DEBUG:
    from django.conf.urls.static import static # Importar apenas se DEBUG for True
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) # Para desenvolvimento
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) # Para desenvolvimento