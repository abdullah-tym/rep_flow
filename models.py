from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from app import db
from decimal import Decimal

class Role(db.Model):
    __tablename__ = 'roles'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    users = db.relationship('User', backref='role', lazy='dynamic')

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    phone = db.Column(db.String(20))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    
    # Relationships
    created_clients = db.relationship('Client', backref='created_by_user', lazy='dynamic')
    assigned_tasks = db.relationship('Task', foreign_keys='Task.assigned_to', backref='assigned_user', lazy='dynamic')
    created_invoices = db.relationship('Invoice', backref='created_by_user', lazy='dynamic')

class Company(db.Model):
    __tablename__ = 'companies'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    name_ar = db.Column(db.String(255))
    cr_number = db.Column(db.String(50), unique=True)
    vat_number = db.Column(db.String(50), unique=True)
    iban = db.Column(db.String(50))
    address = db.Column(db.Text)
    address_ar = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    logo_filename = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Client(db.Model):
    __tablename__ = 'clients'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    name_ar = db.Column(db.String(255))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    cr_number = db.Column(db.String(50))
    vat_number = db.Column(db.String(50))
    address = db.Column(db.Text)
    address_ar = db.Column(db.Text)
    status = db.Column(db.String(20), default='Active')  # Active, Closed, Archived
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    invoices = db.relationship('Invoice', backref='client', lazy='dynamic')
    documents = db.relationship('ClientDocument', backref='client', lazy='dynamic')
    tasks = db.relationship('Task', backref='client', lazy='dynamic')

class ClientDocument(db.Model):
    __tablename__ = 'client_documents'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    description = db.Column(db.Text)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    uploader = db.relationship('User', backref='uploaded_documents')

class Invoice(db.Model):
    __tablename__ = 'invoices'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    issue_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date)
    description = db.Column(db.Text)
    subtotal = db.Column(db.Numeric(12, 2), nullable=False)
    vat_rate = db.Column(db.Numeric(5, 2), default=15.00)  # Saudi VAT rate 15%
    vat_amount = db.Column(db.Numeric(12, 2), nullable=False)
    total_amount = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), default='Unpaid')  # Paid, Unpaid, Overdue
    payment_date = db.Column(db.Date)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    items = db.relationship('InvoiceItem', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')
    attachments = db.relationship('InvoiceAttachment', backref='invoice', lazy='dynamic', cascade='all, delete-orphan')

class InvoiceItem(db.Model):
    __tablename__ = 'invoice_items'
    
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.Text, nullable=False)
    quantity = db.Column(db.Numeric(10, 2), nullable=False)
    unit_price = db.Column(db.Numeric(12, 2), nullable=False)
    total_price = db.Column(db.Numeric(12, 2), nullable=False)
    
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)

class InvoiceAttachment(db.Model):
    __tablename__ = 'invoice_attachments'
    
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(50))
    file_size = db.Column(db.Integer)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    invoice_id = db.Column(db.Integer, db.ForeignKey('invoices.id'), nullable=False)

class Task(db.Model):
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    due_date = db.Column(db.Date)
    priority = db.Column(db.String(20), default='Medium')  # High, Medium, Low
    status = db.Column(db.String(20), default='Pending')  # Pending, In Progress, Completed
    task_type = db.Column(db.String(50))  # VAT Filing, Zakat Filing, General
    reminder_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'))
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_tasks')

class VATCalculation(db.Model):
    __tablename__ = 'vat_calculations'
    
    id = db.Column(db.Integer, primary_key=True)
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    total_sales = db.Column(db.Numeric(15, 2), nullable=False)
    total_purchases = db.Column(db.Numeric(15, 2), nullable=False)
    output_vat = db.Column(db.Numeric(12, 2), nullable=False)
    input_vat = db.Column(db.Numeric(12, 2), nullable=False)
    net_vat = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), default='Draft')  # Draft, Submitted, Paid
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class ZakatCalculation(db.Model):
    __tablename__ = 'zakat_calculations'
    
    id = db.Column(db.Integer, primary_key=True)
    hijri_year = db.Column(db.String(10), nullable=False)
    cash_and_deposits = db.Column(db.Numeric(15, 2), default=0)
    trade_goods = db.Column(db.Numeric(15, 2), default=0)
    receivables = db.Column(db.Numeric(15, 2), default=0)
    investments = db.Column(db.Numeric(15, 2), default=0)
    total_assets = db.Column(db.Numeric(15, 2), nullable=False)
    liabilities = db.Column(db.Numeric(15, 2), default=0)
    net_wealth = db.Column(db.Numeric(15, 2), nullable=False)
    zakat_due = db.Column(db.Numeric(12, 2), nullable=False)
    nisab_threshold = db.Column(db.Numeric(12, 2), nullable=False)
    status = db.Column(db.String(20), default='Draft')  # Draft, Submitted, Paid
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    client_id = db.Column(db.Integer, db.ForeignKey('clients.id'))
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

class Notification(db.Model):
    __tablename__ = 'notifications'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    message = db.Column(db.Text, nullable=False)
    notification_type = db.Column(db.String(50))  # email, whatsapp, system
    recipient_email = db.Column(db.String(120))
    recipient_phone = db.Column(db.String(20))
    is_sent = db.Column(db.Boolean, default=False)
    sent_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    recipient = db.relationship('User', backref='notifications')
