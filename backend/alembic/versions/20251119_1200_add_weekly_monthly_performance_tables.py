"""add weekly monthly performance tables

Revision ID: 2a3b4c5d6e7f
Revises: 4fc9c8e54619
Create Date: 2025-11-19 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB


# revision identifiers, used by Alembic.
revision: str = '2a3b4c5d6e7f'
down_revision: Union[str, None] = '4fc9c8e54619'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. weekly_reports 테이블 생성
    op.create_table(
        'weekly_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, comment='보고서 ID'),
        sa.Column('owner', sa.String(100), nullable=False, index=True, comment='작성자'),
        sa.Column('period_start', sa.Date(), nullable=False, index=True, comment='시작일'),
        sa.Column('period_end', sa.Date(), nullable=False, index=True, comment='종료일'),
        sa.Column('report_json', JSONB, nullable=False, comment='CanonicalReport JSON'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), comment='수정일시'),
        sa.UniqueConstraint('owner', 'period_start', 'period_end', name='uq_weekly_report_owner_period')
    )
    
    # 2. monthly_reports 테이블 생성
    op.create_table(
        'monthly_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, comment='보고서 ID'),
        sa.Column('owner', sa.String(100), nullable=False, index=True, comment='작성자'),
        sa.Column('period_start', sa.Date(), nullable=False, index=True, comment='시작일'),
        sa.Column('period_end', sa.Date(), nullable=False, index=True, comment='종료일'),
        sa.Column('report_json', JSONB, nullable=False, comment='CanonicalReport JSON'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), comment='수정일시'),
        sa.UniqueConstraint('owner', 'period_start', 'period_end', name='uq_monthly_report_owner_period')
    )
    
    # 3. performance_reports 테이블 생성
    op.create_table(
        'performance_reports',
        sa.Column('id', UUID(as_uuid=True), primary_key=True, comment='보고서 ID'),
        sa.Column('owner', sa.String(100), nullable=False, index=True, comment='작성자'),
        sa.Column('period_start', sa.Date(), nullable=False, index=True, comment='시작일'),
        sa.Column('period_end', sa.Date(), nullable=False, index=True, comment='종료일'),
        sa.Column('report_json', JSONB, nullable=False, comment='CanonicalReport JSON'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), comment='생성일시'),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), comment='수정일시'),
        sa.UniqueConstraint('owner', 'period_start', 'period_end', name='uq_performance_report_owner_period')
    )


def downgrade() -> None:
    op.drop_table('performance_reports')
    op.drop_table('monthly_reports')
    op.drop_table('weekly_reports')

