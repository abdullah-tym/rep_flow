from flask import Blueprint, render_template, request, make_response, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, and_, extract
from app import db
from models import Invoice, Client, Task, VATCalculation, ZakatCalculation
from utils import export_to_csv
from datetime import datetime, date, timedelta
import calendar

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/')
@login_required
def index():
    return render_template('reports/index.html')

@reports_bp.route('/revenue')
@login_required
def revenue_report():
    # Get date range from query parameters
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    client_id = request.args.get('client_id', type=int)
    
    # Default to current month if no dates provided
    if not start_date or not end_date:
        today = date.today()
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Base query filters based on user role
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            client_filter = Invoice.client_id == client.id
        else:
            client_filter = Invoice.client_id == -1  # No results
    else:
        client_filter = True
    
    # Build query
    query = Invoice.query.filter(
        and_(
            Invoice.issue_date >= start_date_obj,
            Invoice.issue_date <= end_date_obj,
            client_filter
        )
    )
    
    # Apply client filter if specified
    if client_id:
        query = query.filter_by(client_id=client_id)
    
    invoices = query.order_by(Invoice.issue_date.desc()).all()
    
    # Calculate totals
    total_revenue = sum(invoice.total_amount for invoice in invoices if invoice.status == 'Paid')
    total_outstanding = sum(invoice.total_amount for invoice in invoices if invoice.status != 'Paid')
    total_vat = sum(invoice.vat_amount for invoice in invoices if invoice.status == 'Paid')
    
    # Monthly breakdown
    monthly_data = {}
    for invoice in invoices:
        month_key = invoice.issue_date.strftime('%Y-%m')
        if month_key not in monthly_data:
            monthly_data[month_key] = {
                'month': invoice.issue_date.strftime('%B %Y'),
                'paid': 0,
                'unpaid': 0,
                'vat': 0
            }
        
        if invoice.status == 'Paid':
            monthly_data[month_key]['paid'] += float(invoice.total_amount)
            monthly_data[month_key]['vat'] += float(invoice.vat_amount)
        else:
            monthly_data[month_key]['unpaid'] += float(invoice.total_amount)
    
    # Client breakdown (for Admin/Accountant only)
    client_data = {}
    if current_user.role.name in ['Admin', 'Accountant']:
        for invoice in invoices:
            client_name = invoice.client.name
            if client_name not in client_data:
                client_data[client_name] = {
                    'paid': 0,
                    'unpaid': 0,
                    'vat': 0
                }
            
            if invoice.status == 'Paid':
                client_data[client_name]['paid'] += float(invoice.total_amount)
                client_data[client_name]['vat'] += float(invoice.vat_amount)
            else:
                client_data[client_name]['unpaid'] += float(invoice.total_amount)
    
    # Get clients for filter dropdown
    if current_user.role.name in ['Admin', 'Accountant']:
        clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
    else:
        clients = []
    
    return render_template('reports/revenue.html',
                         invoices=invoices,
                         total_revenue=float(total_revenue),
                         total_outstanding=float(total_outstanding),
                         total_vat=float(total_vat),
                         monthly_data=list(monthly_data.values()),
                         client_data=client_data,
                         start_date=start_date,
                         end_date=end_date,
                         client_id=client_id,
                         clients=clients)

@reports_bp.route('/vat')
@login_required
def vat_report():
    # Get date range from query parameters
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    client_id = request.args.get('client_id', type=int)
    
    # Default to current year if no dates provided
    if not start_date or not end_date:
        today = date.today()
        start_date = today.replace(month=1, day=1).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Base query filters based on user role
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            client_filter = VATCalculation.client_id == client.id
        else:
            client_filter = VATCalculation.client_id == -1  # No results
    else:
        client_filter = True
    
    # Build query
    query = VATCalculation.query.filter(
        and_(
            VATCalculation.period_start >= start_date_obj,
            VATCalculation.period_end <= end_date_obj,
            client_filter
        )
    )
    
    # Apply client filter if specified
    if client_id:
        query = query.filter_by(client_id=client_id)
    
    vat_calculations = query.order_by(VATCalculation.period_start.desc()).all()
    
    # Calculate totals
    total_output_vat = sum(calc.output_vat for calc in vat_calculations)
    total_input_vat = sum(calc.input_vat for calc in vat_calculations)
    total_net_vat = sum(calc.net_vat for calc in vat_calculations)
    
    # Get clients for filter dropdown
    if current_user.role.name in ['Admin', 'Accountant']:
        clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
    else:
        clients = []
    
    return render_template('reports/vat.html',
                         vat_calculations=vat_calculations,
                         total_output_vat=float(total_output_vat),
                         total_input_vat=float(total_input_vat),
                         total_net_vat=float(total_net_vat),
                         start_date=start_date,
                         end_date=end_date,
                         client_id=client_id,
                         clients=clients)

