"""
Database connection and utility functions for the Employee Management System.
"""

import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging
from typing import Optional, Dict, List, Any
import hashlib
import secrets
from datetime import datetime, timedelta

# Load environment variables
load_dotenv('bot.env')

# Configure logging
logging.basicConfig(level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')))
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations for the Employee Management System."""
    
    def __init__(self):
        self.config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 3306)),
            'user': os.getenv('DB_USER', 'root'),
            'password': os.getenv('DB_PASSWORD', 'rootpassword'),
            'database': os.getenv('DB_NAME', 'employee_management_system'),
            'autocommit': True,
            'charset': 'utf8mb4',
            'collation': 'utf8mb4_unicode_ci'
        }
        self.connection = None
    
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.connection = mysql.connector.connect(**self.config)
            if self.connection.is_connected():
                logger.info("Successfully connected to MySQL database")
                return True
        except Error as e:
            logger.error(f"Error connecting to MySQL: {e}")
            return False
        return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            logger.info("MySQL connection closed")
    
    def execute_query(self, query: str, params: tuple = None) -> Optional[List[Dict]]:
        """Execute a SELECT query and return results."""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            cursor = self.connection.cursor(dictionary=True)
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            cursor.close()
            return result
        except Error as e:
            logger.error(f"Error executing query: {e}")
            return None
    
    def execute_update(self, query: str, params: tuple = None) -> bool:
        """Execute an INSERT, UPDATE, or DELETE query."""
        try:
            if not self.connection or not self.connection.is_connected():
                self.connect()
            
            cursor = self.connection.cursor()
            cursor.execute(query, params or ())
            self.connection.commit()
            cursor.close()
            return True
        except Error as e:
            logger.error(f"Error executing update: {e}")
            return False
    
    def get_last_insert_id(self) -> Optional[int]:
        """Get the last inserted ID."""
        try:
            if not self.connection or not self.connection.is_connected():
                return None
            
            cursor = self.connection.cursor()
            cursor.execute("SELECT LAST_INSERT_ID()")
            result = cursor.fetchone()
            cursor.close()
            return result[0] if result else None
        except Error as e:
            logger.error(f"Error getting last insert ID: {e}")
            return None

# Global database manager instance
db = DatabaseManager()

class UserManager:
    """Manages user-related database operations."""
    
    @staticmethod
    def is_main_admin(telegram_id: int) -> bool:
        """Check if user is a main admin."""
        query = "SELECT id FROM main_admin WHERE telegram_id = %s"
        result = db.execute_query(query, (telegram_id,))
        return bool(result)
    
    @staticmethod
    def is_company_owner(telegram_id: int) -> Optional[Dict]:
        """Check if user is a company owner and return company info."""
        query = """
        SELECT c.*, 
               CASE 
                   WHEN c.subscription_type = 'lifetime' THEN TRUE
                   WHEN c.subscription_end_date > NOW() THEN TRUE
                   ELSE FALSE
               END as is_subscription_active
        FROM companies c 
        WHERE c.owner_telegram_id = %s AND c.is_active = TRUE
        """
        result = db.execute_query(query, (telegram_id,))
        return result[0] if result else None
    
    @staticmethod
    def is_employee(telegram_id: int) -> Optional[Dict]:
        """Check if user is an employee and return employee info."""
        query = """
        SELECT e.*, c.company_name, c.company_code
        FROM employees e
        JOIN companies c ON e.company_id = c.id
        WHERE e.telegram_id = %s AND e.status = 'active'
        """
        result = db.execute_query(query, (telegram_id,))
        return result[0] if result else None
    
    @staticmethod
    def get_user_role(telegram_id: int) -> tuple[str, Optional[Dict]]:
        """Get user role and associated data."""
        # Check main admin first
        if UserManager.is_main_admin(telegram_id):
            return 'main_admin', None
        
        # Check company owner
        company_info = UserManager.is_company_owner(telegram_id)
        if company_info:
            return 'company_owner', company_info
        
        # Check employee
        employee_info = UserManager.is_employee(telegram_id)
        if employee_info:
            return 'employee', employee_info
        
        return 'unknown', None
    
    @staticmethod
    def add_main_admin(telegram_id: int, username: str = None, first_name: str = None, last_name: str = None) -> bool:
        """Add a new main admin."""
        query = """
        INSERT INTO main_admin (telegram_id, username, first_name, last_name)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        username = VALUES(username),
        first_name = VALUES(first_name),
        last_name = VALUES(last_name),
        updated_at = CURRENT_TIMESTAMP
        """
        return db.execute_update(query, (telegram_id, username, first_name, last_name))

class CompanyManager:
    """Manages company-related database operations."""
    
    @staticmethod
    def generate_api_key() -> str:
        """Generate a unique API key."""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def generate_company_code(company_name: str) -> str:
        """Generate a unique company code."""
        # Create base code from company name
        base_code = ''.join(c.upper() for c in company_name if c.isalnum())[:6]
        
        # Add random suffix to ensure uniqueness
        suffix = secrets.token_hex(3).upper()
        return f"{base_code}_{suffix}"
    
    @staticmethod
    def create_company(
        company_name: str,
        owner_telegram_id: int,
        owner_username: str = None,
        owner_first_name: str = None,
        owner_last_name: str = None,
        subscription_type: str = '1m'
    ) -> Optional[Dict]:
        """Create a new company."""
        try:
            # Generate unique identifiers
            company_code = CompanyManager.generate_company_code(company_name)
            api_key = CompanyManager.generate_api_key()
            
            # Calculate subscription end date
            subscription_end_date = None
            if subscription_type != 'lifetime':
                months = 1 if subscription_type == '1m' else 6
                subscription_end_date = datetime.now() + timedelta(days=30 * months)
            
            query = """
            INSERT INTO companies (
                company_name, company_code, owner_telegram_id, owner_username,
                owner_first_name, owner_last_name, subscription_type,
                subscription_end_date, api_key
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            params = (
                company_name, company_code, owner_telegram_id, owner_username,
                owner_first_name, owner_last_name, subscription_type,
                subscription_end_date, api_key
            )
            
            if db.execute_update(query, params):
                company_id = db.get_last_insert_id()
                return {
                    'id': company_id,
                    'company_name': company_name,
                    'company_code': company_code,
                    'api_key': api_key,
                    'subscription_type': subscription_type,
                    'subscription_end_date': subscription_end_date
                }
            return None
        except Exception as e:
            logger.error(f"Error creating company: {e}")
            return None
    
    @staticmethod
    def get_company_by_api_key(api_key: str) -> Optional[Dict]:
        """Get company information by API key."""
        query = """
        SELECT c.*,
               CASE 
                   WHEN c.subscription_type = 'lifetime' THEN TRUE
                   WHEN c.subscription_end_date > NOW() THEN TRUE
                   ELSE FALSE
               END as is_subscription_active
        FROM companies c
        WHERE c.api_key = %s AND c.is_active = TRUE
        """
        result = db.execute_query(query, (api_key,))
        return result[0] if result else None
    
    @staticmethod
    def update_subscription(company_id: int, subscription_type: str, admin_telegram_id: int) -> bool:
        """Update company subscription."""
        try:
            # Generate new API key
            new_api_key = CompanyManager.generate_api_key()
            
            # Calculate new end date
            subscription_end_date = None
            if subscription_type != 'lifetime':
                months = 1 if subscription_type == '1m' else 6
                subscription_end_date = datetime.now() + timedelta(days=30 * months)
            
            # Get old API key for logging
            old_key_query = "SELECT api_key FROM companies WHERE id = %s"
            old_key_result = db.execute_query(old_key_query, (company_id,))
            old_api_key = old_key_result[0]['api_key'] if old_key_result else None
            
            # Update company
            update_query = """
            UPDATE companies 
            SET api_key = %s, subscription_type = %s, subscription_start_date = NOW(),
                subscription_end_date = %s, updated_at = NOW()
            WHERE id = %s
            """
            
            if db.execute_update(update_query, (new_api_key, subscription_type, subscription_end_date, company_id)):
                # Log the API key generation
                log_query = """
                INSERT INTO api_key_logs (
                    company_id, old_api_key, new_api_key, generated_by_admin_id,
                    subscription_type, expiry_date, action_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                db.execute_update(log_query, (
                    company_id, old_api_key, new_api_key, admin_telegram_id,
                    subscription_type, subscription_end_date, 'renew'
                ))
                
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating subscription: {e}")
            return False
    
    @staticmethod
    def get_all_companies() -> List[Dict]:
        """Get all companies (for main admin)."""
        query = """
        SELECT c.*,
               CASE 
                   WHEN c.subscription_type = 'lifetime' THEN TRUE
                   WHEN c.subscription_end_date > NOW() THEN TRUE
                   ELSE FALSE
               END as is_subscription_active,
               COUNT(e.id) as employee_count
        FROM companies c
        LEFT JOIN employees e ON c.id = e.company_id AND e.status = 'active'
        WHERE c.is_active = TRUE
        GROUP BY c.id
        ORDER BY c.created_at DESC
        """
        return db.execute_query(query) or []

class EmployeeManager:
    """Manages employee-related database operations."""
    
    @staticmethod
    def add_employee(
        company_id: int,
        employee_id: str,
        first_name: str,
        last_name: str = None,
        designation: str = None,
        phone: str = None,
        email: str = None,
        joining_date: str = None,
        salary: float = None,
        department: str = None
    ) -> bool:
        """Add a new employee."""
        query = """
        INSERT INTO employees (
            company_id, employee_id, first_name, last_name, designation,
            phone, email, joining_date, salary, department
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            company_id, employee_id, first_name, last_name, designation,
            phone, email, joining_date, salary, department
        )
        
        return db.execute_update(query, params)
    
    @staticmethod
    def get_employees_by_company(company_id: int) -> List[Dict]:
        """Get all employees for a company."""
        query = """
        SELECT * FROM employees 
        WHERE company_id = %s AND status = 'active'
        ORDER BY first_name, last_name
        """
        return db.execute_query(query, (company_id,)) or []
    
    @staticmethod
    def get_employee_by_id(company_id: int, employee_id: str) -> Optional[Dict]:
        """Get employee by ID within a company."""
        query = """
        SELECT * FROM employees 
        WHERE company_id = %s AND employee_id = %s AND status = 'active'
        """
        result = db.execute_query(query, (company_id, employee_id))
        return result[0] if result else None
    
    @staticmethod
    def update_employee(
        company_id: int,
        employee_id: str,
        **kwargs
    ) -> bool:
        """Update employee information."""
        # Build dynamic update query
        allowed_fields = [
            'first_name', 'last_name', 'designation', 'phone', 'email',
            'joining_date', 'salary', 'department', 'status'
        ]
        
        update_fields = []
        params = []
        
        for field, value in kwargs.items():
            if field in allowed_fields and value is not None:
                update_fields.append(f"{field} = %s")
                params.append(value)
        
        if not update_fields:
            return False
        
        query = f"""
        UPDATE employees 
        SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
        WHERE company_id = %s AND employee_id = %s
        """
        
        params.extend([company_id, employee_id])
        return db.execute_update(query, tuple(params))
    
    @staticmethod
    def delete_employee(company_id: int, employee_id: str) -> bool:
        """Soft delete an employee (set status to terminated)."""
        return EmployeeManager.update_employee(company_id, employee_id, status='terminated')

class LogManager:
    """Manages logging and audit trail."""
    
    @staticmethod
    def log_bot_usage(
        user_telegram_id: int,
        user_type: str,
        command: str,
        company_id: int = None,
        action_details: str = None,
        success: bool = True,
        error_message: str = None
    ) -> bool:
        """Log bot usage for audit purposes."""
        query = """
        INSERT INTO bot_usage_logs (
            user_telegram_id, user_type, company_id, command,
            action_details, success, error_message
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            user_telegram_id, user_type, company_id, command,
            action_details, success, error_message
        )
        
        return db.execute_update(query, params)
    
    @staticmethod
    def add_support_message(
        from_telegram_id: int,
        from_user_type: str,
        message_text: str,
        company_id: int = None
    ) -> bool:
        """Add a support message."""
        query = """
        INSERT INTO support_messages (
            from_telegram_id, from_user_type, company_id, message_text
        ) VALUES (%s, %s, %s, %s)
        """
        
        return db.execute_update(query, (from_telegram_id, from_user_type, company_id, message_text))

class SettingsManager:
    """Manages system settings."""
    
    @staticmethod
    def get_setting(key: str) -> Optional[str]:
        """Get a system setting value."""
        query = "SELECT setting_value FROM system_settings WHERE setting_key = %s"
        result = db.execute_query(query, (key,))
        return result[0]['setting_value'] if result else None
    
    @staticmethod
    def set_setting(key: str, value: str, description: str = None) -> bool:
        """Set a system setting value."""
        query = """
        INSERT INTO system_settings (setting_key, setting_value, description)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
        setting_value = VALUES(setting_value),
        description = COALESCE(VALUES(description), description),
        updated_at = CURRENT_TIMESTAMP
        """
        
        return db.execute_update(query, (key, value, description))
    
    @staticmethod
    def get_pricing() -> Dict[str, float]:
        """Get current pricing for subscriptions."""
        return {
            '1m': float(SettingsManager.get_setting('subscription_1m_price') or '29.99'),
            '6m': float(SettingsManager.get_setting('subscription_6m_price') or '149.99'),
            'lifetime': float(SettingsManager.get_setting('subscription_lifetime_price') or '499.99')
        }

# Initialize database connection on module import
if not db.connect():
    logger.error("Failed to connect to database on module import")

