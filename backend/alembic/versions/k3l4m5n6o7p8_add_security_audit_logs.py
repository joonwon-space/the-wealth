"""add security_audit_logs table

Revision ID: k3l4m5n6o7p8
Revises: j2k3l4m5n6o7
Create Date: 2026-04-03 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "k3l4m5n6o7p8"
down_revision: Union[str, None] = "j2k3l4m5n6o7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum type using DO block for compatibility with PostgreSQL < 16
    # (CREATE TYPE IF NOT EXISTS requires PG16+)
    op.execute(
        sa.text(
            "DO $$ BEGIN "
            "CREATE TYPE auditaction AS ENUM ("
            "'LOGIN_SUCCESS', 'LOGIN_FAILURE', 'LOGOUT', 'PASSWORD_CHANGE',"
            " 'ACCOUNT_DELETE', 'KIS_CREDENTIAL_ADD', 'KIS_CREDENTIAL_DELETE'"
            "); "
            "EXCEPTION WHEN duplicate_object THEN NULL; "
            "END $$"
        )
    )

    # Use postgresql.ENUM with create_type=False so SQLAlchemy does not emit
    # a second CREATE TYPE after the DO block above already created it.
    action_enum = postgresql.ENUM(
        "LOGIN_SUCCESS",
        "LOGIN_FAILURE",
        "LOGOUT",
        "PASSWORD_CHANGE",
        "ACCOUNT_DELETE",
        "KIS_CREDENTIAL_ADD",
        "KIS_CREDENTIAL_DELETE",
        name="auditaction",
        create_type=False,
    )

    op.create_table(
        "security_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", action_enum, nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("meta", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_security_audit_logs_id"),
        "security_audit_logs",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_security_audit_logs_user_id"),
        "security_audit_logs",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_security_audit_logs_created_at"),
        "security_audit_logs",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_security_audit_logs_user_id_created_at",
        "security_audit_logs",
        ["user_id", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_security_audit_logs_user_id_created_at",
        table_name="security_audit_logs",
    )
    op.drop_index(
        op.f("ix_security_audit_logs_created_at"),
        table_name="security_audit_logs",
    )
    op.drop_index(
        op.f("ix_security_audit_logs_user_id"),
        table_name="security_audit_logs",
    )
    op.drop_index(
        op.f("ix_security_audit_logs_id"),
        table_name="security_audit_logs",
    )
    op.drop_table("security_audit_logs")

    # Drop the enum type
    sa.Enum(name="auditaction").drop(op.get_bind(), checkfirst=True)
