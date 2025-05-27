from django.contrib import admin
from django.urls import include, path
# from merostore.settings import MEDIA_ROOT
from .import views
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    
    path("merostore/", admin.site.urls),
    path('' , views.home , name="home"),
    path('store/' , include('store.urls')),
    path('cart/' , include('carts.urls')),
    path('accounts/' , include('accounts.urls')),
    path('orders/' , include('orders.urls')),
    path('wishlist/', include('wishlist.urls')),
] + static(settings.MEDIA_URL , document_root = settings.MEDIA_ROOT)

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)