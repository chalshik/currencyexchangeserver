from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///currency_converter.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Models
class Currency(db.Model):
    __tablename__ = 'currencies'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(10), unique=True, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    updated_at = db.Column(db.String(50), nullable=False)
    default_buy_rate = db.Column(db.Float, nullable=False, default=0.0)
    default_sell_rate = db.Column(db.Float, nullable=False, default=0.0)
    
    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'quantity': self.quantity,
            'updated_at': self.updated_at,
            'default_buy_rate': self.default_buy_rate,
            'default_sell_rate': self.default_sell_rate
        }

class History(db.Model):
    __tablename__ = 'history'
    
    id = db.Column(db.Integer, primary_key=True)
    currency_code = db.Column(db.String(10), nullable=False)
    operation_type = db.Column(db.String(20), nullable=False)
    rate = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    total = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.String(50), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'currency_code': self.currency_code,
            'operation_type': self.operation_type,
            'rate': self.rate,
            'quantity': self.quantity,
            'total': self.total,
            'created_at': self.created_at
        }

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    created_at = db.Column(db.String(50), nullable=False)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'password': self.password,
            'role': self.role,
            'created_at': self.created_at
        }

# Helper functions
def current_timestamp():
    return datetime.now().isoformat()

# Initialize database
def initialize_database():
    with app.app_context():
        db.create_all()
        
        # Create initial SOM currency if it doesn't exist
        if not Currency.query.filter_by(code='SOM').first():
            som_currency = Currency(
                code='SOM',
                quantity=0.0,
                updated_at=current_timestamp(),
                default_buy_rate=0.0,
                default_sell_rate=0.0
            )
            db.session.add(som_currency)
        
        # Create initial admin user if it doesn't exist
        if not User.query.filter_by(username='a').first():
            admin_user = User(
                username='a',
                password='a',
                role='admin',
                created_at=current_timestamp()
            )
            db.session.add(admin_user)
        
        db.session.commit()

# Initialize database at startup
initialize_database()

# =====================
# CURRENCY ENDPOINTS
# =====================

@app.route('/api/currencies', methods=['GET'])
def get_all_currencies():
    currencies = Currency.query.order_by(Currency.updated_at.desc()).all()
    return jsonify([currency.to_dict() for currency in currencies])

@app.route('/api/currencies/<string:code>', methods=['GET'])
def get_currency(code):
    currency = Currency.query.filter_by(code=code).first()
    if currency:
        return jsonify(currency.to_dict())
    return jsonify({'error': 'Currency not found'}), 404

@app.route('/api/currencies', methods=['POST'])
def create_or_update_currency():
    data = request.get_json()
    code = data.get('code')
    
    # Check if currency exists
    currency = Currency.query.filter_by(code=code).first()
    
    if currency:
        # Update existing currency
        currency.quantity = data.get('quantity', currency.quantity)
        currency.updated_at = current_timestamp()
        currency.default_buy_rate = data.get('default_buy_rate', currency.default_buy_rate)
        currency.default_sell_rate = data.get('default_sell_rate', currency.default_sell_rate)
    else:
        # Create new currency
        currency = Currency(
            code=code,
            quantity=data.get('quantity', 0.0),
            updated_at=current_timestamp(),
            default_buy_rate=data.get('default_buy_rate', 0.0),
            default_sell_rate=data.get('default_sell_rate', 0.0)
        )
        db.session.add(currency)
    
    db.session.commit()
    return jsonify(currency.to_dict())

@app.route('/api/currencies/<int:id>', methods=['DELETE'])
def delete_currency(id):
    currency = Currency.query.get(id)
    if currency:
        db.session.delete(currency)
        db.session.commit()
        return jsonify({'message': 'Currency deleted'})
    return jsonify({'error': 'Currency not found'}), 404

@app.route('/api/currencies/<string:code>/quantity', methods=['PUT'])
def update_currency_quantity(code):
    data = request.get_json()
    new_quantity = data.get('quantity')
    
    currency = Currency.query.filter_by(code=code).first()
    if currency:
        currency.quantity = new_quantity
        currency.updated_at = current_timestamp()
        db.session.commit()
        return jsonify(currency.to_dict())
    return jsonify({'error': 'Currency not found'}), 404

# =====================
# HISTORY ENDPOINTS
# =====================

