from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Wishlist
from store.models import Product , Variation  # adjust if Product is elsewhere

# Add product to wishlist
@login_required(login_url='login')
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)

    if request.user.is_authenticated:
        # Check if it already exists
        wishlist_item, created = Wishlist.objects.get_or_create(user=request.user, product=product)
        
        # Add variations if provided
        product_variations = []
        for key in request.POST:
            value = request.POST[key]
            try:
                variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                product_variations.append(variation)
            except Variation.DoesNotExist:
                continue

        if product_variations:
            wishlist_item.save()
            wishlist_item.variations.set(product_variations)

        return redirect('wishlist')
    else:
        return redirect('login')


@login_required(login_url='login')
def remove_from_wishlist(request, product_id):
    Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
    return redirect('wishlist')

# View wishlist page
@login_required(login_url='login')
def wishlist(request):
    wishlist_items = Wishlist.objects.filter(user=request.user)
    return render(request, 'store/wishlist.html', {'wishlist_items': wishlist_items})
