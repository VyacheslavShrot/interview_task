from datetime import datetime

from flask import Flask, render_template, Blueprint, request, redirect, url_for, flash

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import IntegrityError

order_bp = Blueprint('order', __name__)
invoice_bp = Blueprint('invoice', __name__)
product_bp = Blueprint('product', __name__)
expense_invoice_bp = Blueprint('expense_invoice', __name__)
tax_invoice_bp = Blueprint('tax_invoice', __name__)
sell_product_bp = Blueprint('sell_product', __name__)


class OrderViews:
    @staticmethod
    @order_bp.route('/order', methods=['GET', 'POST'])
    def list_order():
        if request.method == 'POST':
            order_number = request.form.get('search_order_number')
            orders = Order.query.filter_by(order_number=order_number).all()
        else:
            orders = Order.query.all()

        return render_template('list_order.html', orders=orders)

    @staticmethod
    @order_bp.route('/order-create', methods=['POST', 'GET'])
    def create_order():
        if request.method == 'POST':
            order_number = request.form.get('order_number')
            amount = request.form.get('amount')
            product_id = request.form.get('product_id')

            new_order = Order(order_number=order_number, amount=amount)
            new_invoice = Invoice(amount=amount)

            try:
                new_order.invoice = new_invoice
                new_order.product_id = product_id
                db.session.add(new_order)
                db.session.commit()
                flash(f"Замовлення {new_order.order_number} і Рахунок фактура успішно створені.", "success")

            except IntegrityError:
                db.session.rollback()
                flash(f"Не вдалося створити замовлення з номером {order_number}. Такий номер вже існує.", "error")

            return redirect(url_for('order.list_order'))

        products = Product.query.all()
        return render_template('create_order.html', products=products)

    @staticmethod
    @order_bp.route('/order-update/<int:order_id>', methods=['POST', 'GET'])
    def update_order(order_id):
        order = Order.query.get(order_id)
        invoice = Invoice.query.get(order_id)
        if order:
            if request.method == 'POST':
                order_number = request.form.get('order_number')
                amount = request.form.get('amount')
                order.order_number = order_number
                order.amount = amount
                invoice.amount = amount
                db.session.commit()
                return redirect(url_for('order.list_order'))

            return render_template('update_order.html', order=order)

        else:
            return redirect(url_for('order.list_order'))

    @staticmethod
    @order_bp.route('/order-delete/<int:order_id>', methods=['POST', 'GET'])
    def delete_order(order_id):
        order = Order.query.get(order_id)
        invoice = Invoice.query.get(order_id)
        if order:
            db.session.delete(order)
            db.session.delete(invoice)
            db.session.commit()
            flash(f"Замовлення {order.order_number} і Рахунок фактура успішно видалено.", "success")
        return redirect(url_for('order.list_order'))

    @staticmethod
    @order_bp.route('/order-sell/<int:order_id>', methods=['POST'])
    def sell_order(order_id):
        order = Order.query.get(order_id)
        if order:
            quantity = int(request.form.get('quantity'))

            total_cost = order.sell_product(quantity)

            flash(f"Товари із замовлення {order.order_number} списано. Собівартість: {total_cost}", "success")

        return redirect(url_for('order.list_order'))


class InvoiceViews:
    @staticmethod
    @invoice_bp.route('/invoice/<int:order_id>', methods=['GET', 'POST'])
    def invoice(order_id):
        order = Order.query.get(order_id)
        expense_invoice = ExpenseInvoice.query.filter_by(order_id=order_id).first()
        tax_invoice = TaxInvoice.query.filter_by(order_id=order_id).first()

        if order:
            if expense_invoice or tax_invoice:
                invoice = order.invoice
                flash("Для цього замовлення вже створено видаткову накладну або податковий рахунок", "error")

                return render_template('invoice.html', invoice=invoice, order=order)

            else:
                invoice = order.invoice
                if request.method == 'POST':
                    try:
                        new_expense_invoice = ExpenseInvoice(
                            expense_date=datetime.utcnow(),
                            amount=invoice.amount
                        )
                        new_expense_invoice.order = order

                        commission = invoice.amount * 0.1
                        new_tax_invoice = TaxInvoice(
                            tax_date=datetime.utcnow(),
                            amount=commission
                        )
                        new_tax_invoice.order = order

                        product = order.product
                        product.amount -= invoice.amount
                        db.session.add(product)

                        db.session.add(new_expense_invoice)
                        db.session.add(new_tax_invoice)
                        db.session.commit()

                        flash("Видаткова накладна і Податковий рахунок успішно створені.", "success")

                    except IntegrityError:
                        db.session.rollback()
                        flash("Помилка при створенні Видаткової накладної або Податкового рахунку.", "error")

                return render_template('invoice.html', invoice=invoice, order=order)

        else:
            return redirect(url_for('order.list_order'))


