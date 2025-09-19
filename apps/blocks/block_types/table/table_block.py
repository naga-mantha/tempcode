from apps.blocks.base import BaseBlock
from apps.blocks.models.block import Block
from apps.blocks.models.block_column_config import BlockColumnConfig
from apps.blocks.models.block_filter_config import BlockFilterConfig
from apps.blocks.models.config_templates import ColumnConfigTemplate, FilterConfigTemplate
from apps.workflow.permissions import (
    get_readable_fields_state,
    get_editable_fields_state,
    can_read_field_state,
    can_write_field_state,
    filter_viewable_queryset_state,
)
from apps.permissions.checks import (
    can_read_field as can_read_field_generic,
    can_write_field as can_write_field_generic,
    filter_viewable_queryset as filter_viewable_queryset_generic,
)
from apps.blocks.helpers.field_rules import get_field_display_rules
from apps.blocks.helpers.column_config import get_user_column_config
from django.db import models
from django.core.exceptions import FieldDoesNotExist
from django.contrib.admin.utils import label_for_field
import json
from .filter_utils import FilterResolutionMixin
import uuid


class TableBlock(BaseBlock, FilterResolutionMixin):
    template_name = "blocks/table/table_block.html"
    supported_features = ["filters", "column_config"]

    def __init__(self, block_name):
        self.block_name = block_name
        self._block = None
        # Cache context per-request to avoid leaking data across requests
        # while still preventing duplicate work within a single request.
        self._context_cache = {}

    def render(self, request, instance_id=None):
        """Clear cached context and render the block."""
        # Ensure previous request data is discarded before rendering.
        self._context_cache.clear()
        return super().render(request, instance_id=instance_id)

    @property
    def block(self):
        if self._block is None:
            try:
                self._block = Block.objects.get(code=self.block_name)
            except Block.DoesNotExist:
                raise Exception(f"Block '{self.block_name}' not registered in admin.")
        return self._block

    def get_model(self):
        raise NotImplementedError("You must override get_model()")

    def get_queryset(self, user, filters, active_column_config):
        """Default queryset builder for table blocks.

        - Starts from get_base_queryset(user)
        - Infers forward relations from selected fields and applies select_related
        - Applies registered filters via apply_filter_registry

        Subclasses can override get_base_queryset() for base filtering, or
        override this method entirely if the defaults are not sufficient.
        """
        # Late import to avoid circulars
        from apps.blocks.services.filtering import apply_filter_registry

        selected_fields = active_column_config.fields if active_column_config else []
        select_paths, prefetch_paths = self._infer_related_paths(selected_fields, max_depth=5)
        qs = self.get_base_queryset(user)
        if select_paths:
            qs = qs.select_related(*sorted(select_paths))
        if prefetch_paths:
            qs = qs.prefetch_related(*sorted(prefetch_paths))
        return apply_filter_registry(self.block_name, qs, filters, user)

    def get_base_queryset(self, user):
        """Base queryset hook; override in subclasses for default filters."""
        return self.get_model().objects.all()

    def _infer_related_paths(self, selected_fields, max_depth=5):
        """Infer select_related and prefetch_related paths from selected fields.

        - Forward FK/OneToOne -> select_related
        - Reverse OneToOne -> select_related
        - Forward/Reverse M2M -> prefetch_related
        - Reverse ForeignKey (ManyToOne) -> prefetch_related
        Stops at max_depth relations.
        """
        model = self.get_model()
        select_paths = set()
        prefetch_paths = set()

        for f in selected_fields or []:
            if "__" not in f:
                continue
            parts = f.split("__")
            current_model = model
            path_elems = []
            for i, part in enumerate(parts):
                if i >= max_depth:
                    break
                try:
                    field = current_model._meta.get_field(part)
                except FieldDoesNotExist:
                    break
                is_relation = getattr(field, "is_relation", False)
                is_m2m = getattr(field, "many_to_many", False)
                is_auto = getattr(field, "auto_created", False)
                if not is_relation:
                    break
                path_elems.append(part)
                path = "__".join(path_elems)
                # Reverse relations have auto_created=True
                if is_m2m:
                    prefetch_paths.add(path)
                elif is_auto:
                    # Reverse: OneToOneRel -> select_related; ManyToOneRel -> prefetch
                    rel_class_name = type(field).__name__.lower()
                    if "one" in rel_class_name and "toone" in rel_class_name:
                        select_paths.add(path)
                    else:
                        prefetch_paths.add(path)
                else:
                    # Forward: OneToOne/FK -> select_related
                    select_paths.add(path)
                # Descend for further traversal where possible
                try:
                    current_model = field.remote_field.model
                except Exception:
                    break
        return select_paths, prefetch_paths

    def get_column_defs(self, user, column_config=None):
        """Default column defs based on active column config.

        Returns a list of {"field": <path>, "title": <label>} entries,
        where the label mirrors the Manage Columns UI's "Verbose Name"
        for the selected field (i.e., the leaf field's verbose_name),
        instead of a fully expanded relation path.
        """
        fields = column_config.fields if column_config else get_user_column_config(user, self.block)
        model = self.get_model()
        # Build a map of all manageable fields to their labels to match the
        # Manage Columns page (Verbose Name)
        try:
            from apps.blocks.helpers.column_config import get_model_fields_for_column_config
            try:
                max_depth = int(getattr(self, "get_column_config_max_depth")())
            except Exception:
                max_depth = 10
            all_meta = get_model_fields_for_column_config(model, user, max_depth=max_depth) or []
            label_map = {m.get("name"): m.get("label") for m in all_meta if m.get("name")}
        except Exception:
            label_map = {}

        defs = []
        for field in fields or []:
            # Prefer the Manage Columns label; fall back to Django's label_for_field
            label = label_map.get(field)
            if not label:
                try:
                    label = label_for_field(field, model, return_attr=False)
                except Exception:
                    # As a last resort, humanize the field path
                    try:
                        label = field.replace("__", " ").replace("_", " ").title()
                    except Exception:
                        continue
            defs.append({"field": field, "title": label})
        return defs

    def get_tabulator_default_options(self, user):
        """Base defaults for Tabulator options across all TableBlocks.

        Subclasses should generally not override this; instead, override
        :meth:`get_tabulator_options_overrides` to supply per-app/per-block
        changes that are merged on top of these defaults.
        """
        return {
            "layout": "fitDataFill",
            "pagination": "local",
            "paginationSize": 10,
            "paginationSizeSelector": [10, 20, 50, 100],
        }

    def get_tabulator_options_overrides(self, user):
        """Override point for final apps to tweak Tabulator options.

        Return a dict of options that will be shallow-merged on top of
        :meth:`get_tabulator_default_options`.
        """
        return {}

    def get_tabulator_options(self, user):
        """Resolved Tabulator options = defaults + overrides.

        If a subclass overrides this method directly, it takes full control of
        the options. Prefer overriding :meth:`get_tabulator_options_overrides`
        instead to preserve base defaults automatically.
        """
        defaults = self.get_tabulator_default_options(user) or {}
        overrides = self.get_tabulator_options_overrides(user) or {}
        merged = {**defaults, **overrides}
        return merged

    # ----- column config depth -----------------------------------------------
    def get_column_config_max_depth(self) -> int:
        """Maximum ForeignKey traversal depth for Manage Columns.

        Blocks can override to customize how deep related fields expand.
        Default is 10.
        """
        return 10

    def get_xlsx_download_default_options(self, request, instance_id=None):
        """Base defaults for XLSX download across all TableBlocks."""
        return {
            "filename": f"{self.block_name}.xlsx",
            "sheetName": f"{self.block_name}",
            "header": {"fillColor": "#004085", "fontColor": "#FFFFFF", "bold": True},
            # Intentionally omit default "options" to avoid complex deep merges
        }

    def get_xlsx_download_options_overrides(self, request, instance_id=None):
        """Override point for final apps to tweak XLSX download options."""
        return {}

    def get_xlsx_download_options(self, request, instance_id=None):
        """Resolved XLSX options = defaults + overrides (with shallow nested merge).

        Prefer overriding :meth:`get_xlsx_download_options_overrides` to keep
        base defaults. If you override this method, you take full control.
        """
        defaults = self.get_xlsx_download_default_options(request, instance_id) or {}
        overrides = self.get_xlsx_download_options_overrides(request, instance_id) or {}
        merged = {**defaults, **overrides}
        # Merge nested common dicts if present
        for key in ("options", "header"):
            if isinstance(defaults.get(key), dict) or isinstance(overrides.get(key), dict):
                base_sub = defaults.get(key) or {}
                over_sub = overrides.get(key) or {}
                merged[key] = {**base_sub, **over_sub}
        return merged

    def get_pdf_download_default_options(self, request, instance_id=None):
        """Base defaults for PDF download across all TableBlocks."""
        return {
            "filename": f"{self.block_name}.pdf",
            "orientation": "portrait",  # or "landscape"
            "title": getattr(self.block, "name", self.block_name),
            # Simple header styling mapped to autoTable headStyles
            "header": {"fillColor": "#003366", "fontColor": "#FFFFFF", "bold": True},
            "options": {
                "jsPDF": {"unit": "pt", "format": "a4", "compress": True},
            }
        }

    def get_pdf_download_options_overrides(self, request, instance_id=None):
        """Override point for final apps to tweak PDF download options."""
        return {}

    def get_pdf_download_options(self, request, instance_id=None):
        """Resolved PDF options = defaults + overrides (with shallow nested merge)."""
        defaults = self.get_pdf_download_default_options(request, instance_id) or {}
        overrides = self.get_pdf_download_options_overrides(request, instance_id) or {}
        merged = {**defaults, **overrides}
        for key in ("options", "header"):
            if isinstance(defaults.get(key), dict) or isinstance(overrides.get(key), dict):
                base_sub = defaults.get(key) or {}
                over_sub = overrides.get(key) or {}
                merged[key] = {**base_sub, **over_sub}
        return merged

    def get_column_config_queryset(self, user):
        return BlockColumnConfig.objects.filter(user=user, block=self.block)

    def get_filter_config_queryset(self, user):
        return BlockFilterConfig.objects.filter(user=user, block=self.block)

    def _build_context(self, request, instance_id):
        user = request.user
        (
            column_configs,
            filter_configs,
            active_column_config,
            active_filter_config,
            selected_fields,
        ) = self._select_configs(request, instance_id)
        filter_schema, selected_filter_values = self._resolve_filters(
            request, active_filter_config, instance_id
        )
        queryset, sample_obj = self._build_queryset(
            user, selected_filter_values, active_column_config
        )
        fields, columns = self._compute_fields(
            user, selected_fields, active_column_config, sample_obj
        )
        # Provide user to row serializer for per-instance field checks
        self._current_user = user
        try:
            data = self._serialize_rows(queryset, selected_fields)
        finally:
            if hasattr(self, "_current_user"):
                delattr(self, "_current_user")
        # Ensure we have an instance_id (for standalone renders)
        instance_id = instance_id or uuid.uuid4().hex[:8]
        return {
            "block_name": self.block_name,
            "instance_id": instance_id,
            "block_title": getattr(self.block, "name", self.block_name),
            "block": self.block,
            "fields": fields,
            "tabulator_options": self.get_tabulator_options(user),
            "xlsx_download": json.dumps(self.get_xlsx_download_options(request, instance_id) or {}),
            "pdf_download": json.dumps(self.get_pdf_download_options(request, instance_id) or {}),
            "column_configs": column_configs,
            "filter_configs": filter_configs,
            "active_column_config_id": active_column_config.id if active_column_config else None,
            "active_filter_config_id": active_filter_config.id if active_filter_config else None,
            "columns": columns,
            "data": data,
            "filter_schema": filter_schema,
            "selected_filter_values": selected_filter_values,
        }

    def _get_context(self, request, instance_id):
        # If no explicit instance_id is provided (standalone block render),
        # try to detect a previously-used instance namespace from the querystring
        # so that view/filter selections persist across reloads.
        effective_instance_id = instance_id or self._detect_instance_id_from_query(request)
        cache_key = (id(request), effective_instance_id)
        if cache_key not in self._context_cache:
            # Replace cache for this (request, instance) pair.
            self._context_cache[cache_key] = self._build_context(request, effective_instance_id)
        return self._context_cache[cache_key]

    def _detect_instance_id_from_query(self, request):
        """Best-effort extraction of instance_id from namespaced GET params.

        Looks for keys like:
        - "<block>__<instance>__column_config_id"
        - "<block>__<instance>__filter_config_id"
        - "<block>__<instance>__filters.<name>"
        Returns the first detected instance id, or None if not found.
        """
        try:
            keys = request.GET.keys()
        except Exception:
            return None
        prefix = f"{self.block_name}__"
        for key in keys:
            if not key.startswith(prefix):
                continue
            rest = key[len(prefix):]
            if "__" not in rest:
                continue
            candidate, tail = rest.split("__", 1)
            if (
                tail.startswith("column_config_id")
                or tail.startswith("filter_config_id")
                or tail.startswith("filters.")
            ):
                return candidate
        return None

    def get_config(self, request, instance_id=None):
        context = dict(self._get_context(request, instance_id))
        context.pop("data", None)
        return context

    def get_data(self, request, instance_id=None):
        context = self._get_context(request, instance_id)
        return {"data": context.get("data")}

    def _select_configs(self, request, instance_id=None):
        user = request.user
        # Namespaced params by block and (optional) instance
        ns = f"{self.block_name}__{instance_id}__" if instance_id else f"{self.block_name}__"
        column_config_id = (
            request.GET.get(f"{ns}column_config_id")
            or (request.GET.get(f"{self.block_name}__column_config_id") if instance_id else None)
            or request.GET.get("column_config_id")
        )
        filter_config_id = (
            request.GET.get(f"{ns}filter_config_id")
            or (request.GET.get(f"{self.block_name}__filter_config_id") if instance_id else None)
            or request.GET.get("filter_config_id")
        )
        column_configs = self.get_column_config_queryset(user)
        # Lazy seed from admin-defined template when user has no column configs
        if not column_configs.exists():
            try:
                tpl = (
                    ColumnConfigTemplate.objects.filter(block=self.block, is_default=True).first()
                    or ColumnConfigTemplate.objects.filter(block=self.block).first()
                )
                if tpl:
                    BlockColumnConfig.objects.create(
                        block=self.block,
                        user=user,
                        name=tpl.name or "Default",
                        fields=list(tpl.fields or []),
                        is_default=True,
                    )
                    column_configs = self.get_column_config_queryset(user)
            except Exception:
                pass
        filter_configs = self.get_filter_config_queryset(user)
        # Lazy seed filter config from admin-defined template if user has none
        # or only has an auto-generated 'None' placeholder with empty values.
        try:
            tpl = (
                FilterConfigTemplate.objects.filter(block=self.block, is_default=True).first()
                or FilterConfigTemplate.objects.filter(block=self.block).first()
            )
        except Exception:
            tpl = None
        if not filter_configs.exists() and tpl:
            try:
                BlockFilterConfig.objects.create(
                    block=self.block,
                    user=user,
                    name=tpl.name or "Default",
                    values=dict(tpl.values or {}),
                    is_default=True,
                )
                filter_configs = self.get_filter_config_queryset(user)
            except Exception:
                pass
        elif tpl:
            # Detect placeholder-only case
            placeholders = list(filter_configs.filter(name="None", values={}))
            if placeholders and filter_configs.count() == 1:
                try:
                    BlockFilterConfig.objects.create(
                        block=self.block,
                        user=user,
                        name=tpl.name or "Default",
                        values=dict(tpl.values or {}),
                        is_default=True,
                    )
                    # demote placeholder from default if needed
                    for ph in placeholders:
                        if ph.is_default:
                            ph.is_default = False
                            ph.save(update_fields=["is_default"])
                    filter_configs = self.get_filter_config_queryset(user)
                except Exception:
                    pass
        active_column_config = None
        if column_config_id:
            try:
                active_column_config = column_configs.get(pk=column_config_id)
            except BlockColumnConfig.DoesNotExist:
                pass
        if not active_column_config:
            active_column_config = column_configs.filter(is_default=True).first()
        active_filter_config = None
        if filter_config_id:
            try:
                active_filter_config = filter_configs.get(pk=filter_config_id)
            except BlockFilterConfig.DoesNotExist:
                pass
        if not active_filter_config:
            active_filter_config = filter_configs.filter(is_default=True).first()
        selected_fields = active_column_config.fields if active_column_config else []
        return (
            column_configs,
            filter_configs,
            active_column_config,
            active_filter_config,
            selected_fields,
        )

    def _resolve_filters(self, request, active_filter_config, instance_id=None):
        user = request.user
        try:
            raw_schema = self.get_filter_schema(request)
        except TypeError:
            raw_schema = self.get_filter_schema(user)
        filter_schema = self._resolve_filter_schema(raw_schema, user)
        base_values = active_filter_config.values if active_filter_config else {}
        # Use namespaced filter params to avoid collisions across blocks and instances
        ns_prefix = (
            f"{self.block_name}__{instance_id}__filters."
            if instance_id
            else f"{self.block_name}__filters."
        )
        selected_filter_values = self._collect_filters(
            request.GET, filter_schema, base=base_values, prefix=ns_prefix, allow_flat=False
        )
        return filter_schema, selected_filter_values

    def _build_queryset(self, user, filter_values, active_column_config):
        queryset = self.get_queryset(user, filter_values, active_column_config)
        # Filter out instances the user cannot view (base permissions and workflow state)
        queryset = filter_viewable_queryset_generic(user, queryset)
        queryset = filter_viewable_queryset_state(user, queryset)
        sample_obj = queryset.first() if queryset else None
        return queryset, sample_obj

    def _compute_fields(self, user, selected_fields, active_column_config, sample_obj):
        model = self.get_model()
        model_list = [model]
        for field in model._meta.fields:
            if isinstance(field, models.ForeignKey):
                model_list.append(field.remote_field.model)
        readable_fields = []
        editable_fields = []
        for m in model_list:
            readable_fields.extend(get_readable_fields_state(user, m, sample_obj))
            editable_fields.extend(get_editable_fields_state(user, m, sample_obj))
        model_label = f"{model._meta.app_label}.{model.__name__}"
        display_rules = {
            r.field_name: r for r in get_field_display_rules(model_label)
        }
        visible_fields = [
            f
            for f in selected_fields
            if not (display_rules.get(f) and display_rules[f].is_excluded)
        ]
        column_defs = self.get_column_defs(user, active_column_config)
        column_label_map = {col["field"]: col["title"] for col in column_defs}
        fields = []
        for f in visible_fields:
            fields.append(
                {
                    "name": f,
                    "label": column_label_map.get(f, f.replace("_", " ").title()),
                    "mandatory": display_rules[f].is_mandatory if f in display_rules else False,
                    "editable": f in editable_fields,
                }
            )
        from django.contrib.admin.utils import label_for_field
        editable_map = {f["name"]: f.get("editable", False) for f in fields}
        columns = []
        for defn in column_defs:
            field_name = defn.get("field")
            col = {
                # Use the same label we computed in get_column_defs so titles
                # match the Manage Columns "Verbose Name" exactly.
                "title": defn.get("title"),
                "field": field_name,
            }
            # Define editor for direct editable model fields; per-row editability enforced in JS using __editable map
            if "__" not in field_name:
                try:
                    model_field = self.get_model()._meta.get_field(field_name)
                    if getattr(model_field, "editable", True):
                        col["editor"] = "input"
                except Exception:
                    pass
            columns.append(col)
        return fields, columns

    def _serialize_rows(self, queryset, selected_fields):
        """Serialize queryset rows applying field-level read masking.

        For each selected field, if the user lacks read permission (base or
        workflow-state), the value is masked as an empty string.
        """

        # We need the request user; derive from the queryset's _hints when possible.
        # Since we don't have access to request here, cache the last seen user
        # via context. This method is only called from _build_context which has the request.
        data = []
        # Attach user via closure by reading from the most recent context cache entry.
        # Fallback to no masking if user cannot be determined (unlikely in normal flow).
        user = None
        # Attempt to infer from first object's _state (not available); instead,
        # rely on the fact that _serialize_rows is only called within _build_context
        # where self._context_cache entry was just built. We'll pass user via a hidden attr.
        user = getattr(self, "_current_user", None)

        for obj in queryset:
            row = {}
            # Always include primary key for inline edits
            try:
                row["id"] = obj.pk
            except Exception:
                pass
            editable_flags = {}
            for field in selected_fields:
                # Traverse multi-hop relations safely to the leaf parent
                leaf_parent = obj
                leaf_parent_model = type(obj)
                attr_name = field
                if "__" in field:
                    parts = field.split("__")
                    # walk all but the last segment to reach the leaf parent
                    for part in parts[:-1]:
                        if leaf_parent is None:
                            break
                        try:
                            leaf_parent = getattr(leaf_parent, part)
                        except Exception:
                            leaf_parent = None
                            break
                    leaf_parent_model = type(leaf_parent) if isinstance(leaf_parent, models.Model) else None
                    attr_name = parts[-1]

                # Compute value from the leaf parent
                try:
                    value = getattr(leaf_parent or obj, attr_name if leaf_parent is not None else field)
                except Exception:
                    value = None

                # Mask if unreadable by base or state permission
                if user and isinstance(leaf_parent, models.Model):
                    if not can_read_field_generic(user, leaf_parent_model, attr_name, leaf_parent) or not can_read_field_state(
                        user, leaf_parent_model, attr_name, leaf_parent
                    ):
                        row[field] = "***"
                        # still compute edit flags
                        editable_flags[field] = False
                        continue

                if value is None:
                    row[field] = ""
                elif isinstance(value, models.Model):
                    row[field] = str(value)
                else:
                    try:
                        json.dumps(value)
                        row[field] = value
                    except TypeError:
                        row[field] = str(value)

                # Per-row edit flags
                if user and isinstance(leaf_parent, models.Model):
                    can_write = can_write_field_generic(user, leaf_parent_model, attr_name, leaf_parent) and can_write_field_state(
                        user, leaf_parent_model, attr_name, leaf_parent
                    )
                    editable_flags[field] = bool(can_write)
                else:
                    editable_flags[field] = False
            data.append(row)
            if editable_flags:
                row["__editable"] = editable_flags
        return json.dumps(data)
