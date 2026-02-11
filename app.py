

import os
import csv
import io
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import re
import math
import json
from pymongo import MongoClient
from bson.objectid import ObjectId
from dotenv import load_dotenv
import bcrypt
try:
    from openai import OpenAI  # Optional: Used if OPENAI_API_KEY is set
except Exception:
    OpenAI = None

load_dotenv()

app = Flask(__name__)

# Provide a safe default secret key for development if not set
app.secret_key = os.getenv("SECRET_KEY") or "dev-secret-change-me"

# MongoDB client with sensible defaults and connectivity check
mongo_uri = os.getenv("MONGO_URI") or "mongodb://localhost:27017/freshflow"
try:
    client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
    # Trigger a server selection to fail fast if DB is unreachable
    client.admin.command("ping")
    db = client.freshflow
except Exception as db_init_error:
    # Defer crashing until first request; render helpful message instead
    client = None
    db = None
    print(f"[FreshFlow] MongoDB connection failed: {db_init_error}")

# Authentication decorator
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return wrapped

# Landing page
@app.route('/')
def landing():
    return render_template('landing.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = db.users.find_one({'username': request.form['username']})
        if user and bcrypt.checkpw(request.form['password'].encode(), user['password']):
            session['user_id'] = str(user['_id'])
            session['username'] = user['username']
            return redirect(url_for('dashboard'))
        flash('Invalid credentials', 'error')
    return render_template('auth/login.html')

# Signup route
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    roles = ['Admin', 'Manager', 'Warehouse Staff']
    if request.method == 'POST':
        # Basic validations and DB safety
        if db is None:
            flash('Database not connected. Please ensure MongoDB is running and MONGO_URI is set.', 'error')
            return redirect(url_for('signup'))

        form = request.form
        username = (form.get('username') or '').strip()
        email = (form.get('email') or '').strip()
        password = form.get('password') or ''
        role = form.get('role') or ''

        if not username or not email or not password or not role:
            flash('All fields are required.', 'error')
            return redirect(url_for('signup'))
        if role not in roles:
            flash('Invalid role selected.', 'error')
            return redirect(url_for('signup'))
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return redirect(url_for('signup'))

        try:
            if db.users.find_one({'username': username}):
                flash('Username taken', 'error')
                return redirect(url_for('signup'))
            hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            user_id = db.users.insert_one({
                'username': username,
                'email': email,
                'password': hashed,
                'role': role
            }).inserted_id
            session['user_id'] = str(user_id)
            session['username'] = username
            return redirect(url_for('dashboard'))
        except Exception as signup_error:
            flash(f'Signup failed: {signup_error}', 'error')
            return redirect(url_for('signup'))
    return render_template('auth/signup.html', roles=roles)

# Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('landing'))

# Dashboard
@app.route('/dashboard')
@login_required
def dashboard():
    today = datetime.now()
    next_week = today + timedelta(days=7)
    total = db.inventory.count_documents({})
    expiring = db.inventory.count_documents({
        'expiry_date': {'$lte': next_week.strftime('%Y-%m-%d')}
    })
    out_of_stock = db.inventory.count_documents({'quantity': 0})
    recent_items = list(db.inventory.find().sort('_id', -1).limit(5))
    # Pull currently active discount products (top 5)
    discount_products = list(db.discount_products.find({'status': 'active', 'quantity_available': {'$gt': 0}}).sort('start_date', -1).limit(5))

    stats = {
        'total': total,
        'expiring': expiring,
        'out': out_of_stock
    }
    # Smart discount recommendations (top 5)
    recs = list(db.discount_recommendations.find({'status': 'suggested'}).sort('created_at', -1).limit(5)) if db is not None else []
    return render_template('dashboard/index.html', stats=stats, recent=recent_items, today=today.strftime('%Y-%m-%d'), next_week=next_week.strftime('%Y-%m-%d'), discounts=discount_products, recommendations=recs)

# Chart data API
@app.route('/api/chart-data')
@login_required
def chart_data():
    today = datetime.now()
    next_week = today + timedelta(days=7)
    fresh = db.inventory.count_documents({
        'expiry_date': {'$gt': next_week.strftime('%Y-%m-%d')}
    })
    near = db.inventory.count_documents({
        'expiry_date': {'$gte': today.strftime('%Y-%m-%d'),
                        '$lte': next_week.strftime('%Y-%m-%d')}
    })
    expired = db.inventory.count_documents({
        'expiry_date': {'$lt': today.strftime('%Y-%m-%d')}
    })
    return jsonify({'fresh': fresh, 'near': near, 'expired': expired})

# Inventory Management Routes
@app.route('/inventory')
@login_required
def inventory():
    category = request.args.get('category', '')
    status = request.args.get('status', '')
    search = request.args.get('search', '')
    
    # Provide today and next_week strings for template date comparisons
    today_str = datetime.now().strftime('%Y-%m-%d')
    next_week_str = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')

    query = {}
    if category:
        query['category'] = category
    if search:
        query['name'] = {'$regex': search, '$options': 'i'}
    
    items = list(db.inventory.find(query).sort('name', 1))
    
    # Filter by status
    if status:
        today = datetime.now().strftime('%Y-%m-%d')
        next_week = (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        if status == 'fresh':
            items = [item for item in items if item['expiry_date'] > next_week]
        elif status == 'near_expiry':
            items = [item for item in items if item['expiry_date'] <= next_week and item['expiry_date'] >= today]
        elif status == 'expired':
            items = [item for item in items if item['expiry_date'] < today]
    
    categories = db.inventory.distinct('category')
    return render_template('dashboard/inventory.html', items=items, categories=categories, today=today_str, next_week=next_week_str)

@app.route('/inventory/add', methods=['GET', 'POST'])
@login_required
def add_item():
    if request.method == 'POST':
        item_data = {
            'name': request.form['name'],
            'category': request.form['category'],
            'quantity': int(request.form['quantity']),
            'expiry_date': request.form['expiry_date'],
            'supplier': request.form.get('supplier', ''),
            'cost': float(request.form.get('cost', 0)),
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        db.inventory.insert_one(item_data)
        flash('Item added successfully!', 'success')
        return redirect(url_for('inventory'))
    
    categories = ['Fruits', 'Vegetables', 'Dairy', 'Meat', 'Grains', 'Beverages', 'Snacks', 'Other']
    return render_template('dashboard/add_item.html', categories=categories)

@app.route('/inventory/edit/<item_id>', methods=['GET', 'POST'])
@login_required
def edit_item(item_id):
    item = db.inventory.find_one({'_id': ObjectId(item_id)})
    if not item:
        flash('Item not found!', 'error')
        return redirect(url_for('inventory'))
    
    if request.method == 'POST':
        update_data = {
            'name': request.form['name'],
            'category': request.form['category'],
            'quantity': int(request.form['quantity']),
            'expiry_date': request.form['expiry_date'],
            'supplier': request.form.get('supplier', ''),
            'cost': float(request.form.get('cost', 0)),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        db.inventory.update_one({'_id': ObjectId(item_id)}, {'$set': update_data})
        flash('Item updated successfully!', 'success')
        return redirect(url_for('inventory'))
    
    categories = ['Fruits', 'Vegetables', 'Dairy', 'Meat', 'Grains', 'Beverages', 'Snacks', 'Other']
    return render_template('dashboard/edit_item.html', item=item, categories=categories)

@app.route('/inventory/delete/<item_id>')
@login_required
def delete_item(item_id):
    db.inventory.delete_one({'_id': ObjectId(item_id)})
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('inventory'))

# CSV Upload Route
@app.route('/inventory/upload-csv', methods=['POST'])
@login_required
def upload_csv():
    if db is None:
        return jsonify({'success': False, 'error': 'Database not connected. Please ensure MongoDB is running.'}), 500
    
    if 'csv_file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['csv_file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'success': False, 'error': 'Invalid file type. Please upload a CSV file.'}), 400
    
    try:
        # Read CSV file using Python's built-in csv module
        file.stream.seek(0)
        stream = io.TextIOWrapper(file.stream, encoding='utf-8-sig')  # Handle BOM
        csv_reader = csv.DictReader(stream)
        
        # Expected column names mapping (case-insensitive and flexible)
        column_mapping = {
            'item name': 'name',
            'item_name': 'name',
            'name': 'name',
            'category': 'category',
            'quantity': 'quantity',
            'expiry date': 'expiry_date',
            'expiry_date': 'expiry_date',
            'expirydate': 'expiry_date',
            'supplier': 'supplier',
            'supplier cost': 'cost',
            'supplier_cost': 'cost',
            'cost': 'cost'
        }
        
        # Normalize and map CSV columns
        original_fieldnames = csv_reader.fieldnames
        if not original_fieldnames:
            return jsonify({'success': False, 'error': 'CSV file appears to be empty or invalid'}), 400
        
        normalized_fieldnames = [col.strip().lower().replace(' ', '_') for col in original_fieldnames]
        
        # Map columns to database fields
        required_fields = ['name', 'category', 'quantity', 'expiry_date']
        column_map = {}
        missing_fields = []
        
        # Find matching columns
        for db_field in required_fields:
            found = False
            for idx, norm_col in enumerate(normalized_fieldnames):
                if norm_col in column_mapping and column_mapping[norm_col] == db_field:
                    column_map[db_field] = original_fieldnames[idx]
                    found = True
                    break
            if not found:
                missing_fields.append(db_field)
        
        if missing_fields:
            return jsonify({
                'success': False, 
                'error': f'Missing required columns: {", ".join(missing_fields)}. Found columns: {", ".join(original_fieldnames)}'
            }), 400
        
        # Map optional columns
        optional_map = {}
        for idx, norm_col in enumerate(normalized_fieldnames):
            if norm_col in column_mapping:
                db_field = column_mapping[norm_col]
                if db_field in ['supplier', 'cost']:
                    optional_map[db_field] = original_fieldnames[idx]
        
        # Process rows in batches for efficiency
        BATCH_SIZE = 1000  # Process 1000 rows at a time for large files
        items_to_insert = []
        errors = []
        total_rows = 0
        successful_rows = 0
        
        # Process each row
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (row 1 is header)
            total_rows += 1
            
            try:
                # Extract and validate data
                item_data = {
                    'name': '',
                    'category': '',
                    'quantity': 0,
                    'expiry_date': '',
                    'supplier': '',
                    'cost': 0.0,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                # Get values from CSV row (handle missing columns)
                name_val = row.get(column_map['name'], '').strip() if column_map['name'] in row else ''
                category_val = row.get(column_map['category'], '').strip() if column_map['category'] in row else ''
                quantity_val = row.get(column_map['quantity'], '') if column_map['quantity'] in row else ''
                expiry_val = row.get(column_map['expiry_date'], '').strip() if column_map['expiry_date'] in row else ''
                
                # Validate and process name
                if not name_val:
                    raise ValueError(f"Row {row_num}: Item Name cannot be empty")
                item_data['name'] = name_val
                
                # Validate and process category
                if not category_val:
                    raise ValueError(f"Row {row_num}: Category cannot be empty")
                item_data['category'] = category_val
                
                # Validate and process quantity
                if not quantity_val:
                    raise ValueError(f"Row {row_num}: Quantity cannot be empty")
                try:
                    item_data['quantity'] = int(float(str(quantity_val)))
                    if item_data['quantity'] < 0:
                        raise ValueError(f"Row {row_num}: Quantity must be non-negative")
                except (ValueError, TypeError):
                    raise ValueError(f"Row {row_num}: Invalid quantity value: {quantity_val}")
                
                # Validate and process expiry date
                if not expiry_val:
                    raise ValueError(f"Row {row_num}: Expiry Date cannot be empty")
                
                # Try to parse date in various formats
                date_formats = ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%d-%m-%Y', '%Y/%m/%d', '%m/%d/%y', '%d/%m/%y', '%d.%m.%Y', '%Y.%m.%d']
                parsed_date = None
                date_str = str(expiry_val).strip()
                
                for fmt in date_formats:
                    try:
                        parsed_date = datetime.strptime(date_str, fmt)
                        break
                    except ValueError:
                        continue
                
                if parsed_date is None:
                    raise ValueError(f"Row {row_num}: Invalid date format: {date_str}. Supported formats: YYYY-MM-DD, DD/MM/YYYY, etc.")
                item_data['expiry_date'] = parsed_date.strftime('%Y-%m-%d')
                
                # Process supplier (optional)
                if 'supplier' in optional_map and optional_map['supplier'] in row:
                    supplier_val = row[optional_map['supplier']]
                    item_data['supplier'] = str(supplier_val).strip() if supplier_val else ''
                
                # Process cost (optional)
                if 'cost' in optional_map and optional_map['cost'] in row:
                    cost_val = row[optional_map['cost']]
                    try:
                        if cost_val:
                            item_data['cost'] = float(str(cost_val))
                            if item_data['cost'] < 0:
                                item_data['cost'] = 0.0
                    except (ValueError, TypeError):
                        item_data['cost'] = 0.0
                
                items_to_insert.append(item_data)
                successful_rows += 1
                
                # Insert in batches
                if len(items_to_insert) >= BATCH_SIZE:
                    try:
                        db.inventory.insert_many(items_to_insert, ordered=False)
                        items_to_insert = []
                    except Exception as batch_error:
                        errors.append(f"Batch insert error (rows {row_num-BATCH_SIZE+1}-{row_num}): {str(batch_error)}")
                        items_to_insert = []
                
            except Exception as row_error:
                errors.append(f"Row {row_num}: {str(row_error)}")
                continue
        
        # Insert remaining items
        if items_to_insert:
            try:
                db.inventory.insert_many(items_to_insert, ordered=False)
            except Exception as batch_error:
                errors.append(f"Final batch insert error: {str(batch_error)}")
        
        # Prepare response
        response = {
            'success': True,
            'total_rows': total_rows,
            'successful_rows': successful_rows,
            'failed_rows': len(errors),
            'errors': errors[:50] if len(errors) > 50 else errors  # Limit error messages
        }
        
        # Note: Flash messages won't work with JSON responses
        # Success/error messages are handled by JavaScript in the frontend
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Error processing CSV file: {str(e)}'}), 500

# Expiry Alerts Routes
@app.route('/expiry-alerts')
@login_required
def expiry_alerts():
    today = datetime.now()
    next_3_days = today + timedelta(days=3)
    next_week = today + timedelta(days=7)
    
    expired_items = list(db.inventory.find({
        'expiry_date': {'$lt': today.strftime('%Y-%m-%d')}
    }).sort('expiry_date', 1))
    
    critical_items = list(db.inventory.find({
        'expiry_date': {'$gte': today.strftime('%Y-%m-%d'), '$lte': next_3_days.strftime('%Y-%m-%d')}
    }).sort('expiry_date', 1))
    
    warning_items = list(db.inventory.find({
        'expiry_date': {'$gt': next_3_days.strftime('%Y-%m-%d'), '$lte': next_week.strftime('%Y-%m-%d')}
    }).sort('expiry_date', 1))
    
    return render_template('dashboard/expiry_alerts.html', 
                         expired=expired_items, 
                         critical=critical_items, 
                         warning=warning_items)

# Mid Sales Discount Route
@app.route('/mid-sale', methods=['GET', 'POST'])
@login_required
def mid_sale():
    if db is None:
        flash('Database not connected. Please ensure MongoDB is running.', 'error')
        return redirect(url_for('expiry_alerts'))
    
    item_id = request.args.get('item_id') or (request.form.get('item_id') if request.method == 'POST' else None)
    
    if not item_id:
        flash('No item selected for discount sale.', 'error')
        return redirect(url_for('expiry_alerts'))
    
    try:
        item = db.inventory.find_one({'_id': ObjectId(item_id)})
        if not item:
            flash('Item not found!', 'error')
            return redirect(url_for('expiry_alerts'))
        
        if request.method == 'POST':
            # Process the discount sale
            discount_percentage = request.form.get('discount_percentage', '0')
            discounted_price = request.form.get('discounted_price', '0')
            sale_quantity = request.form.get('sale_quantity', '0')
            sale_date = request.form.get('sale_date', datetime.now().strftime('%Y-%m-%d'))
            notes = request.form.get('notes', '')
            
            try:
                discount_pct = float(discount_percentage)
                discounted_price_val = float(discounted_price)
                sale_qty = int(float(sale_quantity))
                
                # Validate quantities
                today = datetime.now().strftime('%Y-%m-%d')
                
                if sale_qty > item['quantity']:
                    flash(f'Sale quantity ({sale_qty}) cannot exceed available quantity ({item["quantity"]})', 'error')
                    return render_template('dashboard/mid_sale.html', item=item, today=today)
                
                if sale_qty <= 0:
                    flash('Sale quantity must be greater than 0', 'error')
                    return render_template('dashboard/mid_sale.html', item=item, today=today)
                
                # Create sale record
                sale_record = {
                    'item_id': ObjectId(item_id),
                    'item_name': item['name'],
                    'item_category': item.get('category', ''),
                    'original_cost': float(item.get('cost', 0)),
                    'discount_percentage': discount_pct,
                    'discounted_price': discounted_price_val,
                    'sale_quantity': sale_qty,
                    'sale_date': sale_date,
                    'notes': notes,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': session.get('username', 'Unknown')
                }
                
                # Save sale record (create a sales collection if it doesn't exist)
                db.sales.insert_one(sale_record)

                # Upsert a discount product entry for availability in shop
                discount_doc = {
                    'inventory_id': ObjectId(item_id),
                    'name': item.get('name', ''),
                    'category': item.get('category', ''),
                    'original_cost': float(item.get('cost', 0)),
                    'discount_percentage': discount_pct,
                    'discounted_price': discounted_price_val,
                    'quantity_available': int(sale_qty),
                    'start_date': sale_date,
                    'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'created_by': session.get('username', 'Unknown'),
                    'status': 'active'
                }

                # If a discount already exists for the same inventory + price, increase quantity; else insert new
                existing = db.discount_products.find_one({
                    'inventory_id': ObjectId(item_id),
                    'discounted_price': discounted_price_val,
                    'status': 'active'
                })
                if existing:
                    db.discount_products.update_one(
                        {'_id': existing['_id']},
                        {'$inc': {'quantity_available': int(sale_qty)}, '$set': {'discount_percentage': discount_pct}}
                    )
                else:
                    db.discount_products.insert_one(discount_doc)

                # Update inventory quantity
                new_quantity = item['quantity'] - sale_qty
                db.inventory.update_one(
                    {'_id': ObjectId(item_id)},
                    {'$set': {'quantity': new_quantity}}
                )
                
                flash(f'Mid sales discount applied successfully! {sale_qty} units listed at {discount_pct}% discount.', 'success')
                return redirect(url_for('discount_product'))
                
            except ValueError as e:
                flash(f'Invalid input: {str(e)}', 'error')
                today = datetime.now().strftime('%Y-%m-%d')
                return render_template('dashboard/mid_sale.html', item=item, today=today)
        
        # GET request - show the discount form
        today = datetime.now().strftime('%Y-%m-%d')
        return render_template('dashboard/mid_sale.html', item=item, today=today)
        
    except Exception as e:
        flash(f'Error processing discount sale: {str(e)}', 'error')
        return redirect(url_for('expiry_alerts'))

# Analytics Routes
@app.route('/discount-product')
@login_required
def discount_product():
    if db is None:
        flash('Database not connected. Please ensure MongoDB is running.', 'error')
        return redirect(url_for('dashboard'))

    # Fetch active discount products
    items = list(db.discount_products.find({'status': 'active', 'quantity_available': {'$gt': 0}}).sort('start_date', -1))
    return render_template('dashboard/discount_product.html', items=items)

@app.route('/analytics')
@login_required
def analytics():
    # Calculate waste statistics
    today = datetime.now()
    last_month = today - timedelta(days=30)
    
    total_items = db.inventory.count_documents({})
    expired_items = db.inventory.count_documents({
        'expiry_date': {'$lt': today.strftime('%Y-%m-%d')}
    })
    
    waste_percentage = (expired_items / total_items * 100) if total_items > 0 else 0
    
    # Category-wise statistics
    categories = db.inventory.distinct('category')
    category_stats = []
    for category in categories:
        count = db.inventory.count_documents({'category': category})
        expired_count = db.inventory.count_documents({
            'category': category,
            'expiry_date': {'$lt': today.strftime('%Y-%m-%d')}
        })
        category_stats.append({
            'name': category,
            'total': count,
            'expired': expired_count,
            'waste_percentage': (expired_count / count * 100) if count > 0 else 0
        })
    
    return render_template('dashboard/analytics.html', 
                         total_items=total_items,
                         expired_items=expired_items,
                         waste_percentage=waste_percentage,
                         category_stats=category_stats)

# ---------------------------- Smart Discount Recommendations ----------------------------
def compute_discount_recommendations():
    """Compute heuristic discount recommendations and store them.
    This is a lightweight placeholder for ML. It focuses on near-expiry and slow-moving items.
    """
    if db is None:
        return 0

    today = datetime.now()
    next_week = today + timedelta(days=7)

    items = list(db.inventory.find({}))

    # Build sales rate map: sales in last 14 days by item_id
    fourteen_days_ago = (today - timedelta(days=14)).strftime('%Y-%m-%d')
    sales = list(db.sales.find({'sale_date': {'$gte': fourteen_days_ago}}))
    item_id_to_sales_qty = {}
    for s in sales:
        iid = str(s.get('item_id'))
        qty = int(s.get('sale_quantity', 0))
        item_id_to_sales_qty[iid] = item_id_to_sales_qty.get(iid, 0) + qty

    # Clear previous suggestions (optional: keep history)
    db.discount_recommendations.delete_many({'status': 'suggested'})

    created = 0
    for it in items:
        try:
            item_id = str(it.get('_id'))
            name = it.get('name', '')
            category = it.get('category', '')
            qty = int(it.get('quantity', 0))
            cost = float(it.get('cost', 0.0))
            expiry = it.get('expiry_date', '')

            # Parse expiry and compute days to expiry
            days_to_expiry = 999
            try:
                dt = datetime.strptime(str(expiry), '%Y-%m-%d')
                days_to_expiry = (dt - today).days
            except Exception:
                pass

            # Recent sales quantity
            recent_sales = item_id_to_sales_qty.get(item_id, 0)
            sales_rate = recent_sales / 14.0  # avg per day

            # Heuristic conditions
            near_expiry = days_to_expiry <= 7
            slow_moving = sales_rate < 0.5  # less than ~1 unit every 2 days
            overstock = qty >= 50

            if not (near_expiry or (slow_moving and overstock)):
                continue

            # Compute suggested discount percent
            base = 10.0
            if near_expiry:
                base += max(0, 8 - max(1, days_to_expiry)) * 5.0 / 7.0 * 10.0 / 10.0  # ~0-10% extra
            if slow_moving:
                base += 5.0
            if overstock:
                base += 5.0
            suggested_pct = max(5.0, min(50.0, round(base, 1)))

            suggested_price = max(0.0, round(cost * (1 - suggested_pct / 100.0), 2))
            reason = []
            if near_expiry:
                reason.append(f"near expiry: {days_to_expiry}d")
            if slow_moving:
                reason.append(f"slow sales: {sales_rate:.2f}/day")
            if overstock:
                reason.append(f"overstock: {qty} units")

            doc = {
                'inventory_id': ObjectId(item_id),
                'name': name,
                'category': category,
                'current_cost': cost,
                'quantity_available': qty,
                'suggested_discount_percentage': suggested_pct,
                'suggested_price': suggested_price,
                'reason': ", ".join(reason),
                'created_at': today.strftime('%Y-%m-%d %H:%M:%S'),
                'status': 'suggested'
            }
            db.discount_recommendations.insert_one(doc)
            created += 1
        except Exception:
            continue
    return created


@app.route('/api/recommend-discounts', methods=['POST'])
@login_required
def api_recommend_discounts():
    if db is None:
        return jsonify({'success': False, 'error': 'Database not connected'}), 500
    try:
        created = compute_discount_recommendations()
        return jsonify({'success': True, 'created': created})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
# ---------------------------- Chatbot Routes ----------------------------
@app.route('/chat')
@login_required
def chat():
    # Initialize minimal context store
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('dashboard/chat.html')


def _format_items_table(items, fields):
    lines = []
    header = " | ".join(fields)
    lines.append(header)
    lines.append("-" * len(header))
    for it in items[:20]:
        row = []
        for f in fields:
            row.append(str(it.get(f, '')))
        lines.append(" | ".join(row))
    return "\n".join(lines)


def _openai_summarize(system_prompt, user_prompt):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or OpenAI is None:
        return None
    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-4o-mini'),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        return completion.choices[0].message.content
    except Exception:
        return None


def _extract_quantity_and_name(text: str):
    text_low = text.lower()
    qty = None
    # Find first integer in text as quantity
    m = re.search(r"(-?\d+)", text_low)
    if m:
        try:
            qty = int(m.group(1))
        except Exception:
            qty = None
    # Try to extract item name after 'of' or 'for' or quotes
    name = None
    m2 = re.search(r"(?:of|for)\s+([\w\s-]{2,})", text_low)
    if m2:
        name = m2.group(1).strip()
    q = re.search(r"['\"]([^'\"]{1,64})['\"]", text)
    if q:
        name = q.group(1).strip()
    return qty, name


@app.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    if db is None:
        return jsonify({"reply": "Database not connected."}), 500

    try:
        data = request.get_json(silent=True) or {}
        user_msg = (data.get('message') or '').strip()
        if not user_msg:
            return jsonify({"reply": "Please type a message."}), 400

        # Keep short, sanitized history
        history = session.get('chat_history', [])[-10:]
        history.append({"role": "user", "content": user_msg})
        session['chat_history'] = history

        lower = user_msg.lower()
        today = datetime.now()
        next_week = today + timedelta(days=7)

        # Intent: Expiring soon
        if 'expiring' in lower or 'expire' in lower:
            items = list(db.inventory.find({
                'expiry_date': {'$gte': today.strftime('%Y-%m-%d'), '$lte': next_week.strftime('%Y-%m-%d')}
            }).sort('expiry_date', 1))
            if not items:
                reply = "No items expiring within the next 7 days."
            else:
                table = _format_items_table(items, ['name', 'category', 'quantity', 'expiry_date'])
                summary = _openai_summarize(
                    "You summarize inventory results briefly.",
                    f"User asked: {user_msg}\nTop results (name|category|quantity|expiry_date):\n{table}"
                )
                reply = summary or f"Items expiring within 7 days:\n{table}"
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})

        # Intent: Discount products
        if 'discount' in lower:
            items = list(db.discount_products.find({
                'status': 'active',
                'quantity_available': {'$gt': 0}
            }).sort('start_date', -1).limit(50))
            if not items:
                reply = "No active discount products right now."
            else:
                table = _format_items_table(items, ['name', 'category', 'discount_percentage', 'discounted_price', 'quantity_available'])
                summary = _openai_summarize(
                    "You summarize discount products briefly.",
                    f"User asked: {user_msg}\nDiscounts (name|category|discount_%|price|qty):\n{table}"
                )
                reply = summary or f"Current discount products:\n{table}"
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})

        # Intent: stock quantity query
        if 'stock' in lower or 'quantity' in lower:
            _, name = _extract_quantity_and_name(user_msg)
            if not name:
                # Try simpler extraction: words after 'of'
                name = user_msg
            item = db.inventory.find_one({'name': {'$regex': re.escape(name), '$options': 'i'}})
            if not item:
                reply = f"I couldn't find an item matching '{name}'."
            else:
                reply = f"{item.get('name', 'Item')}: quantity {item.get('quantity', 0)}, expiry {item.get('expiry_date', 'N/A')}, category {item.get('category', 'N/A')}."
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})

        # Intent: add/remove quantity
        if ('add' in lower or 'increase' in lower or 'remove' in lower or 'decrease' in lower) and ('quantity' in lower or 'stock' in lower):
            qty, name = _extract_quantity_and_name(user_msg)
            if not name:
                return jsonify({"reply": "Please specify the product name."}), 400
            item = db.inventory.find_one({'name': {'$regex': re.escape(name), '$options': 'i'}})
            if not item:
                return jsonify({"reply": f"I couldn't find an item matching '{name}'."}), 404
            if qty is None:
                return jsonify({"reply": "Please specify a valid quantity (e.g., add 5)."}), 400
            delta = qty if ('add' in lower or 'increase' in lower) else -abs(qty)
            new_q = max(0, int(item.get('quantity', 0)) + delta)
            db.inventory.update_one({'_id': item['_id']}, {'$set': {'quantity': new_q}})
            reply = f"Updated '{item.get('name')}' quantity to {new_q}."
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})

        # Default: use OpenAI to respond conversationally with guidance
        fallback = _openai_summarize(
            "You are an inventory assistant. If unclear, ask a concise follow-up.",
            user_msg
        ) or "I can help with expiring items, discounts, stock levels, and adjusting quantities. Try: 'Which products are expiring soon?'"
        session['chat_history'].append({"role": "assistant", "content": fallback})
        return jsonify({"reply": fallback})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500


