# Employee Management System - Telegram Bot

A comprehensive Telegram bot-based Employee Management System with subscription-based licensing, multi-company support, and complete deployment infrastructure.

## 🚀 Features

### Core Functionality
- **Telegram Bot Interface**: Complete employee management through Telegram (no web interface needed)
- **Multi-Company Support**: Each company operates with isolated data and separate subscriptions
- **Role-Based Access Control**: Three distinct user roles with appropriate permissions
- **Subscription Management**: Flexible pricing with 1-month, 6-month, and lifetime options
- **Payment Integration**: Automated payment processing with admin notifications
- **Comprehensive Employee Data**: Full CRUD operations for employee records

### User Roles

#### 🧑‍💼 Main Admin (Bot Owner)
- Generate and manage API keys for companies
- View all companies and their subscription status
- Monitor system statistics and settings
- Receive payment notifications
- Full system oversight

#### 🏢 Company Owner (HR/Admin)
- Purchase and manage company subscriptions
- Add, edit, view, and manage employee records
- Access only their company's data
- Contact support when needed
- View subscription status and renewal options

#### 👷 Employee
- View their own profile information
- Access personal employment data
- Cannot message admins directly (controlled communication)
- Limited to read-only access of personal data

## 🛠️ Technology Stack

- **Backend**: Python 3.11+ with aiogram (Telegram Bot API)
- **Database**: MySQL 8.0+ with comprehensive schema
- **Deployment**: Render.com for hosting
- **Repository**: GitHub for version control
- **Documentation**: GitHub Pages for public documentation

## 📋 Prerequisites

- Python 3.11 or higher
- MySQL 8.0 or higher
- Telegram Bot Token (from @BotFather)
- Render.com account (for deployment)
- GitHub account (for repository hosting)

## 🔧 Installation & Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd employee-management-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Database Setup

```bash
# Start MySQL service
sudo systemctl start mysql

# Create database and tables
mysql -u root -p < database_schema.sql
```

### 4. Environment Configuration

Create a `bot.env` file with the following configuration:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_from_botfather

# Database Configuration
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=employee_management_system

# Main Admin Configuration
MAIN_ADMIN_TELEGRAM_ID=your_telegram_user_id

# Security Configuration
SECRET_KEY=your_secret_key_for_api_generation

# Payment Configuration (optional)
PAYMENT_GATEWAY_API_KEY=your_payment_gateway_api_key
PAYMENT_WEBHOOK_SECRET=your_webhook_secret

# Application Configuration
DEBUG=True
LOG_LEVEL=INFO
```

### 5. Run the Bot

```bash
python bot.py
```

## 🧪 Testing

Run the comprehensive test suite:

```bash
python test_bot.py
```

The test suite includes:
- Database connection tests
- User management tests
- Company management tests
- Employee management tests
- Payment processing tests
- Integration tests

## 🚀 Deployment to Render.com

### 1. Prepare for Deployment

Ensure your code is pushed to GitHub:

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Deploy on Render.com

1. Create a new account on [Render.com](https://render.com)
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
5. Add environment variables from your `bot.env` file
6. Deploy the service

### 3. Database Setup on Render

1. Create a new PostgreSQL or MySQL database on Render
2. Update your environment variables with the database URL
3. Run the database schema setup

## 📱 Bot Commands

### General Commands
- `/start` - Initialize bot interaction and registration
- `/buy` - View subscription pricing and purchase options
- `/support` - Send a message to admin support

### Company Owner Commands
- `👥 Employees` - List all company employees
- `➕ Add Employee` - Add a new employee
- `✏️ Edit Employee` - Edit existing employee data
- `👤 View Employee` - View specific employee details
- `💳 Buy Subscription` - Purchase or renew subscription

### Main Admin Commands
- `/genkey <company_id> <subscription_type>` - Generate API key
- `📊 All Companies` - View all registered companies
- `🔑 Generate API Key` - API key generation instructions
- `📈 System Stats` - View system statistics
- `⚙️ Settings` - View system settings

### Employee Commands
- `👤 My Profile` - View personal employment information
- `🆘 Support` - Contact support (limited access)

## 💳 Subscription Model

### Pricing Tiers
- **1 Month**: $29.99 - Perfect for trying the system
- **6 Months**: $149.99 - Best for growing businesses (save $30)
- **Lifetime**: $499.99 - One-time payment, never expires

### Features Included in All Plans
- Unlimited employee records
- Full data management capabilities
- 24/7 support access
- Regular system updates
- Secure data isolation

## 🔐 Security Features

- **Role-based access control** with strict permission enforcement
- **Company data isolation** - each company can only access their own data
- **API key-based licensing** with automatic expiration
- **Secure payment processing** with webhook verification
- **Audit logging** for all user actions
- **Input validation** and SQL injection prevention

## 📊 Database Schema

The system uses a comprehensive MySQL schema with the following key tables:

- `main_admin` - Main administrator accounts
- `companies` - Company registration and subscription data
- `employees` - Employee records with full details
- `payments` - Payment transaction history
- `api_key_logs` - API key generation audit trail
- `bot_usage_logs` - User action logging
- `support_messages` - Support ticket system
- `system_settings` - Configurable system parameters

## 🔄 Workflow Examples

### New Company Registration
1. User sends `/start` to bot
2. User enters company name
3. User selects subscription type
4. Payment link is generated
5. Admin receives notification
6. Upon payment completion, subscription is activated
7. Company can start managing employees

### Employee Management
1. Company owner uses `➕ Add Employee`
2. Bot guides through employee data entry
3. Employee record is created in company's isolated data
4. Company owner can view, edit, or manage the employee
5. All actions are logged for audit purposes

### Subscription Renewal
1. Company owner uses `/buy` command
2. Current subscription status is displayed
3. User selects new subscription type
4. Payment is processed
5. Subscription is automatically renewed
6. Both admin and company owner receive confirmation

## 🆘 Support & Troubleshooting

### Common Issues

**Bot not responding:**
- Check if the bot token is correct
- Verify the bot is running and deployed
- Check database connectivity

**Database connection errors:**
- Verify MySQL service is running
- Check database credentials in `bot.env`
- Ensure database schema is properly created

**Payment issues:**
- Verify payment gateway configuration
- Check webhook endpoints are accessible
- Review payment logs in the database

### Getting Help

1. Use the `/support` command in the bot
2. Check the documentation website
3. Review the GitHub repository issues
4. Contact the main admin directly

## 📈 Monitoring & Analytics

The system provides comprehensive monitoring through:

- **Usage logs** - Track all user interactions
- **Payment tracking** - Monitor subscription revenue
- **Company statistics** - View growth metrics
- **Error logging** - Debug system issues
- **Performance metrics** - Monitor system health

## 🔮 Future Enhancements

Potential improvements and features:

- **Web dashboard** for advanced analytics
- **Mobile app** for enhanced user experience
- **Advanced reporting** with data visualization
- **Integration APIs** for third-party systems
- **Multi-language support** for global deployment
- **Advanced payment gateways** (Stripe, PayPal, etc.)
- **Backup and restore** functionality
- **Advanced user permissions** and roles

## 📄 License

This project is proprietary software. All rights reserved.

## 🤝 Contributing

This is a private project. For feature requests or bug reports, please contact the main administrator.

## 📞 Contact

For technical support or business inquiries, please use the bot's support system or contact the main administrator directly.

---

**Built with ❤️ for efficient employee management through Telegram**

