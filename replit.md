# Accounting SaaS Application

## Overview

This is a comprehensive Saudi Arabia-focused accounting Software as a Service (SaaS) application built with Flask. The system provides multi-tenant capabilities for managing clients, invoices, VAT calculations, Zakat calculations, tasks, and financial reporting. It's specifically designed to comply with Saudi Arabian accounting regulations and supports both Arabic and English languages.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
The application follows a modular Flask architecture with clear separation of concerns:
- **Flask Application Factory Pattern**: The app is created using the factory pattern in `app.py`
- **Blueprint-based Modular Design**: Features are organized into separate blueprints (auth, clients, invoices, reports, etc.)
- **SQLAlchemy ORM**: Uses Flask-SQLAlchemy with a declarative base for database operations
- **Form Handling**: WTForms integration for secure form processing and validation
- **Authentication**: Flask-Login for session management and user authentication

### Frontend Architecture
- **Server-Side Rendered Templates**: Jinja2 templates with Bootstrap 5 for responsive UI
- **Progressive Enhancement**: JavaScript enhances functionality without being required
- **Component-based Templates**: Base template with block inheritance for consistent layout
- **Static Asset Management**: CSS and JavaScript files organized in the static directory

### Database Design
The system uses PostgreSQL as the primary database with the following key entities:
- **Users and Roles**: Role-based access control (Admin, Accountant, Client)
- **Clients**: Multi-tenant client management with Arabic/English support
- **Invoices and Invoice Items**: Comprehensive invoicing with VAT calculations
- **Tasks**: Task management system for accounting workflows
- **VAT/Zakat Calculations**: Specialized modules for Saudi tax compliance
- **Company Settings**: Configurable company information and branding

## Key Components

### Authentication System
- Role-based access control with three main roles: Admin, Accountant, and Client
- Secure password hashing using Werkzeug
- Session management with Flask-Login
- Registration and login forms with CSRF protection

### Client Management
- Multi-language support (Arabic and English names/addresses)
- CR (Commercial Registration) and VAT number tracking
- Document upload and management capabilities
- Status tracking (Active, Closed, Archived)

### Invoice Management
- Professional invoice generation with PDF export
- Line item management with quantity, unit price, and totals
- VAT calculation integration (15% Saudi VAT rate)
- Multiple payment status tracking
- Invoice numbering system

### VAT and Zakat Calculations
- Saudi VAT compliance (15% standard rate)
- Islamic Zakat calculations with Nisab threshold
- Period-based reporting for tax submissions
- PDF report generation for compliance
- Status tracking (Draft, Submitted, Paid)

### Task Management
- Priority-based task assignment
- Due date tracking with overdue notifications
- Task categorization (VAT Filing, Zakat Filing, General)
- Multi-user assignment capabilities

### Reporting System
- Revenue reports with client breakdowns
- VAT analysis and compliance reports
- Zakat reporting for Islamic compliance
- CSV export functionality
- Date range filtering

## Data Flow

### Authentication Flow
1. User submits credentials via login form
2. System validates against database using password hash comparison
3. Flask-Login creates secure session
4. Role-based permissions determine accessible features

### Invoice Processing
1. User creates invoice with client and line items
2. System calculates VAT automatically (15% rate)
3. PDF generation using ReportLab library
4. Status updates tracked through payment lifecycle

### Tax Calculation Workflow
1. User inputs financial data for specific periods
2. System applies Saudi tax rules (VAT/Zakat)
3. Calculations stored with draft status
4. Reports generated for submission to authorities
5. Status progression: Draft → Submitted → Paid

## External Dependencies

### Core Framework
- **Flask**: Web application framework
- **Flask-SQLAlchemy**: Database ORM
- **Flask-Login**: User session management
- **Flask-WTF**: Form handling and CSRF protection
- **Flask-Mail**: Email functionality

### UI and Frontend
- **Bootstrap 5**: CSS framework for responsive design
- **Font Awesome**: Icon library
- **jQuery**: JavaScript utility library (implied by templates)

### PDF Generation
- **ReportLab**: Professional PDF document generation
- Used for invoices, VAT reports, and Zakat calculations

### Database
- **PostgreSQL**: Primary database (configured via DATABASE_URL)
- **SQLAlchemy**: Database abstraction layer

### File Handling
- **Werkzeug**: File upload utilities and security
- Document storage in local filesystem

## Deployment Strategy

### Environment Configuration
- Environment variables for sensitive configuration
- Database URL configuration for different environments
- Mail server configuration for notifications
- Session secret key management

### Production Considerations
- ProxyFix middleware for reverse proxy deployment
- Connection pooling with pool_recycle and pool_pre_ping
- File upload size limits (16MB maximum)
- CSRF protection enabled globally

### Database Management
- SQLAlchemy migrations support (implied by model structure)
- Declarative base for clean schema management
- Foreign key relationships for data integrity

### Security Features
- Password hashing with Werkzeug security utilities
- CSRF protection on all forms
- Role-based access control throughout application
- Secure file upload with extension validation
- Session management with configurable secret keys

The application is designed to be deployed on platforms like Replit, Heroku, or traditional VPS with minimal configuration changes needed.