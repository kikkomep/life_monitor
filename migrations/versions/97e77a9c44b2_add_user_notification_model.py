"""Add user notification model

Revision ID: 97e77a9c44b2
Revises: f4cbfe20075f
Create Date: 2022-01-17 13:21:37.565495

"""
from alembic import op
import sqlalchemy as sa
from lifemonitor.models import JSON


# revision identifiers, used by Alembic.
revision = '97e77a9c44b2'
down_revision = 'f4cbfe20075f'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('notification',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('name', sa.String(), nullable=True),
                    sa.Column('type', sa.String(), nullable=False),
                    sa.Column('data', JSON(), nullable=True),
                    sa.PrimaryKeyConstraint('id')
                    )
    op.create_table('user_notification',
                    sa.Column('emailed', sa.DateTime(), nullable=True),
                    sa.Column('read', sa.DateTime(), nullable=True),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('notification_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['notification_id'], ['notification.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
                    sa.PrimaryKeyConstraint('user_id', 'notification_id')
                    )
    op.add_column('user', sa.Column('email', sa.String(), nullable=True))
    op.add_column('user', sa.Column('email_verification_hash', sa.String(length=256), nullable=True))
    op.add_column('user', sa.Column('email_verified', sa.Boolean(), nullable=True))


def downgrade():
    op.drop_column('user', 'email_verified')
    op.drop_column('user', 'email_verification_hash')
    op.drop_column('user', 'email')
    op.drop_table('user_notification')
    op.drop_table('notification')