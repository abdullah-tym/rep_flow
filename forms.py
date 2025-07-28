from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, DateField, DecimalField, IntegerField, BooleanField, PasswordField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, EqualTo
from datetime import date
from decimal import Decimal

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Password', validators=[DataRequired()])

class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=64)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = SelectField('Role', choices=[('Accountant', 'Accountant'), ('Client', 'Client')], validators=[DataRequired()])

class ClientForm(FlaskForm):
    name = StringField('Company Name (English)', validators=[DataRequired(), Length(max=255)])
    name_ar = StringField('Company Name (Arabic)', validators=[Optional(), Length(max=255)])
    email = StringField('Email', validators=[Optional(), Email()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    cr_number = StringField('CR Number', validators=[Optional(), Length(max=50)])
    vat_number = StringField('VAT Number', validators=[Optional(), Length(max=50)])
    address = TextAreaField('Address (English)', validators=[Optional()])
    address_ar = TextAreaField('Address (Arabic)', validators=[Optional()])
    status = SelectField('Status', choices=[('Active', 'Active'), ('Closed', 'Closed'), ('Archived', 'Archived')], default='Active')

class InvoiceForm(FlaskForm):
    client_id = SelectField('Client', coerce=int, validators=[DataRequired()])
    invoice_number = StringField('Invoice Number', validators=[DataRequired(), Length(max=50)])
    issue_date = DateField('Issue Date', validators=[DataRequired()], default=date.today)
    due_date = DateField('Due Date', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])
    subtotal = DecimalField('Subtotal (SAR)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    vat_rate = DecimalField('VAT Rate (%)', validators=[DataRequired(), NumberRange(min=0, max=100)], default=Decimal('15.00'), places=2)
    status = SelectField('Status', choices=[('Unpaid', 'Unpaid'), ('Paid', 'Paid'), ('Overdue', 'Overdue')], default='Unpaid')
    payment_date = DateField('Payment Date', validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])

class InvoiceItemForm(FlaskForm):
    description = TextAreaField('Description', validators=[DataRequired()])
    quantity = DecimalField('Quantity', validators=[DataRequired(), NumberRange(min=0)], places=2)
    unit_price = DecimalField('Unit Price (SAR)', validators=[DataRequired(), NumberRange(min=0)], places=2)

class TaskForm(FlaskForm):
    title = StringField('Task Title', validators=[DataRequired(), Length(max=255)])
    description = TextAreaField('Description', validators=[Optional()])
    due_date = DateField('Due Date', validators=[Optional()])
    priority = SelectField('Priority', choices=[('High', 'High'), ('Medium', 'Medium'), ('Low', 'Low')], default='Medium')
    status = SelectField('Status', choices=[('Pending', 'Pending'), ('In Progress', 'In Progress'), ('Completed', 'Completed')], default='Pending')
    task_type = SelectField('Task Type', choices=[('VAT Filing', 'VAT Filing'), ('Zakat Filing', 'Zakat Filing'), ('General', 'General')], default='General')
    assigned_to = SelectField('Assign To', coerce=int, validators=[Optional()])
    client_id = SelectField('Client', coerce=int, validators=[Optional()])

class VATCalculationForm(FlaskForm):
    client_id = SelectField('Client', coerce=int, validators=[Optional()])
    period_start = DateField('Period Start', validators=[DataRequired()])
    period_end = DateField('Period End', validators=[DataRequired()])
    total_sales = DecimalField('Total Sales (SAR)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    total_purchases = DecimalField('Total Purchases (SAR)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    notes = TextAreaField('Notes', validators=[Optional()])

class ZakatCalculationForm(FlaskForm):
    client_id = SelectField('Client', coerce=int, validators=[Optional()])
    hijri_year = StringField('Hijri Year', validators=[DataRequired(), Length(max=10)])
    cash_and_deposits = DecimalField('Cash and Deposits (SAR)', validators=[DataRequired(), NumberRange(min=0)], default=Decimal('0'), places=2)
    trade_goods = DecimalField('Trade Goods (SAR)', validators=[DataRequired(), NumberRange(min=0)], default=Decimal('0'), places=2)
    receivables = DecimalField('Receivables (SAR)', validators=[DataRequired(), NumberRange(min=0)], default=Decimal('0'), places=2)
    investments = DecimalField('Investments (SAR)', validators=[DataRequired(), NumberRange(min=0)], default=Decimal('0'), places=2)
    liabilities = DecimalField('Liabilities (SAR)', validators=[DataRequired(), NumberRange(min=0)], default=Decimal('0'), places=2)
    notes = TextAreaField('Notes', validators=[Optional()])

class CompanySettingsForm(FlaskForm):
    name = StringField('Company Name (English)', validators=[DataRequired(), Length(max=255)])
    name_ar = StringField('Company Name (Arabic)', validators=[Optional(), Length(max=255)])
    cr_number = StringField('CR Number', validators=[Optional(), Length(max=50)])
    vat_number = StringField('VAT Number', validators=[Optional(), Length(max=50)])
    iban = StringField('IBAN', validators=[Optional(), Length(max=50)])
    address = TextAreaField('Address (English)', validators=[Optional()])
    address_ar = TextAreaField('Address (Arabic)', validators=[Optional()])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    email = StringField('Email', validators=[Optional(), Email()])
    logo = FileField('Company Logo', validators=[FileAllowed(['jpg', 'png', 'gif'], 'Images only!')])

class DocumentUploadForm(FlaskForm):
    file = FileField('Document', validators=[DataRequired(), FileAllowed(['pdf', 'doc', 'docx', 'xls', 'xlsx', 'jpg', 'png'], 'Invalid file type!')])
    description = TextAreaField('Description', validators=[Optional()])
