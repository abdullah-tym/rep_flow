from flask import Blueprint, render_template, request, redirect, url_for, flash, make_response, jsonify
from flask_login import login_required, current_user
from app import db
from models import VATCalculation, ZakatCalculation, Client
from forms import VATCalculationForm, ZakatCalculationForm
from utils import calculate_vat, calculate_zakat, generate_vat_report_pdf, generate_zakat_report_pdf, get_current_hijri_year
from decimal import Decimal

vat_zakat_bp = Blueprint('vat_zakat', __name__)

@vat_zakat_bp.route('/')
@login_required
def index():
    # Get VAT calculations
    vat_query = VATCalculation.query
    zakat_query = ZakatCalculation.query
    
    # Apply filters based on user role
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            vat_query = vat_query.filter_by(client_id=client.id)
            zakat_query = zakat_query.filter_by(client_id=client.id)
        else:
            vat_query = vat_query.filter_by(client_id=-1)  # No results
            zakat_query = zakat_query.filter_by(client_id=-1)  # No results
    
    vat_calculations = vat_query.order_by(VATCalculation.created_at.desc()).limit(10).all()
    zakat_calculations = zakat_query.order_by(ZakatCalculation.created_at.desc()).limit(10).all()
    
    return render_template('vat_zakat/index.html', 
                         vat_calculations=vat_calculations,
                         zakat_calculations=zakat_calculations)