# ---------------------------- Alternate Chatbot Routes (/chatbot) ----------------------------
@app.route('/chatbot')
@login_required
def chatbot_page():
    if 'chat_history' not in session:
        session['chat_history'] = []
    return render_template('dashboard/chatbot.html')


@app.route('/chatbot/message', methods=['POST'])
@login_required
def chatbot_message():
    if db is None:
        return jsonify({"reply": "Database not connected."}), 500

    try:
        data = request.get_json(silent=True) or {}
        user_msg = (data.get('message') or '').strip()
        if not user_msg:
            return jsonify({"reply": "Please type a message."}), 400

        history = session.get('chat_history', [])[-10:]
        history.append({"role": "user", "content": user_msg})
        session['chat_history'] = history

        lower = user_msg.lower()
        today = datetime.now()
        next_week = today + timedelta(days=7)

        # Expiring soon
        if 'expiring' in lower or 'expire' in lower:
            items = list(db.inventory.find({
                'expiry_date': {'$gte': today.strftime('%Y-%m-%d'), '$lte': next_week.strftime('%Y-%m-%d')}
            }).sort('expiry_date', 1))
            if not items:
                reply = "No items expiring within the next 7 days."
            else:
                table = _format_items_table(items, ['name', 'category', 'quantity', 'expiry_date'])
                summary = _openai_summarize(
                    "You summarize inventory results briefly.",
                    f"User asked: {user_msg}\nTop results (name|category|quantity|expiry_date):\n{table}"
                )
                reply = summary or f"Items expiring within 7 days:\n{table}"
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})

        # Discount products
        if 'discount' in lower:
            items = list(db.discount_products.find({
                'status': 'active',
                'quantity_available': {'$gt': 0}
            }).sort('start_date', -1).limit(50))
            if not items:
                reply = "No active discount products right now."
            else:
                table = _format_items_table(items, ['name', 'category', 'discount_percentage', 'discounted_price', 'quantity_available'])
                summary = _openai_summarize(
                    "You summarize discount products briefly.",
                    f"User asked: {user_msg}\nDiscounts (name|category|discount_%|price|qty):\n{table}"
                )
                reply = summary or f"Current discount products:\n{table}"
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})

        # Stock quantity query
        if 'stock' in lower or 'quantity' in lower:
            _, name = _extract_quantity_and_name(user_msg)
            if not name:
                name = user_msg
            item = db.inventory.find_one({'name': {'$regex': re.escape(name), '$options': 'i'}})
            if not item:
                reply = f"I couldn't find an item matching '{name}'."
            else:
                reply = f"{item.get('name', 'Item')}: quantity {item.get('quantity', 0)}, expiry {item.get('expiry_date', 'N/A')}, category {item.get('category', 'N/A')}."
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})

        # Add/remove quantity
        if ('add' in lower or 'increase' in lower or 'remove' in lower or 'decrease' in lower) and ('quantity' in lower or 'stock' in lower):
            qty, name = _extract_quantity_and_name(user_msg)
            if not name:
                return jsonify({"reply": "Please specify the product name."}), 400
            item = db.inventory.find_one({'name': {'$regex': re.escape(name), '$options': 'i'}})
            if not item:
                return jsonify({"reply": f"I couldn't find an item matching '{name}'."}), 404
            if qty is None:
                return jsonify({"reply": "Please specify a valid quantity (e.g., add 5)."}), 400
            delta = qty if ('add' in lower or 'increase' in lower) else -abs(qty)
            new_q = max(0, int(item.get('quantity', 0)) + delta)
            db.inventory.update_one({'_id': item['_id']}, {'$set': {'quantity': new_q}})
            reply = f"Updated '{item.get('name')}' quantity to {new_q}."
            session['chat_history'].append({"role": "assistant", "content": reply})
            return jsonify({"reply": reply})

        # Default fallback
        fallback = _openai_summarize(
            "You are an inventory assistant. If unclear, ask a concise follow-up.",
            user_msg
        ) or "I can help with expiring items, discounts, stock levels, and adjusting quantities. Try: 'Which products are expiring soon?'"
        session['chat_history'].append({"role": "assistant", "content": fallback})
        return jsonify({"reply": fallback})

    except Exception as e:
        return jsonify({"reply": f"Error: {str(e)}"}), 500

