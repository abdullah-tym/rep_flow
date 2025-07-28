from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from models import Task, Client, User
from forms import TaskForm
from datetime import date, datetime, timedelta

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/')
@login_required
def index():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '', type=str)
    priority = request.args.get('priority', '', type=str)
    task_type = request.args.get('task_type', '', type=str)
    assigned_to = request.args.get('assigned_to', '', type=str)
    
    query = Task.query
    
    # Apply filters based on user role
    if current_user.role.name == 'Client':
        # Clients can only see tasks related to them
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            query = query.filter_by(client_id=client.id)
        else:
            query = query.filter_by(client_id=-1)  # No results
    elif current_user.role.name == 'Accountant':
        # Accountants can see tasks assigned to them or created by them
        query = query.filter(
            (Task.assigned_to == current_user.id) | 
            (Task.created_by == current_user.id)
        )
    
    # Apply status filter
    if status:
        query = query.filter_by(status=status)
    
    # Apply priority filter
    if priority:
        query = query.filter_by(priority=priority)
    
    # Apply task type filter
    if task_type:
        query = query.filter_by(task_type=task_type)
    
    # Apply assigned to filter
    if assigned_to:
        query = query.filter_by(assigned_to=assigned_to)
    
    tasks = query.order_by(Task.due_date.asc().nullslast(), Task.priority.desc()).paginate(
        page=page, per_page=20, error_out=False
    )
    
    # Get users for filter dropdown (only for Admin/Accountant)
    if current_user.role.name in ['Admin', 'Accountant']:
        users = User.query.filter(User.role.has(name__in=['Admin', 'Accountant'])).order_by(User.first_name).all()
    else:
        users = []
    
    return render_template('tasks/index.html', 
                         tasks=tasks, 
                         status=status, 
                         priority=priority,
                         task_type=task_type,
                         assigned_to=assigned_to,
                         users=users)

@tasks_bp.route('/add', methods=['GET', 'POST'])
@login_required
def add():
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to create tasks.', 'error')
        return redirect(url_for('tasks.index'))
    
    form = TaskForm()
    
    # Populate choices
    users = User.query.filter(User.role.has(name__in=['Admin', 'Accountant'])).order_by(User.first_name).all()
    form.assigned_to.choices = [('', 'Unassigned')] + [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    
    clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
    form.client_id.choices = [('', 'No Client')] + [(c.id, c.name) for c in clients]
    
    if form.validate_on_submit():
        task = Task(
            title=form.title.data,
            description=form.description.data,
            due_date=form.due_date.data,
            priority=form.priority.data,
            status=form.status.data,
            task_type=form.task_type.data,
            assigned_to=form.assigned_to.data if form.assigned_to.data else None,
            client_id=form.client_id.data if form.client_id.data else None,
            created_by=current_user.id
        )
        
        db.session.add(task)
        db.session.commit()
        
        flash('Task created successfully!', 'success')
        return redirect(url_for('tasks.view', id=task.id))
    
    return render_template('tasks/form.html', form=form, title='Create Task')

@tasks_bp.route('/<int:id>')
@login_required
def view(id):
    task = Task.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client or task.client_id != client.id:
            flash('You do not have permission to view this task.', 'error')
            return redirect(url_for('tasks.index'))
    elif current_user.role.name == 'Accountant':
        if task.assigned_to != current_user.id and task.created_by != current_user.id:
            flash('You do not have permission to view this task.', 'error')
            return redirect(url_for('tasks.index'))
    
    return render_template('tasks/view.html', task=task)

@tasks_bp.route('/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit(id):
    task = Task.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Accountant' and task.created_by != current_user.id:
        flash('You can only edit tasks you created.', 'error')
        return redirect(url_for('tasks.view', id=id))
    elif current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to edit tasks.', 'error')
        return redirect(url_for('tasks.view', id=id))
    
    form = TaskForm(obj=task)
    
    # Populate choices
    users = User.query.filter(User.role.has(name__in=['Admin', 'Accountant'])).order_by(User.first_name).all()
    form.assigned_to.choices = [('', 'Unassigned')] + [(u.id, f"{u.first_name} {u.last_name}") for u in users]
    
    clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
    form.client_id.choices = [('', 'No Client')] + [(c.id, c.name) for c in clients]
    
    if form.validate_on_submit():
        form.populate_obj(task)
        
        # Set completion date if status changed to Completed
        if form.status.data == 'Completed' and task.status != 'Completed':
            task.completed_at = datetime.utcnow()
        elif form.status.data != 'Completed':
            task.completed_at = None
        
        # Handle empty values for foreign keys
        task.assigned_to = form.assigned_to.data if form.assigned_to.data else None
        task.client_id = form.client_id.data if form.client_id.data else None
        
        db.session.commit()
        
        flash('Task updated successfully!', 'success')
        return redirect(url_for('tasks.view', id=task.id))
    
    return render_template('tasks/form.html', form=form, task=task, title='Edit Task')

@tasks_bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete(id):
    task = Task.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Accountant' and task.created_by != current_user.id:
        flash('You can only delete tasks you created.', 'error')
        return redirect(url_for('tasks.view', id=id))
    elif current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to delete tasks.', 'error')
        return redirect(url_for('tasks.view', id=id))
    
    try:
        db.session.delete(task)
        db.session.commit()
        
        flash('Task deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting task. Please try again.', 'error')
    
    return redirect(url_for('tasks.index'))

@tasks_bp.route('/<int:id>/complete', methods=['POST'])
@login_required
def mark_complete(id):
    task = Task.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client':
        flash('You do not have permission to complete tasks.', 'error')
        return redirect(url_for('tasks.view', id=id))
    elif current_user.role.name == 'Accountant':
        if task.assigned_to != current_user.id and task.created_by != current_user.id:
            flash('You can only complete tasks assigned to you or created by you.', 'error')
            return redirect(url_for('tasks.view', id=id))
    
    task.status = 'Completed'
    task.completed_at = datetime.utcnow()
    
    db.session.commit()
    
    flash('Task marked as completed!', 'success')
    return redirect(url_for('tasks.view', id=id))

@tasks_bp.route('/dashboard')
@login_required
def dashboard():
    """Task dashboard with upcoming deadlines and overdue tasks"""
    today = date.today()
    
    # Base query filters based on user role
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            base_filter = Task.client_id == client.id
        else:
            base_filter = Task.client_id == -1  # No results
    elif current_user.role.name == 'Accountant':
        base_filter = (Task.assigned_to == current_user.id) | (Task.created_by == current_user.id)
    else:
        base_filter = True
    
    # Overdue tasks
    overdue_tasks = Task.query.filter(
        base_filter,
        Task.due_date < today,
        Task.status != 'Completed'
    ).order_by(Task.due_date.asc()).all()
    
    # Due today
    due_today = Task.query.filter(
        base_filter,
        Task.due_date == today,
        Task.status != 'Completed'
    ).order_by(Task.priority.desc()).all()
    
    # Due this week
    week_end = today + timedelta(days=7)
    due_this_week = Task.query.filter(
        base_filter,
        Task.due_date > today,
        Task.due_date <= week_end,
        Task.status != 'Completed'
    ).order_by(Task.due_date.asc()).all()
    
    # High priority tasks
    high_priority = Task.query.filter(
        base_filter,
        Task.priority == 'High',
        Task.status != 'Completed'
    ).order_by(Task.due_date.asc().nullslast()).all()
    
    return render_template('tasks/dashboard.html',
                         overdue_tasks=overdue_tasks,
                         due_today=due_today,
                         due_this_week=due_this_week,
                         high_priority=high_priority)
