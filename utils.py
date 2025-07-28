import os
import uuid
from datetime import datetime, date
from decimal import Decimal
from werkzeug.utils import secure_filename
from flask import current_app
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
import csv
from io import StringIO, BytesIO

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def save_uploaded_file(file, upload_folder='uploads'):
    """Save uploaded file with unique filename"""
    if file and file.filename:
        # Create uploads directory if it doesn't exist
        upload_path = os.path.join(current_app.root_path, upload_folder)
        os.makedirs(upload_path, exist_ok=True)
        
        # Generate unique filename
        filename = secure_filename(file.filename)
        name, ext = os.path.splitext(filename)
        unique_filename = f"{name}_{uuid.uuid4().hex}{ext}"
        
        # Save file
        file_path = os.path.join(upload_path, unique_filename)
        file.save(file_path)
        
        return unique_filename, filename, file_path
    return None, None, None

def calculate_vat(subtotal, vat_rate=15.0):
    """Calculate VAT amount and total"""
    subtotal = Decimal(str(subtotal))
    vat_rate = Decimal(str(vat_rate))
    
    vat_amount = subtotal * (vat_rate / 100)
    total_amount = subtotal + vat_amount
    
    return vat_amount, total_amount

def calculate_zakat(assets, liabilities, nisab_threshold=85 * 595.05):
    """
    Calculate Zakat according to Saudi rules
    Default nisab threshold is 85 grams of gold (approximately 50,505 SAR as of 2024)
    Zakat rate is 2.5% of net wealth above nisab
    """
    assets = Decimal(str(assets))
    liabilities = Decimal(str(liabilities))
    nisab = Decimal(str(nisab_threshold))
    
    net_wealth = assets - liabilities
    
    if net_wealth >= nisab:
        zakat_due = net_wealth * Decimal('0.025')  # 2.5%
    else:
        zakat_due = Decimal('0')
    
    return net_wealth, zakat_due, nisab

def generate_invoice_pdf(invoice):
    """Generate PDF for invoice"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    story.append(Paragraph(f"Invoice #{invoice.invoice_number}", title_style))
    
    # Invoice details
    details_data = [
        ['Invoice Number:', invoice.invoice_number],
        ['Issue Date:', invoice.issue_date.strftime('%Y-%m-%d')],
        ['Due Date:', invoice.due_date.strftime('%Y-%m-%d') if invoice.due_date else 'N/A'],
        ['Client:', invoice.client.name],
        ['Status:', invoice.status],
    ]
    
    details_table = Table(details_data, colWidths=[2*inch, 3*inch])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(details_table)
    story.append(Spacer(1, 20))
    
    # Invoice items
    if invoice.items.count() > 0:
        items_data = [['Description', 'Quantity', 'Unit Price', 'Total']]
        for item in invoice.items:
            items_data.append([
                str(item.description),
                str(item.quantity),
                f"{item.unit_price:.2f} SAR",
                f"{item.total_price:.2f} SAR"
            ])
        
        items_table = Table(items_data, colWidths=[3*inch, 1*inch, 1.5*inch, 1.5*inch])
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(items_table)
        story.append(Spacer(1, 20))
    
    # Totals
    totals_data = [
        ['Subtotal:', f"{invoice.subtotal:.2f} SAR"],
        ['VAT (15%):', f"{invoice.vat_amount:.2f} SAR"],
        ['Total Amount:', f"{invoice.total_amount:.2f} SAR"],
    ]
    
    totals_table = Table(totals_data, colWidths=[2*inch, 2*inch])
    totals_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(totals_table)
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_vat_report_pdf(vat_calculation):
    """Generate PDF for VAT calculation report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    story.append(Paragraph("VAT Calculation Report", title_style))
    
    # Report details
    details_data = [
        ['Period:', f"{vat_calculation.period_start.strftime('%Y-%m-%d')} to {vat_calculation.period_end.strftime('%Y-%m-%d')}"],
        ['Client:', vat_calculation.client.name if vat_calculation.client else 'N/A'],
        ['Total Sales:', f"{vat_calculation.total_sales:.2f} SAR"],
        ['Total Purchases:', f"{vat_calculation.total_purchases:.2f} SAR"],
        ['Output VAT (15%):', f"{vat_calculation.output_vat:.2f} SAR"],
        ['Input VAT (15%):', f"{vat_calculation.input_vat:.2f} SAR"],
        ['Net VAT Due:', f"{vat_calculation.net_vat:.2f} SAR"],
        ['Status:', vat_calculation.status],
    ]
    
    details_table = Table(details_data, colWidths=[2*inch, 3*inch])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(details_table)
    
    if vat_calculation.notes:
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Notes:</b> {vat_calculation.notes}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def generate_zakat_report_pdf(zakat_calculation):
    """Generate PDF for Zakat calculation report"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        alignment=TA_CENTER,
        spaceAfter=30
    )
    story.append(Paragraph("Zakat Calculation Report", title_style))
    
    # Report details
    details_data = [
        ['Hijri Year:', zakat_calculation.hijri_year],
        ['Client:', zakat_calculation.client.name if zakat_calculation.client else 'N/A'],
        ['Cash and Deposits:', f"{zakat_calculation.cash_and_deposits:.2f} SAR"],
        ['Trade Goods:', f"{zakat_calculation.trade_goods:.2f} SAR"],
        ['Receivables:', f"{zakat_calculation.receivables:.2f} SAR"],
        ['Investments:', f"{zakat_calculation.investments:.2f} SAR"],
        ['Total Assets:', f"{zakat_calculation.total_assets:.2f} SAR"],
        ['Liabilities:', f"{zakat_calculation.liabilities:.2f} SAR"],
        ['Net Wealth:', f"{zakat_calculation.net_wealth:.2f} SAR"],
        ['Nisab Threshold:', f"{zakat_calculation.nisab_threshold:.2f} SAR"],
        ['Zakat Due (2.5%):', f"{zakat_calculation.zakat_due:.2f} SAR"],
        ['Status:', zakat_calculation.status],
    ]
    
    details_table = Table(details_data, colWidths=[2*inch, 3*inch])
    details_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    story.append(details_table)
    
    if zakat_calculation.notes:
        story.append(Spacer(1, 20))
        story.append(Paragraph(f"<b>Notes:</b> {zakat_calculation.notes}", styles['Normal']))
    
    doc.build(story)
    buffer.seek(0)
    return buffer

def export_to_csv(data, columns):
    """Export data to CSV format"""
    output = StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow(columns)
    
    # Write data
    for row in data:
        writer.writerow(row)
    
    output.seek(0)
    return output.getvalue()

def format_currency(amount, currency='SAR'):
    """Format currency amount"""
    if amount is None:
        return f"0.00 {currency}"
    return f"{amount:.2f} {currency}"

def get_current_hijri_year():
    """Get current Hijri year (approximate)"""
    current_year = datetime.now().year
    hijri_year = current_year - 622 + 1  # Approximate conversion
    return f"{hijri_year}H"
