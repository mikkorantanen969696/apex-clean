from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from project.database.models import Order, OrderStatus, Transaction, TransactionStatus, TransactionType, User
from project.services.audit import AuditService


@dataclass(slots=True)
class FinanceService:
    session: AsyncSession

    async def record_income(self, order_id: int, manager: User, amount: float) -> Transaction:
        order = await self._require_manager_order(order_id, manager)
        tx = Transaction(order_id=order.id, type=TransactionType.INCOME, amount=amount, status=TransactionStatus.CONFIRMED)
        self.session.add(tx)
        await self.session.flush()
        await AuditService(self.session).log(
            actor_user_id=manager.id,
            action="income_recorded",
            entity_type="transaction",
            entity_id=str(tx.id),
            metadata={"order_id": order.id, "amount": float(amount)},
        )
        return tx

    async def record_payout(self, order_id: int, manager: User, amount: float) -> Transaction:
        order = await self._require_manager_order(order_id, manager)
        tx = Transaction(order_id=order.id, type=TransactionType.PAYOUT, amount=amount, status=TransactionStatus.CONFIRMED)
        self.session.add(tx)
        order.status = OrderStatus.PAID_TO_CLEANER
        await self.session.flush()
        await AuditService(self.session).log(
            actor_user_id=manager.id,
            action="payout_recorded",
            entity_type="transaction",
            entity_id=str(tx.id),
            metadata={"order_id": order.id, "amount": float(amount)},
        )
        return tx

    async def _require_manager_order(self, order_id: int, manager: User) -> Order:
        res = await self.session.execute(select(Order).where(Order.id == order_id, Order.manager_id == manager.id))
        order = res.scalar_one_or_none()
        if order is None:
            raise PermissionError("Order not found or not owned")
        return order
