from django.core.management.base import BaseCommand
from apps.common.models import *
from apps.production.views.scheduling import *
from datetime import datetime, time, timedelta, date

class Command(BaseCommand):
    help = 'Create Calendar Days'

    def handle(self, *args, **kwargs):
        pass

