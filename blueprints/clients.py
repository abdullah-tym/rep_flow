from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from app import db
from models import Client, ClientDocument, User
from forms import ClientForm, DocumentUploadForm
from utils import save_uploaded_file
import os

clients_bp = Blueprint('clients', __name__)

@clients_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status = request.args.get('status', '', type=str)
    
    query = Client.query
    
    # Apply filters based on user role
    if current_user.role.name == 'Client':
        # Clients can only see their own data
        query = query.filter_by(created_by=current_user.id)
    
    # Apply search filter
    if search:
        query = query.filter(
            Client.name.ilike(f'%{search}%') |
            Client.name_ar.ilike(f'%{search}%') |
            Client.email.ilike(f'%{search}%')
        )
    
    # Apply status filter
    if status:
        query = query.filter_by(status=status)
    
    clients = query.order_by(Client.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('clients/index.html', 
                         clients=clients, 
                         search=search, 
                         status=status)

@clients_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to add clients.', 'error')
        return redirect(url_for('clients.index'))
    
    form = ClientForm()
    if form.validate_on_submit():
        client = Client(
            name=form.name.data,
            name_ar=form.name_ar.data,
            email=form.email.data,
            phone=form.phone.data,
            cr_number=form.cr_number.data,
            vat_number=form.vat_number.data,
            address=form.address.data,
            address_ar=form.address_ar.data,
            status=form.status.data,
            created_by=current_user.id
        )
        db.session.add(client)
        db.session.commit()
        
        flash('Client added successfully!', 'success')
        return redirect(url_for('clients.view', id=client.id))
    
    return render_template('clients/form.html', form=form, title='Add Client')

@clients_bp.route('/<int:id>')
@login_required
def view(id):
    client = Client.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client' and client.created_by != current_user.id:
        flash('You do not have permission to view this client.', 'error')
        return redirect(url_for('clients.index'))
    
    # Get client documents
    documents = ClientDocument.query.filter_by(client_id=client.id).order_by(
        ClientDocument.uploaded_at.desc()
    ).all()
    
    # Get recent invoices
    from models import Invoice
    recent_invoices = Invoice.query.filter_by(client_id=client.id).order_by(
        Invoice.created_at.desc()
    ).limit(5).all()
    
    # Get recent tasks
    from models import Task
    recent_tasks = Task.query.filter_by(client_id=client.id).order_by(
        Task.created_at.desc()
    ).limit(5).all()
    
    return render_template('clients/view.html', 
                         client=client,
                         documents=documents,
                         recent_invoices=recent_invoices,
                         recent_tasks=recent_tasks)

@clients_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    client = Client.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client' and client.created_by != current_user.id:
        flash('You do not have permission to edit this client.', 'error')
        return redirect(url_for('clients.index'))
    
    form = ClientForm(obj=client)
    if form.validate_on_submit():
        form.populate_obj(client)
        db.session.commit()
        
        flash('Client updated successfully!', 'success')
        return redirect(url_for('clients.view', id=client.id))
    
    return render_template('clients/form.html', form=form, client=client, title='Edit Client')

@clients_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to delete clients.', 'error')
        return redirect(url_for('clients.index'))
    
    client = Client.query.get_or_404(id)
    
    try:
        # Delete associated documents
        for document in client.documents:
            # Delete file from filesystem
            file_path = os.path.join(current_app.root_path, 'uploads', document.filename)
            if os.path.exists(file_path):
                os.remove(file_path)
            db.session.delete(document)
        
        db.session.delete(client)
        db.session.commit()
        
        flash('Client deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting client. Please try again.', 'error')
    
    return redirect(url_for('clients.index'))

@clients_bp.route('/<int:id>/upload', methods=['GET', 'POST'])
@login_required
def upload_document(id):
    client = Client.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client' and client.created_by != current_user.id:
        flash('You do not have permission to upload documents for this client.', 'error')
        return redirect(url_for('clients.view', id=id))
    
    form = DocumentUploadForm()
    if form.validate_on_submit():
        file = form.file.data
        if file:
            unique_filename, original_filename, file_path = save_uploaded_file(file)
            
            if unique_filename:
                document = ClientDocument(
                    filename=unique_filename,
                    original_filename=original_filename,
                    file_type=file.content_type,
                    file_size=len(file.read()),
                    description=form.description.data,
                    client_id=client.id,
                    uploaded_by=current_user.id
                )
                file.seek(0)  # Reset file pointer
                
                db.session.add(document)
                db.session.commit()
                
                flash('Document uploaded successfully!', 'success')
                return redirect(url_for('clients.view', id=client.id))
            else:
                flash('Error uploading file. Please try again.', 'error')
    
    return render_template('clients/upload.html', form=form, client=client)

@clients_bp.route('/document/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_document(doc_id):
    document = ClientDocument.query.get_or_404(doc_id)
    client_id = document.client_id
    
    # Check permissions
    if current_user.role.name == 'Client' and document.client.created_by != current_user.id:
        flash('You do not have permission to delete this document.', 'error')
        return redirect(url_for('clients.view', id=client_id))
    
    try:
        # Delete file from filesystem
        file_path = os.path.join(current_app.root_path, 'uploads', document.filename)
        if os.path.exists(file_path):
            os.remove(file_path)
        
        db.session.delete(document)
        db.session.commit()
        
        flash('Document deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting document. Please try again.', 'error')
    
    return redirect(url_for('clients.view', id=client_id))
