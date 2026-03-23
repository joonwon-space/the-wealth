"""add_trading_support

Revision ID: cdf80f13c5f6
Revises: e6f7a8b9c0d1
Create Date: 2026-03-23 09:07:00.226446

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdf80f13c5f6'
down_revision: Union[str, Sequence[str], None] = 'e6f7a8b9c0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add trading support: orders table, kis_accounts columns, transactions columns."""
    # Create orders table
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('portfolio_id', sa.Integer(), nullable=False),
        sa.Column('kis_account_id', sa.Integer(), nullable=True),
        sa.Column('ticker', sa.String(length=20), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=True),
        sa.Column('order_type', sa.String(length=10), nullable=False),
        sa.Column('order_class', sa.String(length=10), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('order_no', sa.String(length=50), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('filled_quantity', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('filled_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('memo', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['kis_account_id'], ['kis_accounts.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['portfolio_id'], ['portfolios.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_orders_id'), 'orders', ['id'], unique=False)
    op.create_index(op.f('ix_orders_portfolio_id'), 'orders', ['portfolio_id'], unique=False)
    op.create_index(op.f('ix_orders_status'), 'orders', ['status'], unique=False)
    op.create_index(op.f('ix_orders_ticker'), 'orders', ['ticker'], unique=False)

    # Add columns to kis_accounts
    op.add_column('kis_accounts', sa.Column('is_paper_trading', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('kis_accounts', sa.Column('account_type', sa.String(length=20), nullable=True))

    # Add columns to transactions
    op.add_column('transactions', sa.Column('order_no', sa.String(length=50), nullable=True))
    op.add_column('transactions', sa.Column('order_source', sa.String(length=10), server_default='manual', nullable=False))


def downgrade() -> None:
    """Remove trading support columns and orders table."""
    op.drop_column('transactions', 'order_source')
    op.drop_column('transactions', 'order_no')
    op.drop_column('kis_accounts', 'account_type')
    op.drop_column('kis_accounts', 'is_paper_trading')
    op.drop_index(op.f('ix_orders_ticker'), table_name='orders')
    op.drop_index(op.f('ix_orders_status'), table_name='orders')
    op.drop_index(op.f('ix_orders_portfolio_id'), table_name='orders')
    op.drop_index(op.f('ix_orders_id'), table_name='orders')
    op.drop_table('orders')
