"""
StockUp Pulse - Purchase Order Generation & Strict Approval Gate
AMD Hackathon ACT III (Reinvent Commerce)

Enforces:
1. No purchase order exists until the owner explicitly approves.
   Raises PlanNotApprovedError (maps to HTTP 409).
2. Generates deterministic PO numbers: PO-2026-001 (Makro), PO-2026-002 (Shoprite), PO-2026-003 (Usave).
3. Produces JSON and formatted supplier WhatsApp message templates.
"""

from typing import Dict, List, Any, Optional
import threading
from datetime import datetime, timezone
from stockup_pulse.trace.tracker import trace_collector, TraceEvent

class PlanNotApprovedError(Exception):
    """Raised when an attempt is made to generate or retrieve purchase orders before approval."""
    pass

class PurchaseOrderManager:
    def __init__(self):
        self._orders: Dict[str, Dict[str, Any]] = {}
        self._counter = 1
        self._counter_lock = threading.Lock()

    def create_orders_from_plan(
        self,
        plan: Dict[str, Any],
        approved: bool,
        store_name: str = "Sunnyside Spaza"
    ) -> List[Dict[str, Any]]:
        """
        Generates Purchase Orders ONLY IF plan has been explicitly approved.
        Otherwise raises PlanNotApprovedError (HTTP 409 in API).
        """
        if not approved or not plan.get("approved", False):
            trace_collector.record(TraceEvent(
                event_type="approval_check_failed",
                status="error",
                details={"error": "Attempted PO generation without explicit owner approval gate (HTTP 409)"}
            ))
            raise PlanNotApprovedError("Explicit approval required. Plan must be approved before purchase orders can be created.")

        supplier_breakdown = plan.get("supplier_breakdown", {})
        created_orders = []

        for supplier_name in sorted(supplier_breakdown.keys()):
            sup_data = supplier_breakdown[supplier_name]
            with self._counter_lock:
                sequence = self._counter
                self._counter += 1
            po_id = f"PO-{datetime.now(timezone.utc).year}-{sequence:06d}"

            po = {
                "order_number": po_id,
                "supplier": supplier_name,
                "store_name": store_name,
                "total_items": sup_data["items_count"],
                "total_spend": round(sup_data["total_spend"], 2),
                "status": "Ready",
                "items": sup_data["items"],
                "whatsapp_message": self.format_whatsapp_message(po_id, supplier_name, store_name, sup_data)
            }

            self._orders[po_id] = po
            created_orders.append(po)

        trace_collector.record(TraceEvent(
            event_type="approval",
            status="success",
            details={
                "action": "purchase_orders_created",
                "order_count": len(created_orders),
                "total_spend": plan.get("total_spend", 0.0)
            }
        ))

        return created_orders

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        return self._orders.get(order_id)

    def list_orders(self) -> List[Dict[str, Any]]:
        return list(self._orders.values())

    def format_whatsapp_message(
        self,
        po_id: str,
        supplier_name: str,
        store_name: str,
        sup_data: Dict[str, Any]
    ) -> str:
        """Formatted WhatsApp message ready for the spaza owner to send directly to wholesale sales reps."""
        items_summary = "\n".join([
            f"  • {item['product']}: {item['qty']} units @ R {item['unit_price']:.2f} (R {item['total_cost']:.2f})"
            for item in sup_data["items"]
        ])
        return (
            f"Hi {supplier_name},\n"
            f"Please process this restocking order for *{store_name}*.\n\n"
            f"*Order Reference:* {po_id}\n"
            f"*Items:*\n{items_summary}\n\n"
            f"*Total Order Value:* R {sup_data['total_spend']:,.2f}\n"
            f"Please confirm delivery availability. Thank you!"
        )

order_manager = PurchaseOrderManager()
