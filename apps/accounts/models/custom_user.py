from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    # Override inherited labels
    first_name = models.CharField("First Name", max_length=150, blank=True)
    last_name = models.CharField("Last Name", max_length=150, blank=True)

    # Extra fields
    phone_number = models.CharField(max_length=20, blank=True)
    employee_code = models.CharField(max_length=5, blank=True, verbose_name="Employee Code")

    # If you want to override something like email→unique, you could do:
    # email = models.EmailField(unique=True)