# Orders/Reorders Routes
@app.route('/orders')
@login_required
def orders():
    # Get low stock items for reorder suggestions
    low_stock_items = list(db.inventory.find({'quantity': {'$lte': 10}}).sort('quantity', 1))

    # Recent orders from DB
    recent_orders = list(db.orders.find().sort('created_at', -1).limit(20)) if db is not None else []
    # Normalize shape for template
    normalized_orders = []
    for o in recent_orders:
        normalized_orders.append({
            'id': str(o.get('_id')),
            'supplier': o.get('supplier', 'N/A'),
            'items': sum([int(i.get('quantity', 0)) for i in o.get('items', [])]),
            'total': float(o.get('total', 0.0)),
            'status': o.get('status', 'Pending'),
            'date': o.get('created_at', datetime.now().strftime('%Y-%m-%d'))
        })

    return render_template('dashboard/orders.html',
                         low_stock_items=low_stock_items,
                         recent_orders=normalized_orders)

@app.route('/orders/create', methods=['GET', 'POST'])
@login_required
def create_order():
    if db is None:
        flash('Database not connected. Please ensure MongoDB is running and MONGO_URI is set.', 'error')
        return redirect(url_for('orders'))

    if request.method == 'POST':
        supplier = (request.form.get('supplier') or '').strip()
        item_ids = request.form.getlist('item_id')
        quantities = request.form.getlist('quantity')

        items = []
        total = 0.0
        for idx, item_id in enumerate(item_ids):
            try:
                qty = max(0, int(quantities[idx]))
            except Exception:
                qty = 0
            inv = db.inventory.find_one({'_id': ObjectId(item_id)})
            if inv and qty > 0:
                cost = float(inv.get('cost', 0.0))
                items.append({
                    'inventory_id': ObjectId(item_id),
                    'name': inv.get('name', ''),
                    'category': inv.get('category', ''),
                    'unit_cost': cost,
                    'quantity': qty
                })
                total += cost * qty

        order_doc = {
            'supplier': supplier or 'N/A',
            'items': items,
            'total': round(total, 2),
            'status': 'Pending',
            'created_at': datetime.now().strftime('%Y-%m-%d')
        }
        db.orders.insert_one(order_doc)
        flash('Order created successfully!', 'success')
        return redirect(url_for('orders'))

    # GET: render order creation form
    low_stock_items = list(db.inventory.find({'quantity': {'$lte': 10}}).sort('quantity', 1))
    suppliers = [s for s in db.inventory.distinct('supplier') if s]
    return render_template('dashboard/create_order.html', low_stock_items=low_stock_items, suppliers=suppliers)