@app.route('/api/history', methods=['GET'])
def get_history():
    # Get query parameters
    currency_code = request.args.get('currency_code')
    operation_type = request.args.get('operation_type')
    limit = request.args.get('limit', type=int)
    
    query = History.query
    
    if currency_code:
        query = query.filter_by(currency_code=currency_code)
    if operation_type:
        query = query.filter_by(operation_type=operation_type)
    
    query = query.order_by(History.created_at.desc())
    
    if limit:
        query = query.limit(limit)
    
    history = query.all()
    return jsonify([entry.to_dict() for entry in history])

@app.route('/api/history/filter', methods=['GET'])
def get_filtered_history():
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    currency_code = request.args.get('currency_code')
    operation_type = request.args.get('operation_type')
    
    query = History.query
    
    if from_date and to_date:
        query = query.filter(History.created_at >= from_date, History.created_at <= to_date)
    if currency_code:
        query = query.filter_by(currency_code=currency_code)
    if operation_type:
        query = query.filter_by(operation_type=operation_type)
    
    query = query.order_by(History.created_at.desc())
    
    history = query.all()
    return jsonify([entry.to_dict() for entry in history])

@app.route('/api/history', methods=['POST'])
def create_history():
    data = request.get_json()
    
    history = History(
        currency_code=data['currency_code'],
        operation_type=data['operation_type'],
        rate=data['rate'],
        quantity=data['quantity'],
        total=data['total'],
        created_at=data.get('created_at', current_timestamp())
    )
    
    db.session.add(history)
    db.session.commit()
    return jsonify(history.to_dict()), 201

@app.route('/api/history/<int:id>', methods=['PUT'])
def update_history(id):
    data = request.get_json()
    
    history = History.query.get(id)
    if not history:
        return jsonify({'error': 'History entry not found'}), 404
    
    history.currency_code = data.get('currency_code', history.currency_code)
    history.operation_type = data.get('operation_type', history.operation_type)
    history.rate = data.get('rate', history.rate)
    history.quantity = data.get('quantity', history.quantity)
    history.total = data.get('total', history.total)
    history.created_at = data.get('created_at', history.created_at)
    
    db.session.commit()
    return jsonify(history.to_dict())

@app.route('/api/history/<int:id>', methods=['DELETE'])
def delete_history(id):
    history = History.query.get(id)
    if not history:
        return jsonify({'error': 'History entry not found'}), 404
    
    db.session.delete(history)
    db.session.commit()
    return jsonify({'message': 'History entry deleted'})

# =====================
# USER ENDPOINTS
# =====================

@app.route('/api/users', methods=['GET'])
def get_all_users():
    users = User.query.order_by(User.created_at.desc()).all()
    return jsonify([user.to_dict() for user in users])

@app.route('/api/users/<int:id>', methods=['GET'])
def get_user(id):
    user = User.query.get(id)
    if user:
        return jsonify(user.to_dict())
    return jsonify({'error': 'User not found'}), 404

@app.route('/api/users/login', methods=['POST'])
def login_user():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        return jsonify(user.to_dict())
    return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    
    # Check if username exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'error': 'Username already exists'}), 400
    
    user = User(
        username=data['username'],
        password=data['password'],
        role=data.get('role', 'user'),
        created_at=current_timestamp()
    )
    
    db.session.add(user)
    db.session.commit()
    return jsonify(user.to_dict()), 201

