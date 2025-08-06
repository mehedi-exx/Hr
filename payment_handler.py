"""
Payment integration module for the Employee Management System.
This module handles payment processing and webhook notifications.
"""

import os
import hashlib
import hmac
import json
import logging
from typing import Dict, Optional, Any
from datetime import datetime
from dotenv import load_dotenv

from database import db, CompanyManager, LogManager, SettingsManager

# Load environment variables
load_dotenv('bot.env')

logger = logging.getLogger(__name__)

class PaymentProcessor:
    """Handles payment processing and validation."""
    
    def __init__(self):
        self.webhook_secret = os.getenv('PAYMENT_WEBHOOK_SECRET', 'default_secret')
        self.api_key = os.getenv('PAYMENT_GATEWAY_API_KEY', 'test_key')
        
    def verify_webhook_signature(self, payload: str, signature: str) -> bool:
        """Verify webhook signature for security."""
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
        except Exception as e:
            logger.error(f"Error verifying webhook signature: {e}")
            return False
    
    def create_payment_record(
        self,
        company_id: int,
        transaction_id: str,
        amount: float,
        subscription_type: str,
        payment_method: str = 'unknown',
        currency: str = 'USD'
    ) -> bool:
        """Create a payment record in the database."""
        query = """
        INSERT INTO payments (
            company_id, transaction_id, amount, currency, subscription_type,
            payment_method, payment_status, payment_gateway
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            company_id, transaction_id, amount, currency, subscription_type,
            payment_method, 'pending', 'placeholder_gateway'
        )
        
        return db.execute_update(query, params)
    
    def update_payment_status(
        self,
        transaction_id: str,
        status: str,
        gateway_transaction_id: str = None
    ) -> bool:
        """Update payment status."""
        query = """
        UPDATE payments 
        SET payment_status = %s, gateway_transaction_id = %s, updated_at = CURRENT_TIMESTAMP
        WHERE transaction_id = %s
        """
        
        return db.execute_update(query, (status, gateway_transaction_id, transaction_id))
    
    def get_payment_by_transaction_id(self, transaction_id: str) -> Optional[Dict]:
        """Get payment record by transaction ID."""
        query = "SELECT * FROM payments WHERE transaction_id = %s"
        result = db.execute_query(query, (transaction_id,))
        return result[0] if result else None
    
    def process_successful_payment(self, payment_data: Dict) -> bool:
        """Process a successful payment and activate subscription."""
        try:
            transaction_id = payment_data['transaction_id']
            company_id = payment_data['company_id']
            subscription_type = payment_data['subscription_type']
            
            # Update payment status
            self.update_payment_status(transaction_id, 'completed')
            
            # Get company info
            company_query = "SELECT * FROM companies WHERE id = %s"
            company_result = db.execute_query(company_query, (company_id,))
            
            if not company_result:
                logger.error(f"Company not found for payment: {company_id}")
                return False
            
            company = company_result[0]
            
            # Update subscription (this will generate new API key)
            success = CompanyManager.update_subscription(
                company_id, 
                subscription_type, 
                admin_telegram_id=0  # System generated
            )
            
            if success:
                # Log the successful payment
                LogManager.log_bot_usage(
                    company['owner_telegram_id'], 'company_owner', 'payment_completed',
                    company_id=company_id,
                    action_details=f"Payment completed for {subscription_type} subscription",
                    success=True
                )
                
                logger.info(f"Payment processed successfully: {transaction_id}")
                return True
            else:
                logger.error(f"Failed to update subscription for payment: {transaction_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing payment: {e}")
            return False

class PaymentGatewayMock:
    """Mock payment gateway for demonstration purposes."""
    
    @staticmethod
    def create_payment_link(
        amount: float,
        currency: str,
        subscription_type: str,
        company_id: int,
        return_url: str = None
    ) -> Dict[str, Any]:
        """Create a mock payment link."""
        import uuid
        
        transaction_id = str(uuid.uuid4())
        
        # In a real implementation, this would call the actual payment gateway API
        payment_link = f"https://mock-payment-gateway.com/pay/{transaction_id}"
        
        return {
            'transaction_id': transaction_id,
            'payment_url': payment_link,
            'amount': amount,
            'currency': currency,
            'subscription_type': subscription_type,
            'company_id': company_id,
            'expires_at': datetime.now().isoformat(),
            'status': 'pending'
        }
    
    @staticmethod
    def verify_payment(transaction_id: str) -> Dict[str, Any]:
        """Mock payment verification."""
        # In a real implementation, this would verify with the payment gateway
        return {
            'transaction_id': transaction_id,
            'status': 'completed',
            'verified': True,
            'gateway_transaction_id': f"gw_{transaction_id[:8]}"
        }

class SubscriptionManager:
    """Manages subscription-related operations."""
    
    @staticmethod
    def get_subscription_price(subscription_type: str) -> float:
        """Get subscription price."""
        pricing = SettingsManager.get_pricing()
        return pricing.get(subscription_type, 0.0)
    
    @staticmethod
    def create_subscription_payment(
        company_id: int,
        subscription_type: str,
        payment_method: str = 'online'
    ) -> Optional[Dict]:
        """Create a subscription payment."""
        try:
            amount = SubscriptionManager.get_subscription_price(subscription_type)
            
            if amount <= 0:
                logger.error(f"Invalid subscription type: {subscription_type}")
                return None
            
            # Create payment link using mock gateway
            payment_data = PaymentGatewayMock.create_payment_link(
                amount=amount,
                currency='USD',
                subscription_type=subscription_type,
                company_id=company_id
            )
            
            # Create payment record
            processor = PaymentProcessor()
            success = processor.create_payment_record(
                company_id=company_id,
                transaction_id=payment_data['transaction_id'],
                amount=amount,
                subscription_type=subscription_type,
                payment_method=payment_method
            )
            
            if success:
                return payment_data
            else:
                logger.error("Failed to create payment record")
                return None
                
        except Exception as e:
            logger.error(f"Error creating subscription payment: {e}")
            return None
    
    @staticmethod
    def handle_payment_webhook(webhook_data: Dict) -> bool:
        """Handle payment webhook notification."""
        try:
            processor = PaymentProcessor()
            
            # Extract relevant data from webhook
            transaction_id = webhook_data.get('transaction_id')
            status = webhook_data.get('status')
            gateway_transaction_id = webhook_data.get('gateway_transaction_id')
            
            if not transaction_id or not status:
                logger.error("Invalid webhook data: missing transaction_id or status")
                return False
            
            # Get payment record
            payment = processor.get_payment_by_transaction_id(transaction_id)
            if not payment:
                logger.error(f"Payment not found: {transaction_id}")
                return False
            
            # Update payment status
            processor.update_payment_status(transaction_id, status, gateway_transaction_id)
            
            # If payment is successful, activate subscription
            if status == 'completed':
                return processor.process_successful_payment(payment)
            
            return True
            
        except Exception as e:
            logger.error(f"Error handling payment webhook: {e}")
            return False

# Utility functions for bot integration
def format_payment_info(payment_data: Dict) -> str:
    """Format payment information for display."""
    info = f"💳 **Payment Information**\n\n"
    info += f"🆔 **Transaction ID:** `{payment_data['transaction_id']}`\n"
    info += f"💰 **Amount:** ${payment_data['amount']:.2f} {payment_data['currency']}\n"
    info += f"📅 **Subscription:** {payment_data['subscription_type'].upper()}\n"
    info += f"🔗 **Payment Link:** [Click here to pay]({payment_data['payment_url']})\n\n"
    info += f"⚠️ **Note:** Complete the payment to activate your subscription."
    
    return info

def get_pricing_text() -> str:
    """Get formatted pricing text."""
    pricing = SettingsManager.get_pricing()
    
    text = "💳 **Subscription Pricing**\n\n"
    text += f"📅 **1 Month:** ${pricing['1m']:.2f}\n"
    text += f"   • Perfect for trying out the system\n"
    text += f"   • All features included\n\n"
    
    text += f"📅 **6 Months:** ${pricing['6m']:.2f}\n"
    text += f"   • Save ${(pricing['1m'] * 6 - pricing['6m']):.2f} compared to monthly\n"
    text += f"   • Best for growing businesses\n\n"
    
    text += f"♾️ **Lifetime:** ${pricing['lifetime']:.2f}\n"
    text += f"   • One-time payment\n"
    text += f"   • Never worry about renewals\n"
    text += f"   • Best value for established companies\n\n"
    
    text += "✅ **All plans include:**\n"
    text += "• Unlimited employee records\n"
    text += "• Full data management\n"
    text += "• 24/7 support\n"
    text += "• Regular updates"
    
    return text

# Test functions for development
def test_payment_flow():
    """Test the payment flow with mock data."""
    logger.info("Testing payment flow...")
    
    # Create a test payment
    payment_data = SubscriptionManager.create_subscription_payment(
        company_id=1,
        subscription_type='1m'
    )
    
    if payment_data:
        logger.info(f"Payment created: {payment_data['transaction_id']}")
        
        # Simulate webhook notification
        webhook_data = {
            'transaction_id': payment_data['transaction_id'],
            'status': 'completed',
            'gateway_transaction_id': f"gw_{payment_data['transaction_id'][:8]}"
        }
        
        success = SubscriptionManager.handle_payment_webhook(webhook_data)
        logger.info(f"Webhook processed: {success}")
        
        return success
    else:
        logger.error("Failed to create test payment")
        return False

if __name__ == "__main__":
    # Run test if executed directly
    logging.basicConfig(level=logging.INFO)
    test_payment_flow()

