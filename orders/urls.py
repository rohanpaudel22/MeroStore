from django.urls import path
from . import views

urlpatterns = [
    
    path('place_order/' , views.place_order , name="place_order"),
    
    path('payments/' , views.payments , name="payments" ),
    
    path('create-checkout-session/', views.create_checkout_session, name='create-checkout-session'),
    path('payment-success/', views.payment_success, name='payment-success'),
    path('payment-cancel/', views.payment_cancel, name='payment-cancel'),
]
