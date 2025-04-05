from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('livability.urls')),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)



# Configure Admin Titles
admin.site.site_header = "ULA Yönetim Paneli"
admin.site.site_title = "ULA Yönetim Paneli"
admin.site.index_title = "ULA Yönetim Paneline Hoşgeldiniz!"