@vat_zakat_bp.route('/vat/calculate', methods=['GET', 'POST'])
@login_required
def vat_calculate():
    form = VATCalculationForm()
    
    # Populate client choices for Admin/Accountant
    if current_user.role.name in ['Admin', 'Accountant']:
        clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
        form.client_id.choices = [('', 'Select Client')] + [(c.id, c.name) for c in clients]
    else:
        # For clients, pre-select their own data
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            form.client_id.choices = [(client.id, client.name)]
            form.client_id.data = client.id
        else:
            form.client_id.choices = []
    
    if form.validate_on_submit():
        # Calculate VAT amounts
        output_vat = form.total_sales.data * Decimal('0.15')  # 15% VAT on sales
        input_vat = form.total_purchases.data * Decimal('0.15')  # 15% VAT on purchases
        net_vat = output_vat - input_vat
        
        vat_calculation = VATCalculation(
            client_id=form.client_id.data if form.client_id.data else None,
            period_start=form.period_start.data,
            period_end=form.period_end.data,
            total_sales=form.total_sales.data,
            total_purchases=form.total_purchases.data,
            output_vat=output_vat,
            input_vat=input_vat,
            net_vat=net_vat,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        db.session.add(vat_calculation)
        db.session.commit()
        
        flash('VAT calculation completed successfully!', 'success')
        return redirect(url_for('vat_zakat.vat_view', id=vat_calculation.id))
    
    return render_template('vat_zakat/vat_calculate.html', form=form)

@vat_zakat_bp.route('/vat/<int:id>')
@login_required
def vat_view(id):
    vat_calculation = VATCalculation.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client or (vat_calculation.client_id and vat_calculation.client_id != client.id):
            flash('You do not have permission to view this VAT calculation.', 'error')
            return redirect(url_for('vat_zakat.index'))
    
    return render_template('vat_zakat/vat_view.html', calculation=vat_calculation)

@vat_zakat_bp.route('/vat/<int:id>/pdf')
@login_required
def vat_pdf(id):
    vat_calculation = VATCalculation.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client or (vat_calculation.client_id and vat_calculation.client_id != client.id):
            flash('You do not have permission to download this VAT report.', 'error')
            return redirect(url_for('vat_zakat.index'))
    
    pdf_buffer = generate_vat_report_pdf(vat_calculation)
    
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=vat_report_{id}.pdf'
    
    return response

@vat_zakat_bp.route('/vat/<int:id>/submit', methods=['POST'])
@login_required
def vat_submit(id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to submit VAT calculations.', 'error')
        return redirect(url_for('vat_zakat.vat_view', id=id))
    
    vat_calculation = VATCalculation.query.get_or_404(id)
    vat_calculation.status = 'Submitted'
    
    db.session.commit()
    
    flash('VAT calculation submitted successfully!', 'success')
    return redirect(url_for('vat_zakat.vat_view', id=id))

@vat_zakat_bp.route('/zakat/calculate', methods=['GET', 'POST'])
@login_required
def zakat_calculate():
    form = ZakatCalculationForm()
    
    # Populate client choices for Admin/Accountant
    if current_user.role.name in ['Admin', 'Accountant']:
        clients = Client.query.filter_by(status='Active').order_by(Client.name).all()
        form.client_id.choices = [('', 'Select Client')] + [(c.id, c.name) for c in clients]
    else:
        # For clients, pre-select their own data
        client = Client.query.filter_by(created_by=current_user.id).first()
        if client:
            form.client_id.choices = [(client.id, client.name)]
            form.client_id.data = client.id
        else:
            form.client_id.choices = []
    
    # Set default Hijri year
    if not form.hijri_year.data:
        form.hijri_year.data = get_current_hijri_year()
    
    if form.validate_on_submit():
        # Calculate total assets
        total_assets = (form.cash_and_deposits.data + 
                       form.trade_goods.data + 
                       form.receivables.data + 
                       form.investments.data)
        
        # Calculate Zakat
        net_wealth, zakat_due, nisab_threshold = calculate_zakat(
            total_assets, 
            form.liabilities.data
        )
        
        zakat_calculation = ZakatCalculation(
            client_id=form.client_id.data if form.client_id.data else None,
            hijri_year=form.hijri_year.data,
            cash_and_deposits=form.cash_and_deposits.data,
            trade_goods=form.trade_goods.data,
            receivables=form.receivables.data,
            investments=form.investments.data,
            total_assets=total_assets,
            liabilities=form.liabilities.data,
            net_wealth=net_wealth,
            zakat_due=zakat_due,
            nisab_threshold=nisab_threshold,
            notes=form.notes.data,
            created_by=current_user.id
        )
        
        db.session.add(zakat_calculation)
        db.session.commit()
        
        flash('Zakat calculation completed successfully!', 'success')
        return redirect(url_for('vat_zakat.zakat_view', id=zakat_calculation.id))
    
    return render_template('vat_zakat/zakat_calculate.html', form=form)

@vat_zakat_bp.route('/zakat/<int:id>')
@login_required
def zakat_view(id):
    zakat_calculation = ZakatCalculation.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client or (zakat_calculation.client_id and zakat_calculation.client_id != client.id):
            flash('You do not have permission to view this Zakat calculation.', 'error')
            return redirect(url_for('vat_zakat.index'))
    
    return render_template('vat_zakat/zakat_view.html', calculation=zakat_calculation)

@vat_zakat_bp.route('/zakat/<int:id>/pdf')
@login_required
def zakat_pdf(id):
    zakat_calculation = ZakatCalculation.query.get_or_404(id)
    
    # Check permissions
    if current_user.role.name == 'Client':
        client = Client.query.filter_by(created_by=current_user.id).first()
        if not client or (zakat_calculation.client_id and zakat_calculation.client_id != client.id):
            flash('You do not have permission to download this Zakat report.', 'error')
            return redirect(url_for('vat_zakat.index'))
    
    pdf_buffer = generate_zakat_report_pdf(zakat_calculation)
    
    response = make_response(pdf_buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=zakat_report_{id}.pdf'
    
    return response

@vat_zakat_bp.route('/zakat/<int:id>/submit', methods=['POST'])
@login_required
def zakat_submit(id):
    if current_user.role.name not in ['Admin', 'Accountant']:
        flash('You do not have permission to submit Zakat calculations.', 'error')
        return redirect(url_for('vat_zakat.zakat_view', id=id))
    
    zakat_calculation = ZakatCalculation.query.get_or_404(id)
    zakat_calculation.status = 'Submitted'
    
    db.session.commit()
    
    flash('Zakat calculation submitted successfully!', 'success')
    return redirect(url_for('vat_zakat.zakat_view', id=id))

# API Routes for calculation endpoints
@vat_zakat_bp.route('/api/vat/calculate', methods=['POST'])
@login_required
def api_vat_calculate():
    """API endpoint for VAT calculation"""
    try:
        data = request.get_json()
        revenue = Decimal(str(data.get('revenue', 0)))
        
        # Calculate 15% VAT on revenue
        vat_amount = revenue * Decimal('0.15')
        
        return jsonify({
            'success': True,
            'revenue': float(revenue),
            'vat_rate': 15.0,
            'vat_amount': float(vat_amount),
            'total_with_vat': float(revenue + vat_amount)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

@vat_zakat_bp.route('/api/zakat/calculate', methods=['POST'])
@login_required
def api_zakat_calculate():
    """API endpoint for Zakat calculation"""
    try:
        data = request.get_json()
        assets = Decimal(str(data.get('assets', 0)))
        liabilities = Decimal(str(data.get('liabilities', 0)))
        
        net_wealth, zakat_due, nisab_threshold = calculate_zakat(assets, liabilities)
        
        return jsonify({
            'success': True,
            'assets': float(assets),
            'liabilities': float(liabilities),
            'net_wealth': float(net_wealth),
            'nisab_threshold': float(nisab_threshold),
            'zakat_due': float(zakat_due),
            'eligible_for_zakat': net_wealth >= nisab_threshold
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
