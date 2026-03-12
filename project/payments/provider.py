from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PaymentLinkProvider:
    base_url: str

    def build_link(self, order_id: int, amount: float) -> str:
        if not self.base_url:
            return ""
        sep = "&" if "?" in self.base_url else "?"
        return f"{self.base_url}{sep}order_id={order_id}&amount={amount}"
