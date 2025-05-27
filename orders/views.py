import json
from django.shortcuts import get_object_or_404, render , redirect
from django.http import HttpResponse
from carts.models import CartItem
from .forms import OrderForm
from .models import Order, OrderProduct , Payment
import datetime
import stripe
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from django.core.mail import EmailMessage
from django.template.loader import render_to_string

stripe.api_key = settings.STRIPE_SECRET_KEY

# Create your views here.

def payments(request):
  
  
  # move the cart items to order Product table
  
  return render(request , 'orders/payments.html')


def place_order(request, total=0, quantity=0):
    current_user = request.user
    
    # If the cart count is less than or equal to 0, then redirect to shop
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')
    
    grand_total = 0
    tax = 0

    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity
        
    tax = (2 * total) / 100  # Tax rate can be changed if needed
    grand_total = total + tax
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Store all the billing information inside the order table
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']
            
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')
            data.save()

            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")
            
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            # Create a Stripe Checkout session
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[
                    {
                        'price_data': {
                            'currency': 'npr',  # Use appropriate currency
                            'product_data': {
                                'name': f"Order #{order_number}",
                            },
                            'unit_amount': int(grand_total * 100),  # Amount in paise (100 paise = 1 NPR)
                        },
                        'quantity': 1,
                    },
                ],
                mode='payment',
                success_url=f"{settings.DOMAIN_URL}/orders/payment-success/?session_id={{CHECKOUT_SESSION_ID}}",
                cancel_url=f"{settings.DOMAIN_URL}/orders/payment-cancel/",
            )
            
            # Save the session ID in the order (optional for tracking)
            data.stripe_session_id = checkout_session.id
            data.save()

            # Pass the session ID to the template for Stripe to use
            context = {
                'order': data,
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
                'stripe_public_key': settings.STRIPE_PUBLIC_KEY,  # Ensure the public key is in settings
                'session_id': checkout_session.id,
            }
            return render(request, 'orders/payments.html', context)

    else:
        return redirect('checkout')
  
  
@csrf_exempt
def create_checkout_session(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        order_id = data.get('order_id')

        if not order_id:
            return JsonResponse({'error': 'Order ID is required'}, status=400)

        try:
            order = Order.objects.get(id=order_id, user=request.user, is_ordered=False)
        except Order.DoesNotExist:
            return JsonResponse({'error': 'Order not found'}, status=404)

        YOUR_DOMAIN = "http://127.0.0.1:8000"

        # Use order total (grand_total = order_total + tax)
        grand_total = order.order_total + order.tax
        grand_total_paisa = int(grand_total * 100)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[
                {
                    'price_data': {
                        'currency': 'npr',
                        'product_data': {
                            'name': f"MeroStore Order #{order.order_number}",
                        },
                        'unit_amount': grand_total_paisa,
                    },
                    'quantity': 1,
                },
            ],
            mode='payment',
            success_url=YOUR_DOMAIN + '/orders/payment-success/?session_id={CHECKOUT_SESSION_ID}&order_id=' + str(order_id),
            cancel_url=YOUR_DOMAIN + '/orders/payment-cancel/',
        )

        # Create Payment record
        Payment.objects.create(
            user=request.user,
            payment_id=checkout_session.id,
            payment_method='Stripe',
            amount_paid=str(grand_total),
            status='Pending',
        )

        return JsonResponse({'id': checkout_session.id})
    else:
        return JsonResponse({'error': 'Invalid request'}, status=400)


def payment_success(request):
    session_id = request.GET.get('session_id')
    order_id = request.GET.get('order_id')

    if not session_id or not order_id:
        return render(request, 'orders/payment_cancel.html')

    try:
        session = stripe.checkout.Session.retrieve(session_id)
        payment = get_object_or_404(Payment, payment_id=session.id)

        # Try to get the order for the current user and not yet ordered
        try:
            order = Order.objects.get(id=order_id, user=request.user, is_ordered=False)
        except Order.DoesNotExist:
            return render(request, 'orders/payment_cancel.html')

        # Update payment status
        payment.status = 'completed'
        payment.save()

        # Mark order as ordered
        order.payment = payment
        order.is_ordered = True
        order.save()

        # Move Cart Items into OrderProduct
        cart_items = CartItem.objects.filter(user=request.user)

        for item in cart_items:
            order_product = OrderProduct()
            order_product.order = order
            order_product.payment = payment
            order_product.user = request.user
            order_product.product = item.product
            order_product.quantity = item.quantity
            order_product.product_price = item.product.price
            order_product.ordered = True

            # Check for variations and assign color and size properly
            variations = item.variations.all()
            if variations.exists():
                for variation in variations:
                    if variation.variation_category == 'color':
                        order_product.color = variation.variation_value
                    elif variation.variation_category == 'size':
                        order_product.size = variation.variation_value
                # Just assign one variation instance to variation field (for ForeignKey)
                order_product.variation = variations.first()
            else:
                order_product.variation = None
                order_product.color = ''
                order_product.size = ''

            order_product.save()
            
          
            # Decrease product stock
            product = item.product
            product.stock -= item.quantity
            product.save()

        # After moving to OrderProduct, clear the user's cart
        cart_items.delete()
        
        mail_subject = "Thank you for your order!"
        message = render_to_string('orders/order_received_email.html' , {
          
          'user' : request.user,
          'order' : order,
        })
        to_email = request.user.email
        send_email = EmailMessage(mail_subject , message , to=[to_email])
        send_email.send()
        
        

        return render(request, 'orders/payment_success.html', {'payment': payment, 'order': order})

    except stripe.error.InvalidRequestError:
        return render(request, 'orders/payment_cancel.html')



def payment_cancel(request):
    return render(request, 'orders/payment_cancel.html')
