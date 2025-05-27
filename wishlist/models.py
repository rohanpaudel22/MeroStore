from django.db import models
from accounts.models import Account
from store.models import Product , Variation

# Create your models here.
class Wishlist(models.Model):
    user = models.ForeignKey(Account, on_delete=models.CASCADE)
    
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    
    variations = models.ManyToManyField(Variation , blank=True)
    added_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.product_name} - {self.user.username}"
