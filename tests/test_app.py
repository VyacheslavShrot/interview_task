import unittest
from datetime import datetime

from app import app, db, Order, Product


class TestApp(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        self.app = app.test_client()

        with app.app_context():
            db.create_all()

        test_product = Product(
            title="Test",
            price=10,
            amount=200,
            end_date=datetime.strptime("01-01-2005", "%d-%m-%Y").date()
        )
        with app.app_context():
            db.session.add(test_product)
            db.session.commit()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_create_order(self):
        response = self.app.post('/order-create', data={
            'order_number': '123',
            'amount': '10',
            'product_id': '1'
        })
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            order = Order.query.filter_by(order_number='123').first()

        self.assertIsNotNone(order)

    def test_create_product(self):
        response = self.app.post('/product-create', data={
            'title': 'New Product',
            'price': '20.0',
            'amount': '50',
            'end_date': '2023-01-01'
        })
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            product = Product.query.filter_by(title='New Product').first()

        self.assertIsNotNone(product)

    def test_update_product(self):
        with app.app_context():
            product = Product.query.get(1)
        self.assertIsNotNone(product, "Product not found")

        response = self.app.post(
            f"/product-update/{product.id}",
            data={"amount": "52", "end_date": "2023-01-01"}
        )
        self.assertEqual(response.status_code, 302)

        with app.app_context():
            updated_product = Product.query.get(product.id)

        self.assertIsNotNone(updated_product, "Updated product not found")

        self.assertEqual(updated_product.amount, 52)

    def test_delete_product(self):
        with app.app_context():
            product = Product.query.get(1)
        self.assertIsNotNone(product, "Product not found")

        response = self.app.post(f"/product-delete/{product.id}")
        self.assertEqual(response.status_code, 302)


if __name__ == '__main__':
    unittest.main()
