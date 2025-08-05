# apps/blocks/models/block_column_config.py
from django.db import models
from apps.accounts.models.custom_user import CustomUser
from apps.blocks.models import Block

class BlockColumnConfig(models.Model):
    block = models.ForeignKey(Block, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    fields = models.JSONField(default=list)
    is_default = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.pk:
            if not BlockColumnConfig.objects.filter(block=self.block, user=self.user).exists():
                self.is_default = True
        elif self.is_default:
            BlockColumnConfig.objects.filter(block=self.block, user=self.user).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        configs = BlockColumnConfig.objects.filter(block=self.block, user=self.user)
        if configs.count() <= 1:
            raise Exception("At least one configuration must exist.")
        was_default = self.is_default
        super().delete(*args, **kwargs)
        if was_default:
            new_default = configs.exclude(pk=self.pk).order_by("pk").first()
            if new_default:
                new_default.is_default = True
                new_default.save()
