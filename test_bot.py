"""
Test suite for the Employee Management System Telegram Bot.
"""

import unittest
import asyncio
import os
import sys
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

# Add the current directory to the path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    DatabaseManager, UserManager, CompanyManager, EmployeeManager, 
    LogManager, SettingsManager
)
from payment_handler import PaymentProcessor, SubscriptionManager, PaymentGatewayMock

class TestDatabaseManager(unittest.TestCase):
    """Test database manager functionality."""
    
    def setUp(self):
        """Set up test database manager."""
        self.db = DatabaseManager()
    
    def test_connection(self):
        """Test database connection."""
        # This test requires a running MySQL instance
        # In production, you might want to use a test database
        result = self.db.connect()
        self.assertIsInstance(result, bool)
        if result:
            self.db.disconnect()

class TestUserManager(unittest.TestCase):
    """Test user management functionality."""
    
    def setUp(self):
        """Set up test data."""
        self.test_telegram_id = 123456789
        self.test_username = "testuser"
        self.test_first_name = "Test"
        self.test_last_name = "User"
    
    @patch('database.db.execute_query')
    def test_is_main_admin(self, mock_query):
        """Test main admin check."""
        # Test when user is admin
        mock_query.return_value = [{'id': 1}]
        result = UserManager.is_main_admin(self.test_telegram_id)
        self.assertTrue(result)
        
        # Test when user is not admin
        mock_query.return_value = []
        result = UserManager.is_main_admin(self.test_telegram_id)
        self.assertFalse(result)
    
    @patch('database.db.execute_query')
    def test_is_company_owner(self, mock_query):
        """Test company owner check."""
        # Test when user is company owner
        mock_query.return_value = [{
            'id': 1,
            'company_name': 'Test Company',
            'subscription_type': 'lifetime',
            'is_subscription_active': True
        }]
        result = UserManager.is_company_owner(self.test_telegram_id)
        self.assertIsNotNone(result)
        self.assertEqual(result['company_name'], 'Test Company')
        
        # Test when user is not company owner
        mock_query.return_value = []
        result = UserManager.is_company_owner(self.test_telegram_id)
        self.assertIsNone(result)
    
    @patch('database.db.execute_query')
    def test_is_employee(self, mock_query):
        """Test employee check."""
        # Test when user is employee
        mock_query.return_value = [{
            'id': 1,
            'employee_id': 'EMP001',
            'first_name': 'Test',
            'company_name': 'Test Company'
        }]
        result = UserManager.is_employee(self.test_telegram_id)
        self.assertIsNotNone(result)
        self.assertEqual(result['employee_id'], 'EMP001')
        
        # Test when user is not employee
        mock_query.return_value = []
        result = UserManager.is_employee(self.test_telegram_id)
        self.assertIsNone(result)
    
    @patch('database.UserManager.is_main_admin')
    @patch('database.UserManager.is_company_owner')
    @patch('database.UserManager.is_employee')
    def test_get_user_role(self, mock_employee, mock_company, mock_admin):
        """Test user role determination."""
        # Test main admin
        mock_admin.return_value = True
        mock_company.return_value = None
        mock_employee.return_value = None
        role, data = UserManager.get_user_role(self.test_telegram_id)
        self.assertEqual(role, 'main_admin')
        
        # Test company owner
        mock_admin.return_value = False
        mock_company.return_value = {'id': 1, 'company_name': 'Test'}
        mock_employee.return_value = None
        role, data = UserManager.get_user_role(self.test_telegram_id)
        self.assertEqual(role, 'company_owner')
        
        # Test employee
        mock_admin.return_value = False
        mock_company.return_value = None
        mock_employee.return_value = {'id': 1, 'employee_id': 'EMP001'}
        role, data = UserManager.get_user_role(self.test_telegram_id)
        self.assertEqual(role, 'employee')
        
        # Test unknown user
        mock_admin.return_value = False
        mock_company.return_value = None
        mock_employee.return_value = None
        role, data = UserManager.get_user_role(self.test_telegram_id)
        self.assertEqual(role, 'unknown')