@app.route('/api/users/<int:id>', methods=['PUT'])
def update_user(id):
    data = request.get_json()
    
    user = User.query.get(id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Check if username is being changed to one that already exists
    if 'username' in data and data['username'] != user.username:
        if User.query.filter_by(username=data['username']).first():
            return jsonify({'error': 'Username already exists'}), 400
    
    user.username = data.get('username', user.username)
    user.password = data.get('password', user.password)
    user.role = data.get('role', user.role)
    
    db.session.commit()
    return jsonify(user.to_dict())

@app.route('/api/users/<int:id>', methods=['DELETE'])
def delete_user(id):
    user = User.query.get(id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    # Prevent deleting the admin user
    if user.username == 'a':
        return jsonify({'error': 'Cannot delete admin user'}), 403
    
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted'})

@app.route('/api/users/check-username', methods=['POST'])
def check_username():
    data = request.get_json()
    username = data.get('username')
    
    exists = User.query.filter_by(username=username).first() is not None
    return jsonify({'exists': exists})

# =====================
# SYSTEM ENDPOINTS
# =====================

@app.route('/api/system/reset', methods=['POST'])
def reset_data():
    # Delete all history entries
    History.query.delete()
    
    # Reset all currency quantities to zero
    currencies = Currency.query.all()
    for currency in currencies:
        currency.quantity = 0.0
        currency.updated_at = current_timestamp()
    
    # Ensure SOM currency exists
    if not Currency.query.filter_by(code='SOM').first():
        som_currency = Currency(
            code='SOM',
            quantity=0.0,
            updated_at=current_timestamp(),
            default_buy_rate=0.0,
            default_sell_rate=0.0
        )
        db.session.add(som_currency)
    
    # Delete all users except admin
    User.query.filter(User.username != 'a').delete()
    
    # Ensure admin user exists
    if not User.query.filter_by(username='a').first():
        admin_user = User(
            username='a',
            password='a',
            role='admin',
            created_at=current_timestamp()
        )
        db.session.add(admin_user)
    else:
        # Reset admin user
        admin = User.query.filter_by(username='a').first()
        admin.password = 'a'
        admin.role = 'admin'
    
    db.session.commit()
    return jsonify({'message': 'Data reset successfully'})

@app.route('/api/system/currency-summary', methods=['GET'])
def get_currency_summary():
    som = Currency.query.filter_by(code='SOM').first()
    other_currencies = Currency.query.filter(Currency.code != 'SOM').all()
    
    return jsonify({
        'som_balance': som.quantity if som else 0.0,
        'other_currencies': {
            currency.code: currency.quantity for currency in other_currencies
        }
    })

@app.route('/api/system/history-codes', methods=['GET'])
def get_history_currency_codes():
    codes = db.session.query(History.currency_code).distinct().order_by(History.currency_code).all()
    return jsonify([code[0] for code in codes])

@app.route('/api/system/history-types', methods=['GET'])
def get_history_operation_types():
    types = db.session.query(History.operation_type).distinct().order_by(History.operation_type).all()
    return jsonify([type[0] for type in types])

@app.route('/api/system/exchange', methods=['POST'])
def perform_exchange():
    data = request.get_json()
    
    # Extract exchange parameters
    currency_code = data.get('currency_code')
    operation_type = data.get('operation_type')
    rate = data.get('rate')
    quantity = data.get('quantity')
    total = data.get('total')
    
    # Validate parameters
    if not all([currency_code, operation_type, rate, quantity, total]):
        return jsonify({'error': 'Missing required parameters'}), 400
    
    try:
        # Begin transaction
        if operation_type == 'Purchase':
            # Check if enough SOM available
            som = Currency.query.filter_by(code='SOM').first()
            if not som or som.quantity < total:
                return jsonify({'error': 'Not enough SOM to perform this operation'}), 400
                
            # Update SOM balance (deduct total)
            som.quantity -= total
            som.updated_at = current_timestamp()
            
            # Update or create target currency (add quantity)
            target_currency = Currency.query.filter_by(code=currency_code).first()
            if target_currency:
                target_currency.quantity += quantity
                target_currency.updated_at = current_timestamp()
            else:
                target_currency = Currency(
                    code=currency_code,
                    quantity=quantity,
                    updated_at=current_timestamp(),
                    default_buy_rate=0.0,
                    default_sell_rate=0.0
                )
                db.session.add(target_currency)
                
        elif operation_type == 'Sale':
            # Check if enough currency available
            target_currency = Currency.query.filter_by(code=currency_code).first()
            if not target_currency or target_currency.quantity < quantity:
                return jsonify({'error': f'Not enough {currency_code} to perform this operation'}), 400
                
            # Update SOM balance (add total)
            som = Currency.query.filter_by(code='SOM').first()
            if som:
                som.quantity += total
                som.updated_at = current_timestamp()
            else:
                som = Currency(
                    code='SOM',
                    quantity=total,
                    updated_at=current_timestamp(),
                    default_buy_rate=0.0,
                    default_sell_rate=0.0
                )
                db.session.add(som)
                
            # Update target currency (deduct quantity)
            target_currency.quantity -= quantity
            target_currency.updated_at = current_timestamp()
        
        # Record transaction in history
        history = History(
            currency_code=currency_code,
            operation_type=operation_type,
            rate=rate,
            quantity=quantity,
            total=total,
            created_at=current_timestamp()
        )
        db.session.add(history)
        
        # Commit all changes
        db.session.commit()
        return jsonify({'success': True, 'message': 'Exchange completed successfully'})
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)