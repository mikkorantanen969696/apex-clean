from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from project.config.settings import Settings
from project.database.models import Order


@dataclass(slots=True)
class InvoiceGenerator:
    settings: Settings
    out_dir: str = "storage/invoices"

    def generate(self, order: Order) -> str:
        os.makedirs(self.out_dir, exist_ok=True)
        filename = f"invoice_order_{order.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        path = os.path.join(self.out_dir, filename)

        c = canvas.Canvas(path, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 16)
        c.drawString(20 * mm, height - 25 * mm, self.settings.company_name)

        c.setFont("Helvetica", 10)
        if self.settings.company_inn:
            c.drawString(20 * mm, height - 32 * mm, f"ИНН: {self.settings.company_inn}")
        if self.settings.company_phone:
            c.drawString(20 * mm, height - 38 * mm, f"Телефон: {self.settings.company_phone}")

        c.setFont("Helvetica-Bold", 14)
        c.drawString(20 * mm, height - 55 * mm, f"Счет на оплату №{order.id}")

        c.setFont("Helvetica", 11)
        c.drawString(20 * mm, height - 70 * mm, f"Услуга: {order.cleaning_type}")
        c.drawString(20 * mm, height - 78 * mm, f"Адрес: {order.address}")
        c.drawString(20 * mm, height - 86 * mm, f"Дата/время: {order.scheduled_time:%Y-%m-%d %H:%M}")
        c.drawString(20 * mm, height - 94 * mm, f"Описание: {order.description[:120]}")

        c.setFont("Helvetica-Bold", 12)
        c.drawString(20 * mm, height - 110 * mm, f"Итого: {order.price} ₽")

        if self.settings.company_pay_url:
            pay_url = f"{self.settings.company_pay_url}?order_id={order.id}&amount={order.price}"
            qr_img = qrcode.make(pay_url)
            qr_path = os.path.join(self.out_dir, f"qr_{order.id}.png")
            qr_img.save(qr_path)
            c.setFont("Helvetica", 10)
            c.drawString(20 * mm, height - 125 * mm, "Оплата по QR:")
            c.drawImage(qr_path, 20 * mm, height - 175 * mm, width=45 * mm, height=45 * mm)
            c.setFont("Helvetica", 8)
            c.drawString(20 * mm, height - 180 * mm, pay_url[:90])

        c.showPage()
        c.save()
        return path
