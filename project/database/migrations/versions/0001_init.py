"""init

Revision ID: 0001_init
Revises: 
Create Date: 2026-03-12

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tg_id", sa.BigInteger(), nullable=True),
        sa.Column("username", sa.String(length=64), nullable=True),
        sa.Column("full_name", sa.String(length=120), nullable=False),
        sa.Column("role", sa.Enum("ADMIN", "MANAGER", "CLEANER", name="user_role"), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tg_id"),
    )

    op.create_table(
        "city_topics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("supergroup_id", sa.BigInteger(), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("supergroup_id", "thread_id", name="uq_city_topics_thread"),
    )

    op.create_table(
        "cleaner_profiles",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("payout_details", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("rating", sa.Numeric(precision=3, scale=2), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "cleaner_cities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cleaner_id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["cleaner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cleaner_id", "city_id", name="uq_cleaner_cities"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("city_id", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(length=255), nullable=False),
        sa.Column("client_name", sa.String(length=120), nullable=False),
        sa.Column("client_phone", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("cleaning_type", sa.String(length=120), nullable=False),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("manager_id", sa.Integer(), nullable=False),
        sa.Column("cleaner_id", sa.Integer(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "NEW",
                "PUBLISHED",
                "ACCEPTED",
                "IN_PROGRESS",
                "BEFORE_PHOTOS_UPLOADED",
                "AFTER_PHOTOS_UPLOADED",
                "COMPLETED",
                "PAID_TO_CLEANER",
                "CANCELLED",
                name="order_status",
            ),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("scheduled_time", sa.DateTime(), nullable=False),
        sa.Column("published_supergroup_id", sa.BigInteger(), nullable=True),
        sa.Column("published_thread_id", sa.Integer(), nullable=True),
        sa.Column("published_message_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["city_id"], ["cities.id"]),
        sa.ForeignKeyConstraint(["cleaner_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "order_photos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("uploader_user_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.Enum("BEFORE", "AFTER", name="photo_kind"), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("telegram_file_id", sa.String(length=300), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploader_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "transactions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.Enum("INCOME", "PAYOUT", name="transaction_type"), nullable=False),
        sa.Column("amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.Enum("NEW", "CONFIRMED", "CANCELLED", name="transaction_status"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "action_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("entity_type", sa.String(length=80), nullable=False),
        sa.Column("entity_id", sa.String(length=80), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "client_blacklist",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("phone", name="uq_client_blacklist_phone"),
    )


def downgrade() -> None:
    op.drop_table("client_blacklist")
    op.drop_table("action_logs")
    op.drop_table("transactions")
    op.drop_table("order_photos")
    op.drop_table("orders")
    op.drop_table("cleaner_cities")
    op.drop_table("cleaner_profiles")
    op.drop_table("city_topics")
    op.drop_table("users")
    op.drop_table("cities")
    op.execute("DROP TYPE IF EXISTS transaction_status")
    op.execute("DROP TYPE IF EXISTS transaction_type")
    op.execute("DROP TYPE IF EXISTS photo_kind")
    op.execute("DROP TYPE IF EXISTS order_status")
    op.execute("DROP TYPE IF EXISTS user_role")
