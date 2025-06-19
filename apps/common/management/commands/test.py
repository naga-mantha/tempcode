from django.core.management.base import BaseCommand
from django.core.management import call_command
from apps.frms.models import NewEmployee
from django_comments_xtd.models import XtdComment

class Command(BaseCommand):
    help = 'Test'

    def handle(self, *args, **kwargs):
        qs = XtdComment.objects.select_related('user', 'content_type').all()
        for c in qs:
            self.stdout.write(f"[{c.id}] {getattr(c.user, 'username', 'Anonymous')}"
                              f" on {c.content_type.app_label}.{c.content_type.model}"
                              f"#{c.object_pk} at {c.submit_date}")
            self.stdout.write(c.comment)
            self.stdout.write("-" * 50)