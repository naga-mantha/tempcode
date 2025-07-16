from django.core.management.base import BaseCommand
from apps.common.models import *
from datetime import date, datetime

class Command(BaseCommand):
    help = 'Create Production Order Operations'

    def handle(self, *args, **kwargs):
        objects = []

        data = [{"production_order": "1000", "operation": "10", "task": "001", "machine": "m_001", "workcenter": "610", "remaining_time": 12, "required_start": datetime(2025, 7, 1, 8, 0, 0), "required_end": datetime(2025, 7, 9, 10, 0, 0), "priority": 999, "op_po": None, "op_po_line": None, "op_po_seq": None},
                {"production_order": "1000", "operation": "20", "task": "002", "machine": "m_001", "workcenter": "615", "remaining_time": 5, "required_start": datetime(2025, 7, 5, 8, 0, 0), "required_end": datetime(2025, 7, 10, 10, 0, 0), "priority": 999, "op_po": 2000, "op_po_line": 10, "op_po_seq": 0},
                {"production_order": "1000", "operation": "30", "task": "003", "machine": "m_002", "workcenter": "610", "remaining_time": 6, "required_start": datetime(2025, 7, 10, 8, 0, 0), "required_end": datetime(2025, 7, 15, 10, 0, 0), "priority": 999, "op_po": None, "op_po_line": None, "op_po_seq": None},
                # {"production_order": "1000", "operation": "40", "task": "004", "machine": "m_004", "workcenter": "610", "remaining_time": 5, "required_start": datetime(2025, 7, 15, 10, 0, 0), "required_end": datetime(2025, 7, 21, 10, 0, 0), "priority": 999, "op_po": None, "op_po_line": None, "op_po_seq": None},
                # {"production_order": "1000", "operation": "50", "task": "005", "machine": "m_005", "workcenter": "610", "remaining_time": 1, "required_start": datetime(2025, 7, 22, 10, 0, 0), "required_end": datetime(2025, 7, 25, 10, 0, 0), "priority": 999, "op_po": None, "op_po_line": None, "op_po_seq": None},
                ]

        for i in range(0, len(data)):
            obj = ProductionOrderOperation()

            obj.production_order = ProductionOrder.objects.get(production_order=data[i]["production_order"])
            obj.operation = data[i]["operation"]
            obj.task = Task.objects.get(code=data[i]["task"])
            obj.machine = Machine.objects.get(code=data[i]["machine"])
            obj.workcenter = WorkCenter.objects.get(code=data[i]["workcenter"])
            obj.remaining_time = data[i]["remaining_time"]
            obj.required_start = data[i]["required_start"]
            obj.required_end = data[i]["required_end"]
            obj.priority = data[i]["priority"]
            obj.op_po = None

            if data[i]["op_po"]:
                obj.op_po = PurchaseOrderLine.objects.get(order=PurchaseOrder.objects.get(order=data[i]["op_po"]), line=data[i]["op_po_line"], sequence=data[i]["op_po_seq"])

            objects.append(obj)

        ProductionOrderOperation.objects.bulk_create(objects,
                                      update_conflicts=True,
                                      unique_fields=['production_order', 'operation'],
                                      update_fields=["task", "machine", "workcenter", "remaining_time", "required_start", "required_end", "priority", "op_po" ])