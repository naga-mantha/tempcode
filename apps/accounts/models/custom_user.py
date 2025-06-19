from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Example: add an extra field
    phone_number = models.CharField(max_length=20, blank=True)

    # If you want to override something like email→unique, you could do:
    # email = models.EmailField(unique=True)
