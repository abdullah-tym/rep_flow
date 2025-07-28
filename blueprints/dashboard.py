from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func, and_
from datetime import datetime, timedelta, date
from app import db
from models import Client, Invoice, Task, VATCalculation, ZakatCalculation

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    # Get dashboard statistics
    stats = get_dashboard_stats()
    
    # Get recent activities
    recent_invoices = get_recent_invoices()
    upcoming_tasks = get_upcoming_tasks()
    pending_calculations = get_pending_calculations()
    
    return render_template('dashboard/index.html',
                         stats=stats,
                         recent_invoices=recent_invoices,
                         upcoming_tasks=upcoming_tasks,
                         pending_calculations=pending_calculations)

def get_dashboard_stats():
    """Get dashboard statistics"""
    today = date.today()
    current_month = today.replace(day=1)
    
    # Base query filters based on user role
    if current_user.role.name == 'Client':
        # Client can only see their own data
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client:
            return {
                'total_clients': 0,
                'total_invoices': 0,
                'monthly_revenue': 0,
                'pending_tasks': 0,
                'overdue_invoices': 0,
                'unpaid_amount': 0
            }
        client_filter = Invoice.client_id == client.id
        task_client_filter = Task.client_id == client.id
    else:
        # Admin and Accountant can see all data
        client_filter = True
        task_client_filter = True
    
    # Total clients
    if current_user.role.name == 'Client':
        total_clients = 1 if client else 0
    else:
        total_clients = Client.query.count()
    
    # Total invoices
    total_invoices = Invoice.query.filter(client_filter).count()
    
    # Monthly revenue (current month)
    monthly_revenue = db.session.query(func.sum(Invoice.total_amount)).filter(
        and_(
            Invoice.issue_date >= current_month,
            Invoice.status == 'Paid',
            client_filter
        )
    ).scalar() or 0
    
    # Pending tasks
    pending_tasks = Task.query.filter(
        and_(
            Task.status.in_(['Pending', 'In Progress']),
            task_client_filter
        )
    ).count()
    
    # Overdue invoices
    overdue_invoices = Invoice.query.filter(
        and_(
            Invoice.due_date < today,
            Invoice.status != 'Paid',
            client_filter
        )
    ).count()
    
    # Unpaid amount
    unpaid_amount = db.session.query(func.sum(Invoice.total_amount)).filter(
        and_(
            Invoice.status != 'Paid',
            client_filter
        )
    ).scalar() or 0
    
    return {
        'total_clients': total_clients,
        'total_invoices': total_invoices,
        'monthly_revenue': float(monthly_revenue),
        'pending_tasks': pending_tasks,
        'overdue_invoices': overdue_invoices,
        'unpaid_amount': float(unpaid_amount)
    }

def get_recent_invoices(limit=5):
    """Get recent invoices"""
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client:
            return []
        invoices = Invoice.query.filter_by(client_id=client.id)
    else:
        invoices = Invoice.query
    
    return invoices.order_by(Invoice.created_at.desc()).limit(limit).all()

def get_upcoming_tasks(limit=5):
    """Get upcoming tasks"""
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client:
            return []
        tasks = Task.query.filter_by(client_id=client.id)
    else:
        tasks = Task.query
    
    return tasks.filter(
        and_(
            Task.status.in_(['Pending', 'In Progress']),
            Task.due_date >= date.today()
        )
    ).order_by(Task.due_date.asc()).limit(limit).all()

def get_pending_calculations():
    """Get pending VAT and Zakat calculations"""
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client:
            return {'vat': [], 'zakat': []}
        vat_filter = VATCalculation.client_id == client.id
        zakat_filter = ZakatCalculation.client_id == client.id
    else:
        vat_filter = True
        zakat_filter = True
    
    pending_vat = VATCalculation.query.filter(
        and_(VATCalculation.status == 'Draft', vat_filter)
    ).order_by(VATCalculation.created_at.desc()).limit(3).all()
    
    pending_zakat = ZakatCalculation.query.filter(
        and_(ZakatCalculation.status == 'Draft', zakat_filter)
    ).order_by(ZakatCalculation.created_at.desc()).limit(3).all()
    
    return {
        'vat': pending_vat,
        'zakat': pending_zakat
    }
