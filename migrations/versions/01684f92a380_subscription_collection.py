"""Subscription collection

Revision ID: 01684f92a380
Revises: 6086cb72f9e1
Create Date: 2021-10-15 10:02:53.756948

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '01684f92a380'
down_revision = '6086cb72f9e1'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic ###
    op.create_table('subscription',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('created', sa.DateTime(), nullable=True),
                    sa.Column('modified', sa.DateTime(), nullable=True),
                    sa.Column('user_id', sa.Integer(), nullable=False),
                    sa.Column('resource_id', sa.Integer(), nullable=False),
                    sa.ForeignKeyConstraint(['resource_id'], ['resource.id'], ),
                    sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
                    sa.PrimaryKeyConstraint('id')
                    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic ###
    op.drop_table('subscription')
    # ### end Alembic commands ###
