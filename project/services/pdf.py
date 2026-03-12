from __future__ import annotations

from dataclasses import dataclass

from project.config.settings import Settings
from project.database.models import Order
from project.pdf.invoice import InvoiceGenerator


@dataclass(slots=True)
class PdfService:
    settings: Settings

    def generate_invoice(self, order: Order) -> str:
        return InvoiceGenerator(self.settings).generate(order)