@reports_bp.route('/zakat')
@login_required
def zakat_report():
    # Get Hijri year from query parameters
    hijri_year = request.args.get('hijri_year', type=str)
    client_id = request.args.get('client_id', type=int)
    
    # Default to current Hijri year if not provided
    if not hijri_year:
        current_year = datetime.now().year
        hijri_year = f"{current_year - 622 + 1}H"
    
    # Base query filters based on user role
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            client_filter = ZakatCalculation.client_id == client.id
        else:
            client_filter = ZakatCalculation.client_id == -1  # No results
    else:
        client_filter = True
    
    # Build query
    query = ZakatCalculation.query.filter(
        and_(
            ZakatCalculation.hijri_year == hijri_year,
            client_filter
        )
    )
    
    # Apply client filter if specified
    if client_id:
        query = query.filter_by(client_id=client_id)
    
    zakat_calculations = query.order_by(ZakatCalculation.created_at.desc()).all()
    
    # Calculate totals
    total_assets = sum(calc.total_assets for calc in zakat_calculations)
    total_liabilities = sum(calc.liabilities for calc in zakat_calculations)
    total_net_wealth = sum(calc.net_wealth for calc in zakat_calculations)
    total_zakat_due = sum(calc.zakat_due for calc in zakat_calculations)
    
    # Get clients for filter dropdown
    if current_user.role.name in ['Admin', 'Accountant']:
        clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
    else:
        clients = []
    
    return render_template('reports/zakat.html',
                         zakat_calculations=zakat_calculations,
                         total_assets=float(total_assets),
                         total_liabilities=float(total_liabilities),
                         total_net_wealth=float(total_net_wealth),
                         total_zakat_due=float(total_zakat_due),
                         hijri_year=hijri_year,
                         client_id=client_id,
                         clients=clients)

@reports_bp.route('/tasks')
@login_required
def tasks_report():
    # Get date range from query parameters
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    status = request.args.get('status', type=str)
    assigned_to = request.args.get('assigned_to', type=int)
    
    # Default to current month if no dates provided
    if not start_date or not end_date:
        today = date.today()
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Base query filters based on user role
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            task_filter = Task.client_id == client.id
        else:
            task_filter = Task.client_id == -1  # No results
    elif current_user.role.name == 'Accountant':
        task_filter = (Task.assigned_to == current_user.id) | (Task.created_by == current_user.id)
    else:
        task_filter = True
    
    # Build query
    query = Task.query.filter(
        and_(
            Task.created_at >= datetime.combine(start_date_obj, datetime.min.time()),
            Task.created_at <= datetime.combine(end_date_obj, datetime.max.time()),
            task_filter
        )
    )
    
    # Apply filters
    if status:
        query = query.filter_by(status=status)
    
    if assigned_to:
        query = query.filter_by(assigned_to=assigned_to)
    
    tasks = query.order_by(Task.created_at.desc()).all()
    
    # Calculate statistics
    total_tasks = len(tasks)
    completed_tasks = len([t for t in tasks if t.status == 'Completed'])
    pending_tasks = len([t for t in tasks if t.status == 'Pending'])
    in_progress_tasks = len([t for t in tasks if t.status == 'In Progress'])
    overdue_tasks = len([t for t in tasks if t.due_date and t.due_date < date.today() and t.status != 'Completed'])
    
    # Task type breakdown
    task_type_data = {}
    for task in tasks:
        task_type = task.task_type or 'General'
        if task_type not in task_type_data:
            task_type_data[task_type] = 0
        task_type_data[task_type] += 1
    
    # Get users for filter dropdown
    if current_user.role.name in ['Admin', 'Accountant']:
        from models import User
        users = User.query.filter(User.role.has(name__in=['Admin', 'Accountant'])).order_by(User.first_name).all()
    else:
        users = []
    
    return render_template('reports/tasks.html',
                         tasks=tasks,
                         total_tasks=total_tasks,
                         completed_tasks=completed_tasks,
                         pending_tasks=pending_tasks,
                         in_progress_tasks=in_progress_tasks,
                         overdue_tasks=overdue_tasks,
                         task_type_data=task_type_data,
                         start_date=start_date,
                         end_date=end_date,
                         status=status,
                         assigned_to=assigned_to,
                         users=users)

