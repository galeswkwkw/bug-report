"""initial_migration - create core tables

Revision ID: 001
Revises: 
Create Date: 2026-08-01 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    
    # 1. CREATE ROLES TABLE
    op.create_table(
        'roles',
        sa.Column('id', sa.SmallInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(30), nullable=False, unique=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )

    
    # 2. CREATE DEPARTMENTS TABLE
    op.create_table(
        'departments',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False, unique=True)
    )

    
    # 3. CREATE DOCUMENT TYPES TABLE
    op.create_table(
        'document_types',
        sa.Column('id', sa.SmallInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(50), nullable=False, unique=True),
        sa.Column('required', sa.Boolean(), default=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )

    
    # 4. CREATE USERS TABLE
    op.create_table(
        'users',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('role_id', sa.SmallInteger(), sa.ForeignKey('roles.id'), nullable=False),
        sa.Column('department_id', sa.BigInteger(), sa.ForeignKey('departments.id'), nullable=True),
        sa.Column('researcher_type', sa.String(20), nullable=False),
        sa.Column('employee_id', sa.String(30), nullable=True),
        sa.Column('company', sa.String(150), nullable=True),
        sa.Column('full_name', sa.String(150), nullable=False),
        sa.Column('email', sa.String(150), nullable=False, unique=True),
        sa.Column('phone_number', sa.String(20), nullable=True),
        sa.Column('password_hash', sa.Text(), nullable=False),
        sa.Column('total_point', sa.Integer(), default=0),
        sa.Column('status', sa.String(20), nullable=False, default='Pending'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.Column('position', sa.String(100), nullable=True),
        sa.Column('office_location', sa.String(200), nullable=True),
        sa.Column('must_change_password', sa.Boolean(), default=False)
    )

    
    # 5. CREATE USER DOCUMENTS TABLE
    op.create_table(
        'user_documents',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('document_type_id', sa.SmallInteger(), sa.ForeignKey('document_types.id'), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('object_name', sa.String(255), nullable=False),
        sa.Column('bucket_name', sa.String(100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )

    
    # 6. CREATE POINT RULES TABLE
    op.create_table(
        'point_rules',
        sa.Column('id', sa.SmallInteger(), primary_key=True, autoincrement=True),
        sa.Column('severity', sa.String(20), nullable=False, unique=True),
        sa.Column('point', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )

    
    # 7. CREATE ASSETS TABLE
    op.create_table(
        'assets',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False, unique=True),
        sa.Column('asset_type', sa.String(30), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    
    # 8. CREATE REPORTS TABLE
    op.create_table(
        'reports',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('asset_id', sa.BigInteger(), sa.ForeignKey('assets.id'), nullable=False),
        sa.Column('reviewer_id', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('assigned_to', sa.BigInteger(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('steps_to_reproduce', sa.Text(), nullable=False),
        sa.Column('steps_to_resolve', sa.Text(), nullable=True),
        sa.Column('impact', sa.Text(), nullable=True),
        sa.Column('affected_endpoint', sa.String(500), nullable=True),
        sa.Column('severity', sa.String(20), nullable=True),
        sa.Column('point', sa.Integer(), default=0),
        sa.Column('status', sa.String(20), default='Submitted'),
        sa.Column('review_comment', sa.Text(), nullable=True),
        sa.Column('reject_reason', sa.Text(), nullable=True),
        sa.Column('assignment_comment', sa.Text(), nullable=True),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('accepted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('rejected_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    )

    
    # 9. CREATE REPORT EVIDENCES TABLE
    op.create_table(
        'report_evidences',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('report_id', sa.BigInteger(), sa.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False),
        sa.Column('file_name', sa.String(255), nullable=False),
        sa.Column('object_name', sa.String(255), nullable=False),
        sa.Column('bucket_name', sa.String(100), nullable=False),
        sa.Column('file_size', sa.BigInteger(), nullable=False),
        sa.Column('content_type', sa.String(100), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )

    
    # 10. CREATE NOTIFICATIONS TABLE
    op.create_table(
        'notifications',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.BigInteger(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('type', sa.String(50), nullable=False),
        sa.Column('reference_id', sa.BigInteger(), nullable=True),
        sa.Column('is_read', sa.Boolean(), default=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )

    
    # 11. CREATE PASSWORD RESET TOKENS TABLE
    op.create_table(
        'password_reset_tokens',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token', sa.String(255), nullable=False, unique=True),
        sa.Column('expired_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('used_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.func.now())
    )

    
    # 12. CREATE INDEXES
    # Users
    op.create_index('idx_users_email', 'users', ['email'])
    op.create_index('idx_users_status', 'users', ['status'])
    op.create_index('idx_users_role_id', 'users', ['role_id'])

    # Reports
    op.create_index('idx_reports_status', 'reports', ['status'])
    op.create_index('idx_reports_user_id', 'reports', ['user_id'])
    op.create_index('idx_reports_asset_id', 'reports', ['asset_id'])
    op.create_index('idx_reports_assigned_to', 'reports', ['assigned_to'])

    # Notifications
    op.create_index('idx_notifications_user_id', 'notifications', ['user_id'])
    op.create_index('idx_notifications_is_read', 'notifications', ['is_read'])

    # Password Reset Tokens
    op.create_index('idx_password_reset_tokens_token', 'password_reset_tokens', ['token'])
    op.create_index('idx_password_reset_tokens_user_id', 'password_reset_tokens', ['user_id'])

    # User Documents
    op.create_index('idx_user_documents_user_id', 'user_documents', ['user_id'])

    # Report Evidences
    op.create_index('idx_report_evidences_report_id', 'report_evidences', ['report_id'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('idx_report_evidences_report_id')
    op.drop_index('idx_user_documents_user_id')
    op.drop_index('idx_password_reset_tokens_user_id')
    op.drop_index('idx_password_reset_tokens_token')
    op.drop_index('idx_notifications_is_read')
    op.drop_index('idx_notifications_user_id')
    op.drop_index('idx_reports_assigned_to')
    op.drop_index('idx_reports_asset_id')
    op.drop_index('idx_reports_user_id')
    op.drop_index('idx_reports_status')
    op.drop_index('idx_users_role_id')
    op.drop_index('idx_users_status')
    op.drop_index('idx_users_email')

    # Drop tables in reverse order
    op.drop_table('password_reset_tokens')
    op.drop_table('notifications')
    op.drop_table('report_evidences')
    op.drop_table('reports')
    op.drop_table('assets')
    op.drop_table('point_rules')
    op.drop_table('user_documents')
    op.drop_table('users')
    op.drop_table('document_types')
    op.drop_table('departments')
    op.drop_table('roles')