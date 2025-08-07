from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.blocks.models.block_column_config import BlockColumnConfig
# from apps.blocks.helpers.field_rules import merge_column_config_with_rules
from apps.blocks.models import FieldDisplayRule  # Adjust path

@receiver(post_save, sender=FieldDisplayRule)
def update_column_configs_on_rule_change(sender, instance, **kwargs):
    pass
    # model = instance.model  # Assuming this is a ContentType or model reference
    # model_class = model.model_class()
    #
    # all_configs = BlockColumnConfig.objects.filter(block__model=model_class._meta.label)
    #
    # for config in all_configs:
    #     old_values = config.values
    #     new_values = merge_column_config_with_rules(old_values, model_class, config.user)
    #
    #     if new_values != old_values:
    #         config.values = new_values
    #         config.save(update_fields=["values"])


