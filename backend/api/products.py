from flask import Blueprint, request
from backend.config.database import execute_query
from backend.utils.auth import token_required, permission_required
from backend.utils.response import success_response, error_response
from backend.utils.audit import log_audit

products_bp = Blueprint('products', __name__, url_prefix='/api/products')

@products_bp.route('', methods=['GET'])
@token_required
def get_products():
    category = request.args.get('category')
    search = request.args.get('search')
    
    query = "SELECT * FROM products WHERE is_active = TRUE"
    params = []
    
    if category:
        query += " AND category = %s"
        params.append(category)
    
    if search:
        query += " AND (product_code LIKE %s OR product_name LIKE %s)"
        params.extend([f'%{search}%', f'%{search}%'])
    
    query += " ORDER BY product_name"
    
    products = execute_query(query, tuple(params) if params else None, fetch_all=True)
    return success_response(products)

@products_bp.route('/<int:id>', methods=['GET'])
@token_required
def get_product(id):
    product = execute_query("SELECT * FROM products WHERE id = %s", (id,), fetch_one=True)
    
    if not product:
        return error_response('Product not found', 404)
    
    return success_response(product)

@products_bp.route('', methods=['POST'])
@token_required
@permission_required('admin', 'write')
def create_product():
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    required_fields = ['product_code', 'product_name']
    for field in required_fields:
        if not data.get(field):
            return error_response(f'{field} is required', 400)
    
    query = """
        INSERT INTO products
        (product_code, product_name, description, category, specifications)
        VALUES (%s, %s, %s, %s, %s)
    """
    
    try:
        product_id = execute_query(
            query,
            (
                data['product_code'],
                data['product_name'],
                data.get('description'),
                data.get('category'),
                data.get('specifications')
            ),
            commit=True
        )
        
        log_audit(user_id, 'CREATE', 'product', product_id, None, data)
        
        return success_response({'id': product_id}, 'Product created successfully', 201)
    except Exception as e:
        return error_response(str(e), 500)

@products_bp.route('/<int:id>', methods=['PUT'])
@token_required
@permission_required('admin', 'write')
def update_product(id):
    data = request.get_json()
    user_id = request.current_user['user_id']
    
    old_data = execute_query("SELECT * FROM products WHERE id = %s", (id,), fetch_one=True)
    if not old_data:
        return error_response('Product not found', 404)
    
    query = """
        UPDATE products SET
            product_code = %s, product_name = %s, description = %s,
            category = %s, specifications = %s
        WHERE id = %s
    """
    
    try:
        execute_query(
            query,
            (
                data.get('product_code', old_data['product_code']),
                data.get('product_name', old_data['product_name']),
                data.get('description', old_data['description']),
                data.get('category', old_data['category']),
                data.get('specifications', old_data['specifications']),
                id
            ),
            commit=True
        )
        
        log_audit(user_id, 'UPDATE', 'product', id, old_data, data)
        
        return success_response(message='Product updated successfully')
    except Exception as e:
        return error_response(str(e), 500)

@products_bp.route('/search', methods=['GET'])
@token_required
def search_products():
    term = request.args.get('term', '')
    
    query = """
        SELECT id, product_code, product_name, category
        FROM products
        WHERE is_active = TRUE
        AND (product_code LIKE %s OR product_name LIKE %s)
        LIMIT 20
    """
    
    results = execute_query(query, (f'%{term}%', f'%{term}%'), fetch_all=True)
    return success_response(results)

@products_bp.route('/autocomplete', methods=['GET'])
@token_required
def autocomplete_products():
    term = request.args.get('term', '')
    category = request.args.get('category')
    limit = int(request.args.get('limit', 10))
    
    query = """
        SELECT 
            p.id, p.product_code, p.product_name, p.category,
            (SELECT COUNT(*) FROM orders o WHERE o.product_id = p.id) as order_count,
            (SELECT MAX(o.created_at) FROM orders o WHERE o.product_id = p.id) as last_ordered
        FROM products p
        WHERE p.is_active = TRUE
        AND (p.product_code LIKE %s OR p.product_name LIKE %s)
    """
    
    params = [f'%{term}%', f'%{term}%']
    
    if category:
        query += " AND p.category = %s"
        params.append(category)
    
    query += " ORDER BY order_count DESC, p.product_name LIMIT %s"
    params.append(limit)
    
    results = execute_query(query, tuple(params), fetch_all=True)
    
    suggestions = []
    for product in results:
        suggestions.append({
            'id': product['id'],
            'code': product['product_code'],
            'name': product['product_name'],
            'category': product['category'],
            'label': f"{product['product_code']} - {product['product_name']}",
            'popularity': product['order_count'] or 0
        })
    
    return success_response(suggestions)

@products_bp.route('/categories', methods=['GET'])
@token_required
def get_categories():
    query = """
        SELECT DISTINCT category, COUNT(*) as product_count
        FROM products
        WHERE is_active = TRUE AND category IS NOT NULL
        GROUP BY category
        ORDER BY category
    """
    
    categories = execute_query(query, fetch_all=True)
    return success_response(categories)