@reports_bp.route('/export/revenue')
@login_required
def export_revenue_csv():
    # Get same parameters as revenue report
    start_date = request.args.get('start_date', type=str)
    end_date = request.args.get('end_date', type=str)
    client_id = request.args.get('client_id', type=int)
    
    if not start_date or not end_date:
        today = date.today()
        start_date = today.replace(day=1).strftime('%Y-%m-%d')
        end_date = today.strftime('%Y-%m-%d')
    
    start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
    end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
    
    # Base query filters based on user role
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            client_filter = Invoice.client_id == client.id
        else:
            client_filter = Invoice.client_id == -1
    else:
        client_filter = True
    
    query = Invoice.query.filter(
        and_(
            Invoice.issue_date >= start_date_obj,
            Invoice.issue_date <= end_date_obj,
            client_filter
        )
    )
    
    if client_id:
        query = query.filter_by(client_id=client_id)
    
    invoices = query.order_by(Invoice.issue_date.desc()).all()
    
    # Prepare data for CSV
    columns = ['Invoice Number', 'Client', 'Issue Date', 'Due Date', 'Subtotal (SAR)', 'VAT (SAR)', 'Total (SAR)', 'Status', 'Payment Date']
    data = []
    
    for invoice in invoices:
        data.append([
            invoice.invoice_number,
            invoice.client.name,
            invoice.issue_date.strftime('%Y-%m-%d'),
            invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else '',
            f"{invoice.subtotal:.2f}",
            f"{invoice.vat_amount:.2f}",
            f"{invoice.total_amount:.2f}",
            invoice.status,
            invoice.payment_date.strftime('%Y-%m-%d') if invoice.payment_date else ''
        ])
    
    csv_content = export_to_csv(data, columns)
    
    response = make_response(csv_content)
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=revenue_report_{start_date}_to_{end_date}.csv'
    
    return response

@reports_bp.route('/api/dashboard-data')
@login_required
def api_dashboard_data():
    """API endpoint for dashboard charts data"""
    try:
        # Monthly revenue for the past 6 months
        today = date.today()
        six_months_ago = today - timedelta(days=180)
        
        # Base query filters based on user role
        if current_user.role.name == 'Client':
            client = Client.query.filter_by(created_by=current_user.id).first()
            if client:
                client_filter = Invoice.client_id == client.id
            else:
                client_filter = Invoice.client_id == -1
        else:
            client_filter = True
        
        # Get monthly revenue data
        monthly_revenue = db.session.query(
            extract('year', Invoice.issue_date).label('year'),
            extract('month', Invoice.issue_date).label('month'),
            func.sum(Invoice.total_amount).label('total')
        ).filter(
            and_(
                Invoice.issue_date >= six_months_ago,
                Invoice.status == 'Paid',
                client_filter
            )
        ).group_by(
            extract('year', Invoice.issue_date),
            extract('month', Invoice.issue_date)
        ).order_by(
            extract('year', Invoice.issue_date),
            extract('month', Invoice.issue_date)
        ).all()
        
        # Format data for charts
        revenue_labels = []
        revenue_data = []
        
        for item in monthly_revenue:
            month_name = calendar.month_abbr[int(item.month)]
            revenue_labels.append(f"{month_name} {int(item.year)}")
            revenue_data.append(float(item.total or 0))
        
        # Task status distribution
        if current_user.role.name == 'Client':
            client = Client.query.filter_by(created_by=current_user.id).first()
            if client:
                task_filter = Task.client_id == client.id
            else:
                task_filter = Task.client_id == -1
        elif current_user.role.name == 'Accountant':
            task_filter = (Task.assigned_to == current_user.id) | (Task.created_by == current_user.id)
        else:
            task_filter = True
        
        task_status = db.session.query(
            Task.status,
            func.count(Task.id).label('count')
        ).filter(task_filter).group_by(Task.status).all()
        
        task_labels = []
        task_data = []
        
        for item in task_status:
            task_labels.append(item.status)
            task_data.append(item.count)
        
        return jsonify({
            'success': True,
            'revenue': {
                'labels': revenue_labels,
                'data': revenue_data
            },
            'tasks': {
                'labels': task_labels,
                'data': task_data
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
