from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from app import db
from models import Company
from forms import CompanySettingsForm
from utils import save_uploaded_file
import os

settings_bp = Blueprint('settings', __name__)

@settings_bp.route('/')
@login_required
def index():
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to access settings.', 'error')
        return redirect(url_for('dashboard.index'))
    
    # Get or create company settings
    company = Company.query.first()
    if not company:
        company = Company(name="Your Company Name")
        db.session.add(company)
        db.session.commit()
    
    return render_template('settings/index.html', company=company)

@settings_bp.route('/company', methods=['GET', 'POST'])
@login_required
def company():
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to edit company settings.', 'error')
        return redirect(url_for('settings.index'))
    
    # Get or create company settings
    company_obj = Company.query.first()
    if not company_obj:
        company_obj = Company(name="Your Company Name")
        db.session.add(company_obj)
        db.session.commit()
    
    form = CompanySettingsForm(obj=company_obj)
    
    if form.validate_on_submit():
        # Handle logo upload
        if form.logo.data:
            logo_file = form.logo.data
            unique_filename, original_filename, file_path = save_uploaded_file(
                logo_file, 
                upload_folder='static/uploads/logos'
            )
            
            if unique_filename:
                # Delete old logo if exists
                if company_obj.logo_filename:
                    old_logo_path = os.path.join(
                        current_app.root_path, 
                        'static/uploads/logos', 
                        company_obj.logo_filename
                    )
                    if os.path.exists(old_logo_path):
                        os.remove(old_logo_path)
                
                company_obj.logo_filename = unique_filename
        
        # Update company details
        form.populate_obj(company_obj)
        db.session.commit()
        
        flash('Company settings updated successfully!', 'success')
        return redirect(url_for('settings.index'))
    
    return render_template('settings/company_form.html', form=form, company=company_obj)

@settings_bp.route('/users')
@login_required
def users():
    if current_user.role.name != 'Admin':
        flash('You do not have permission to manage users.', 'error')
        return redirect(url_for('settings.index'))
    
    from models import User
    
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    role = request.args.get('role', '', type=str)
    
    query = User.query
    
    # Apply search filter
    if search:
        query = query.filter(
            User.username.ilike(f'%{search}%') |
            User.email.ilike(f'%{search}%') |
            User.first_name.ilike(f'%{search}%') |
            User.last_name.ilike(f'%{search}%')
        )
    
    # Apply role filter
    if role:
        query = query.filter(User.role.has(name=role))
    
    users = query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('settings/users.html', 
                         users=users, 
                         search=search, 
                         role=role)

@settings_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
def toggle_user_status(user_id):
    if current_user.role.name != 'Admin':
        flash('You do not have permission to manage users.', 'error')
        return redirect(url_for('settings.users'))
    
    from models import User
    
    user = User.query.get_or_404(user_id)
    
    # Prevent admin from deactivating themselves
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'error')
        return redirect(url_for('settings.users'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(url_for('settings.users'))

@settings_bp.route('/backup')
@login_required
def backup():
    if current_user.role.name != 'Admin':
        flash('You do not have permission to access backup settings.', 'error')
        return redirect(url_for('settings.index'))
    
    return render_template('settings/backup.html')

@settings_bp.route('/notifications')
@login_required
def notifications():
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to access notification settings.', 'error')
        return redirect(url_for('settings.index'))
    
    return render_template('settings/notifications.html')