# Donations Routes
@app.route('/donations')
@login_required
def donations():
    today = datetime.now()
    next_week = today + timedelta(days=7)
    
    # Get items suitable for donation (expiring soon but not expired)
    donation_items = list(db.inventory.find({
        'expiry_date': {'$gte': today.strftime('%Y-%m-%d'), '$lte': next_week.strftime('%Y-%m-%d')}
    }).sort('expiry_date', 1))
    
    # NGO partners (placeholder data)
    ngo_partners = [
        {'name': 'Food Bank Foundation', 'contact': 'contact@foodbank.org', 'phone': '+1-555-0123'},
        {'name': 'Community Kitchen', 'contact': 'info@communitykitchen.org', 'phone': '+1-555-0456'},
        {'name': 'Hope Shelter', 'contact': 'donations@hopeshelter.org', 'phone': '+1-555-0789'}
    ]
    
    return render_template('dashboard/donations.html', 
                         donation_items=donation_items,
                         ngo_partners=ngo_partners)

@app.route('/donations/create', methods=['POST'])
@login_required
def create_donation():
    item_ids = request.form.getlist('item_ids')
    ngo_name = request.form['ngo_name']
    
    # Create donation record
    donation_data = {
        'ngo_name': ngo_name,
        'item_ids': [ObjectId(item_id) for item_id in item_ids],
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'Pending'
    }
    
    donation_id = db.donations.insert_one(donation_data).inserted_id
    
    # Update item status
    db.inventory.update_many(
        {'_id': {'$in': [ObjectId(item_id) for item_id in item_ids]}},
        {'$set': {'status': 'Donated', 'donation_id': donation_id}}
    )
    
    flash('Donation created successfully!', 'success')
    return redirect(url_for('donations'))