class TestCompanyManager(unittest.TestCase):
    """Test company management functionality."""
    
    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = CompanyManager.generate_api_key()
        self.assertIsInstance(api_key, str)
        self.assertGreater(len(api_key), 20)  # Should be reasonably long
    
    def test_generate_company_code(self):
        """Test company code generation."""
        company_name = "Test Company Inc."
        code = CompanyManager.generate_company_code(company_name)
        self.assertIsInstance(code, str)
        self.assertIn('TESTCO', code)  # Should contain alphanumeric chars from name
        self.assertIn('_', code)  # Should have separator
    
    @patch('database.db.execute_update')
    @patch('database.db.get_last_insert_id')
    @patch('database.CompanyManager.generate_company_code')
    @patch('database.CompanyManager.generate_api_key')
    def test_create_company(self, mock_api_key, mock_code, mock_insert_id, mock_update):
        """Test company creation."""
        # Mock return values
        mock_api_key.return_value = 'test_api_key_123'
        mock_code.return_value = 'TESTCO_ABC123'
        mock_update.return_value = True
        mock_insert_id.return_value = 1
        
        result = CompanyManager.create_company(
            company_name="Test Company",
            owner_telegram_id=123456789,
            subscription_type='1m'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['company_name'], 'Test Company')
        self.assertEqual(result['api_key'], 'test_api_key_123')

class TestEmployeeManager(unittest.TestCase):
    """Test employee management functionality."""
    
    @patch('database.db.execute_update')
    def test_add_employee(self, mock_update):
        """Test employee addition."""
        mock_update.return_value = True
        
        result = EmployeeManager.add_employee(
            company_id=1,
            employee_id='EMP001',
            first_name='John',
            last_name='Doe',
            designation='Developer'
        )
        
        self.assertTrue(result)
        mock_update.assert_called_once()
    
    @patch('database.db.execute_query')
    def test_get_employees_by_company(self, mock_query):
        """Test getting employees by company."""
        mock_query.return_value = [
            {'id': 1, 'employee_id': 'EMP001', 'first_name': 'John'},
            {'id': 2, 'employee_id': 'EMP002', 'first_name': 'Jane'}
        ]
        
        result = EmployeeManager.get_employees_by_company(1)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]['employee_id'], 'EMP001')
    
    @patch('database.db.execute_query')
    def test_get_employee_by_id(self, mock_query):
        """Test getting employee by ID."""
        mock_query.return_value = [
            {'id': 1, 'employee_id': 'EMP001', 'first_name': 'John'}
        ]
        
        result = EmployeeManager.get_employee_by_id(1, 'EMP001')
        self.assertIsNotNone(result)
        self.assertEqual(result['employee_id'], 'EMP001')
        
        # Test employee not found
        mock_query.return_value = []
        result = EmployeeManager.get_employee_by_id(1, 'NONEXISTENT')
        self.assertIsNone(result)

