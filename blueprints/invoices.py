from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response
from flask_login import login_required, current_user
from app import db
from models import Invoice, InvoiceItem, InvoiceAttachment, Client
from forms import InvoiceForm, InvoiceItemForm
from utils import calculate_vat, generate_invoice_pdf, save_uploaded_file
from decimal import Decimal
import uuid

invoices_bp = Blueprint('invoices', __name__)

@invoices_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status = request.args.get('status', '', type=str)
    client_id = request.args.get('client_id', '', type=str)
    
    query = Invoice.query
    
    # Apply filters based on user role
    if current_user.role.name == 'Client':
        # Clients can only see their invoices
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            query = query.filter_by(client_id=client.id)
        else:
            query = query.filter_by(client_id=-1)  # No results
    
    # Apply search filter
    if search:
        query = query.join(Client).filter(
            Invoice.invoice_number.ilike(f'%{search}%') |
            Client.name.ilike(f'%{search}%') |
            Invoice.description.ilike(f'%{search}%')
        )
    
    # Apply status filter
    if status:
        query = query.filter_by(status=status)
    
    # Apply client filter
    if client_id:
        query = query.filter_by(client_id=client_id)
    
    invoices = query.order_by(Invoice.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get clients for filter dropdown
    if current_user.role.name == 'Client':
        clients = []
    else:
        clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
    
    return render_template('invoices/index.html', 
                         invoices=invoices, 
                         search=search, 
                         status=status,
                         client_id=client_id,
                         clients=clients)

@invoices_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to create invoices.', 'error')
        return redirect(url_for('invoices.index'))
    
    form = InvoiceForm()
    
    # Populate client choices
    clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
    form.client_id.choices = [(c.id, c.name) for c in clients]
    
    if form.validate_on_submit():
        # Generate unique invoice number
        invoice_number = form.invoice_number.data
        if Invoice.query.filter_by(invoice_number=invoice_number).first():
            flash('Invoice number already exists. Please use a different number.', 'error')
            return render_template('invoices/form.html', form=form, title='Create Invoice')
        
        # Calculate VAT and total
        vat_amount, total_amount = calculate_vat(form.subtotal.data, form.vat_rate.data)
        
        invoice = Invoice(
            invoice_number=invoice_number,
            client_id=form.client_id.data,
            issue_date=form.issue_date.data,
            due_date=form.due_date.data,
            description=form.description.data,
            subtotal=form.subtotal.data,
            vat_rate=form.vat_rate.data,
            vat_amount=vat_amount,
            total_amount=total_amount,
            status=form.status.data,
            payment_date=form.payment_date.data,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        db.session.add(invoice)
        db.session.commit()
        
        flash('Invoice created successfully!', 'success')
        return redirect(url_for('invoices.view', id=invoice.id))
    
    # Generate default invoice number
    if not form.invoice_number.data:
        last_invoice = Invoice.query.order_by(Invoice.id.desc()).first()
        next_number = (last_invoice.id + 1) if last_invoice else 1
        form.invoice_number.data = f"INV-{next_number:06d}"
    
    return render_template('invoices/form.html', form=form, title='Create Invoice')

@invoices_bp.route('/<int:id>')
@login_required
def view(id):
    invoice = Invoice.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client or invoice.client_id != client.id:
            flash('You do not have permission to view this invoice.', 'error')
            return redirect(url_for('invoices.index'))
    
    return render_template('invoices/view.html', invoice=invoice)

@invoices_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to edit invoices.', 'error')
        return redirect(url_for('invoices.index'))
    
    invoice = Invoice.query.get_or_404(id)
    form = InvoiceForm(obj=invoice)
    
    # Populate client choices
    clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
    form.client_id.choices = [(c.id, c.name) for c in clients]
    
    if form.validate_on_submit():
        # Check if invoice number is unique (excluding current invoice)
        existing_invoice = Invoice.query.filter(
            Invoice.invoice_number == form.invoice_number.data,
            Invoice.id != invoice.id
        ).first()
        
        if existing_invoice:
            flash('Invoice number already exists. Please use a different number.', 'error')
            return render_template('invoices/form.html', form=form, invoice=invoice, title='Edit Invoice')
        
        # Calculate VAT and total
        vat_amount, total_amount = calculate_vat(form.subtotal.data, form.vat_rate.data)
        
        # Update invoice
        form.populate_obj(invoice)
        invoice.vat_amount = vat_amount
        invoice.total_amount = total_amount
        
        db.session.commit()
        
        flash('Invoice updated successfully!', 'success')
        return redirect(url_for('invoices.view', id=invoice.id))
    
    return render_template('invoices/form.html', form=form, invoice=invoice, title='Edit Invoice')

@invoices_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to delete invoices.', 'error')
        return redirect(url_for('invoices.index'))
    
    invoice = Invoice.query.get_or_404(id)
    
    try:
        db.session.delete(invoice)
        db.session.commit()
        
        flash('Invoice deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting invoice. Please try again.', 'error')
    
    return redirect(url_for('invoices.index'))

@invoices_bp.route('/<int:id>/items')
@login_required
def manage_items(id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to manage invoice items.', 'error')
        return redirect(url_for('invoices.view', id=id))
    
    invoice = Invoice.query.get_or_404(id)
    items = InvoiceItem.query.filter_by(invoice_id=invoice.id).all()
    
    return render_template('invoices/items.html', invoice=invoice, items=items)

@invoices_bp.route('/<int:id>/items/add', methods=['GET', 'POST'])
@login_required
def add_item(id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to add invoice items.', 'error')
        return redirect(url_for('invoices.view', id=id))
    
    invoice = Invoice.query.get_or_404(id)
    form = InvoiceItemForm()
    
    if form.validate_on_submit():
        total_price = form.quantity.data * form.unit_price.data
        
        item = InvoiceItem(
            description=form.description.data,
            quantity=form.quantity.data,
            unit_price=form.unit_price.data,
            total_price=total_price,
            invoice_id=invoice.id
        )
        
        db.session.add(item)
        
        # Recalculate invoice totals
        recalculate_invoice_totals(invoice)
        
        db.session.commit()
        
        flash('Invoice item added successfully!', 'success')
        return redirect(url_for('invoices.manage_items', id=invoice.id))
    
    return render_template('invoices/item_form.html', form=form, invoice=invoice, title='Add Item')

@invoices_bp.route('/items/<int:item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to edit invoice items.', 'error')
        return redirect(url_for('invoices.index'))
    
    item = InvoiceItem.query.get_or_404(item_id)
    invoice = item.invoice
    form = InvoiceItemForm(obj=item)
    
    if form.validate_on_submit():
        form.populate_obj(item)
        item.total_price = item.quantity * item.unit_price
        
        # Recalculate invoice totals
        recalculate_invoice_totals(invoice)
        
        db.session.commit()
        
        flash('Invoice item updated successfully!', 'success')
        return redirect(url_for('invoices.manage_items', id=invoice.id))
    
    return render_template('invoices/item_form.html', form=form, invoice=invoice, item=item, title='Edit Item')

@invoices_bp.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to delete invoice items.', 'error')
        return redirect(url_for('invoices.index'))
    
    item = InvoiceItem.query.get_or_404(item_id)
    invoice = item.invoice
    
    db.session.delete(item)
    
    # Recalculate invoice totals
    recalculate_invoice_totals(invoice)
    
    db.session.commit()
    
    flash('Invoice item deleted successfully!', 'success')
    return redirect(url_for('invoices.manage_items', id=invoice.id))

@invoices_bp.route('/<int:id>/pdf')
@login_required
def download_pdf(id):
    invoice = Invoice.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client or invoice.client_id != client.id:
            flash('You do not have permission to download this invoice.', 'error')
            return redirect(url_for('invoices.index'))
    
    pdf_buffer = generate_invoice_pdf(invoice)
    
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=invoice_{invoice.invoice_number}.pdf'
    
    return response

@invoices_bp.route('/<int:id>/mark-paid', methods=['POST'])
@login_required
def mark_paid(id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to mark invoices as paid.', 'error')
        return redirect(url_for('invoices.view', id=id))
    
    invoice = Invoice.query.get_or_404(id)
    invoice.status = 'Paid'
    invoice.payment_date = db.func.current_date()
    
    db.session.commit()
    
    flash('Invoice marked as paid!', 'success')
    return redirect(url_for('invoices.view', id=id))

def recalculate_invoice_totals(invoice):
    """Recalculate invoice subtotal, VAT, and total based on items"""
    items_total = sum(item.total_price for item in invoice.items)
    
    if items_total > 0:
        invoice.subtotal = items_total
        vat_amount, total_amount = calculate_vat(invoice.subtotal, invoice.vat_rate)
        invoice.vat_amount = vat_amount
        invoice.total_amount = total_amount
    else:
        # Keep original values if no items
        vat_amount, total_amount = calculate_vat(invoice.subtotal, invoice.vat_rate)
        invoice.vat_amount = vat_amount
        invoice.total_amount = total_amount