# Settings Routes
@app.route('/settings')
@login_required
def settings():
    users = list(db.users.find())
    return render_template('dashboard/settings.html', users=users)

@app.route('/settings/add-user', methods=['POST'])
@login_required
def add_user():
    form = request.form
    if db.users.find_one({'username': form['username']}):
        flash('Username already exists!', 'error')
        return redirect(url_for('settings'))
    
    hashed = bcrypt.hashpw(form['password'].encode(), bcrypt.gensalt())
    db.users.insert_one({
        'username': form['username'],
        'email': form['email'],
        'password': hashed,
        'role': form['role']
    })
    flash('User added successfully!', 'success')
    return redirect(url_for('settings'))

@app.route('/donate/<int:item_id>', methods=['POST'])
def donate_item(item_id):
    # Your logic to mark the item as donated
    # ...
    return jsonify({'success': True})

@app.route('/remove/<int:item_id>', methods=['POST'])
def remove_item(item_id):
    # Your logic to remove the item
    # ...
    return jsonify({'success': True})

# Initialize default admin user and run app
if __name__ == '__main__':
    if not db.users.find_one({'username': 'admin'}):
        default_pwd = bcrypt.hashpw('admin123'.encode(), bcrypt.gensalt())
        db.users.insert_one({
            'username': 'admin',
            'email': 'admin@freshflow.com',
            'password': default_pwd,
            'role': 'Admin'
        })
    
    # Add sample inventory data
    if db.inventory.count_documents({}) == 0:
        sample_items = [
            {'name': 'Fresh Milk', 'category': 'Dairy', 'quantity': 25, 'expiry_date': '2024-01-20', 'supplier': 'Dairy Direct', 'cost': 2.50},
            {'name': 'Bananas', 'category': 'Fruits', 'quantity': 50, 'expiry_date': '2024-01-18', 'supplier': 'Fresh Foods', 'cost': 1.20},
            {'name': 'Bread', 'category': 'Grains', 'quantity': 15, 'expiry_date': '2024-01-16', 'supplier': 'Bakery Co', 'cost': 3.00},
            {'name': 'Chicken Breast', 'category': 'Meat', 'quantity': 30, 'expiry_date': '2024-01-22', 'supplier': 'Meat Market', 'cost': 8.50},
            {'name': 'Apples', 'category': 'Fruits', 'quantity': 40, 'expiry_date': '2024-01-25', 'supplier': 'Fresh Foods', 'cost': 2.00}
        ]
        db.inventory.insert_many(sample_items)
    
    print("Starting FreshFlow...")
    app.run(debug=True, host='127.0.0.1', port=5000)