class TestPaymentProcessor(unittest.TestCase):
    """Test payment processing functionality."""
    
    def setUp(self):
        """Set up payment processor."""
        self.processor = PaymentProcessor()
    
    def test_verify_webhook_signature(self):
        """Test webhook signature verification."""
        payload = '{"test": "data"}'
        
        # Test with correct signature
        import hmac
        import hashlib
        expected_signature = hmac.new(
            self.processor.webhook_secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        result = self.processor.verify_webhook_signature(payload, expected_signature)
        self.assertTrue(result)
        
        # Test with incorrect signature
        result = self.processor.verify_webhook_signature(payload, 'wrong_signature')
        self.assertFalse(result)
    
    @patch('database.db.execute_update')
    def test_create_payment_record(self, mock_update):
        """Test payment record creation."""
        mock_update.return_value = True
        
        result = self.processor.create_payment_record(
            company_id=1,
            transaction_id='test_txn_123',
            amount=29.99,
            subscription_type='1m'
        )
        
        self.assertTrue(result)
        mock_update.assert_called_once()

class TestSubscriptionManager(unittest.TestCase):
    """Test subscription management functionality."""
    
    @patch('payment_handler.SettingsManager.get_pricing')
    def test_get_subscription_price(self, mock_pricing):
        """Test subscription price retrieval."""
        mock_pricing.return_value = {
            '1m': 29.99,
            '6m': 149.99,
            'lifetime': 499.99
        }
        
        price = SubscriptionManager.get_subscription_price('1m')
        self.assertEqual(price, 29.99)
        
        price = SubscriptionManager.get_subscription_price('invalid')
        self.assertEqual(price, 0.0)
    
    @patch('payment_handler.PaymentGatewayMock.create_payment_link')
    @patch('payment_handler.PaymentProcessor.create_payment_record')
    @patch('payment_handler.SubscriptionManager.get_subscription_price')
    def test_create_subscription_payment(self, mock_price, mock_record, mock_gateway):
        """Test subscription payment creation."""
        mock_price.return_value = 29.99
        mock_record.return_value = True
        mock_gateway.return_value = {
            'transaction_id': 'test_txn_123',
            'payment_url': 'https://test.com/pay',
            'amount': 29.99
        }
        
        result = SubscriptionManager.create_subscription_payment(
            company_id=1,
            subscription_type='1m'
        )
        
        self.assertIsNotNone(result)
        self.assertEqual(result['transaction_id'], 'test_txn_123')

class TestPaymentGatewayMock(unittest.TestCase):
    """Test mock payment gateway functionality."""
    
    def test_create_payment_link(self):
        """Test payment link creation."""
        result = PaymentGatewayMock.create_payment_link(
            amount=29.99,
            currency='USD',
            subscription_type='1m',
            company_id=1
        )
        
        self.assertIn('transaction_id', result)
        self.assertIn('payment_url', result)
        self.assertEqual(result['amount'], 29.99)
        self.assertEqual(result['currency'], 'USD')
    
    def test_verify_payment(self):
        """Test payment verification."""
        result = PaymentGatewayMock.verify_payment('test_txn_123')
        
        self.assertEqual(result['transaction_id'], 'test_txn_123')
        self.assertEqual(result['status'], 'completed')
        self.assertTrue(result['verified'])

class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    @patch('database.db.execute_query')
    @patch('database.db.execute_update')
    @patch('database.db.get_last_insert_id')
    def test_complete_user_flow(self, mock_insert_id, mock_update, mock_query):
        """Test complete user registration and employee management flow."""
        # Mock database responses
        mock_update.return_value = True
        mock_insert_id.return_value = 1
        
        # Test company creation
        company = CompanyManager.create_company(
            company_name="Test Company",
            owner_telegram_id=123456789,
            subscription_type='1m'
        )
        self.assertIsNotNone(company)
        
        # Test employee addition
        result = EmployeeManager.add_employee(
            company_id=company['id'],
            employee_id='EMP001',
            first_name='John',
            last_name='Doe'
        )
        self.assertTrue(result)
        
        # Test employee retrieval
        mock_query.return_value = [
            {'id': 1, 'employee_id': 'EMP001', 'first_name': 'John', 'last_name': 'Doe'}
        ]
        
        employees = EmployeeManager.get_employees_by_company(company['id'])
        self.assertEqual(len(employees), 1)
        self.assertEqual(employees[0]['employee_id'], 'EMP001')

def run_tests():
    """Run all tests."""
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestDatabaseManager,
        TestUserManager,
        TestCompanyManager,
        TestEmployeeManager,
        TestPaymentProcessor,
        TestSubscriptionManager,
        TestPaymentGatewayMock,
        TestIntegration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    print("Running Employee Management System Tests...")
    print("=" * 50)
    
    success = run_tests()
    
    print("=" * 50)
    if success:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    sys.exit(0 if success else 1)

