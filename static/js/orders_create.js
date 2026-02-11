@app.route('/orders/create')
def create_order():
    items = get_items()  # Fetch items from DB
    categories = get_categories()  # Fetch categories from DB
    return render_template('orders_create.html', items=items, categories=categories)