class ProductViews:
    @staticmethod
    @product_bp.route('/product', methods=['GET', 'POST'])
    def product_list():
        products = Product.query.all()
        if request.method == 'POST':
            end_date_str = request.form.get('end_date')
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            products = Product.query.filter(Product.end_date >= end_date).all()

        return render_template('product_list.html', products=products)

    @staticmethod
    @product_bp.route('/product-create', methods=['POST', 'GET'])
    def product_create():
        if request.method == 'POST':
            title = request.form.get('title')
            price = request.form.get('price')
            amount = request.form.get('amount')
            end_date_str = request.form.get('end_date')

            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

            new_product = Product(title=title, price=price, amount=amount, end_date=end_date)

            try:
                db.session.add(new_product)
                db.session.commit()
                flash(f"Продукт {new_product.title} успішно створен.", "success")

            except IntegrityError:
                db.session.rollback()
                flash(f"Не вдалося створити продукт з назвою {new_product.title}. Така назва вже існує.", "error")

            return redirect(url_for('product.product_list'))

        return render_template('create_product.html')

    @staticmethod
    @product_bp.route('/product-update/<int:product_id>', methods=['POST', 'GET'])
    def update_product(product_id):
        product = Product.query.get(product_id)
        if product:
            if request.method == 'POST':
                title = request.form.get('title')
                price = request.form.get('price')
                amount = request.form.get('amount')
                end_date_str = request.form.get('end_date')

                end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

                product.title = title
                product.price = price
                product.amount = amount
                product.end_date = end_date
                db.session.commit()
                return redirect(url_for('product.product_list'))

            return render_template('update_product.html', product=product)

        else:
            return redirect(url_for('product.product_list'))

    @staticmethod
    @product_bp.route('/product-delete/<int:product_id>', methods=['POST', 'GET'])
    def delete_product(product_id):
        product = Product.query.get(product_id)
        if product:
            db.session.delete(product)
            db.session.commit()
            flash(f"Продукт {product.title} успішно видалено.", "success")
        return redirect(url_for('product.product_list'))


class ExpenseInvoiceViews:
    @staticmethod
    @expense_invoice_bp.route('/invoice/expense/<int:order_id>', methods=['POST', 'GET'])
    def expense_invoice(order_id):
        expense_invoice = ExpenseInvoice.query.filter_by(order_id=order_id).first()
        tax_invoice = TaxInvoice.query.filter_by(order_id=order_id).first()

        if expense_invoice:
            return render_template('expense_invoice.html', expense_invoice=expense_invoice, tax_invoice=tax_invoice)


class TaxInvoiceViews:
    @staticmethod
    @tax_invoice_bp.route('/invoice/tax/<int:order_id>', methods=['POST', 'GET'])
    def tax_invoice(order_id):
        tax_invoice = TaxInvoice.query.filter_by(order_id=order_id).first()

        if tax_invoice:
            return render_template('tax_invoice.html', tax_invoice=tax_invoice)


class SellProductViews:
    @staticmethod
    @sell_product_bp.route('/product/sell', methods=['POST', 'GET'])
    def sell_product():
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        start_date = datetime.strptime(start_date_str, '%Y-%m-%d') if start_date_str else None
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d') if end_date_str else None

        total_profit = 0

        if start_date and end_date:
            expense_invoices = ExpenseInvoice.query.filter(
                ExpenseInvoice.expense_date.between(start_date, end_date)
            ).all()
        else:
            expense_invoices = ExpenseInvoice.query.all()

        for expense_invoice in expense_invoices:
            total_profit += expense_invoice.order.product.price * expense_invoice.amount

        return render_template('sell_product.html', expense_invoices=expense_invoices, total_profit=total_profit)


app = Flask(__name__)
app.secret_key = 'my_secret_key_123'
app.register_blueprint(order_bp)
app.register_blueprint(invoice_bp)
app.register_blueprint(product_bp)
app.register_blueprint(expense_invoice_bp)
app.register_blueprint(tax_invoice_bp)
app.register_blueprint(sell_product_bp)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mydatabase.db'
db = SQLAlchemy(app)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    production_date = db.Column(db.Date)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    order_number = db.Column(db.Integer, unique=True)
    amount = db.Column(db.Integer)
    invoice = db.relationship('Invoice', backref='order', uselist=False)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', back_populates='orders')
    expense_invoice = db.relationship('ExpenseInvoice', back_populates='order', uselist=False)
    tax_invoice = db.relationship('TaxInvoice', back_populates='order', uselist=False)

    def __str__(self):
        return f"{self.id}_{self.order_number} {self.amount}"

    def sell_product(self, quantity):
        batches = Order.query.filter(
            Order.product_id == self.product.id,
            Order.amount > 0
        ).order_by(Order.production_date).all()

        total_cost = 0
        remaining_quantity = quantity

        for batch in batches:
            to_sell = min(remaining_quantity, batch.amount)

            total_cost += to_sell * batch.product.price
            batch.amount -= to_sell
            remaining_quantity -= to_sell

            if batch.amount == 0:
                batch.completed = True

            self.invoice.amount = batch.amount

            db.session.commit()

            if remaining_quantity == 0:
                break

        return total_cost


class Invoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    invoice_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Integer)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))

    def __str__(self):
        return f"{self.id} {self.amount}"


class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), unique=True)
    price = db.Column(db.Float)
    amount = db.Column(db.Integer)
    production_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    orders = db.relationship('Order', back_populates='product')

    def __str__(self):
        return f"{self.id} {self.title}"


class ExpenseInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    expense_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Integer)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    order = db.relationship('Order', back_populates='expense_invoice')

    def __str__(self):
        return f"{self.id} {self.amount}"


class TaxInvoice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tax_date = db.Column(db.DateTime, default=datetime.utcnow)
    amount = db.Column(db.Integer)
    order_id = db.Column(db.Integer, db.ForeignKey('order.id'))
    order = db.relationship('Order', back_populates='tax_invoice')


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
