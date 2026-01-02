"""
Authentication Routes Blueprint
Handles login, logout, and user registration
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app.models import User, Profile
from app import db
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login page"""
    # Redirect if already logged in
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False) == 'on'
        
        if not email or not password:
            flash('Por favor ingresa email y contraseña', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.active:
                flash('Tu cuenta está desactivada. Contacta al administrador.', 'error')
                return render_template('auth/login.html')
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            login_user(user, remember=remember)
            flash(f'¡Bienvenido, {user.name}!', 'success')
            
            # Redirect to next page or home
            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.index'))
        else:
            flash('Email o contraseña incorrectos', 'error')
    
    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """Logout user"""
    logout_user()
    flash('Has cerrado sesión correctamente', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
@login_required
def register():
    """Register new user (admin only)"""
    # Only admins can register users
    if not current_user.is_admin:
        flash('No tienes permisos para registrar usuarios', 'error')
        return redirect(url_for('main.index'))
    
    profiles = Profile.query.all()
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        name = request.form.get('name', '').strip()
        password = request.form.get('password', '')
        profile_id = request.form.get('profile_id')
        
        # Validation
        if not email or not name or not password:
            flash('Todos los campos son requeridos', 'error')
            return render_template('auth/register.html', profiles=profiles)
        
        # Check if email exists
        if User.query.filter_by(email=email).first():
            flash('El email ya está registrado', 'error')
            return render_template('auth/register.html', profiles=profiles)
        
        # Create user
        user = User(
            email=email,
            name=name,
            profile_id=int(profile_id) if profile_id else None
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash(f'Usuario {name} creado exitosamente', 'success')
        return redirect(url_for('admin.users'))
    
    return render_template('auth/register.html', profiles=profiles)
