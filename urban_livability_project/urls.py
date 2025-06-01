from livability import views as livability_views
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('livability.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path("register/", livability_views.register, name="register"),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# Configure Admin Titles
admin.site.site_header = "ULA Yönetim Paneli"
admin.site.site_title = "ULA Yönetim Paneli"
admin.site.index_title = "ULA Yönetim Paneline Hoşgeldiniz!"