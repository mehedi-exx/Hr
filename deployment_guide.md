# Deployment Guide - Employee Management System

This guide provides step-by-step instructions for deploying the Employee Management System Telegram Bot to Render.com.

## 📋 Pre-Deployment Checklist

Before deploying, ensure you have:

- [x] Telegram Bot Token from @BotFather
- [x] GitHub repository with your code
- [x] Render.com account
- [x] MySQL database (local or cloud)
- [x] Main admin Telegram ID
- [x] All environment variables configured

## 🚀 Step-by-Step Deployment

### Step 1: Prepare Your Repository

1. **Create a GitHub Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Employee Management Bot"
   git branch -M main
   git remote add origin https://github.com/yourusername/employee-management-bot.git
   git push -u origin main
   ```

2. **Verify Required Files**
   Ensure these files are in your repository:
   - `bot.py` (main bot file)
   - `database.py` (database management)
   - `payment_handler.py` (payment processing)
   - `requirements.txt` (dependencies)
   - `database_schema.sql` (database setup)
   - `README.md` (documentation)

### Step 2: Set Up Render.com Account

1. **Create Account**
   - Go to [render.com](https://render.com)
   - Sign up with GitHub (recommended)
   - Verify your email address

2. **Connect GitHub**
   - Authorize Render to access your repositories
   - Select the employee management bot repository

### Step 3: Create Database Service

1. **Create PostgreSQL Database** (Alternative to MySQL)
   - Click "New" → "PostgreSQL"
   - Choose a name: `employee-management-db`
   - Select region closest to your users
   - Choose the free tier for testing
   - Click "Create Database"

2. **Get Database Connection Details**
   - Note the Internal Database URL
   - Note the External Database URL
   - Save these for environment variables

### Step 4: Deploy the Bot Service

1. **Create Web Service**
   - Click "New" → "Web Service"
   - Select "Build and deploy from a Git repository"
   - Choose your GitHub repository
   - Click "Connect"

2. **Configure Service Settings**
   ```
   Name: employee-management-bot
   Region: [Choose closest to your users]
   Branch: main
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: python bot.py
   ```

3. **Set Environment Variables**
   Add these environment variables in Render:
   
   ```env
   BOT_TOKEN=your_telegram_bot_token
   DB_HOST=your_database_host
   DB_PORT=5432
   DB_USER=your_database_user
   DB_PASSWORD=your_database_password
   DB_NAME=your_database_name
   MAIN_ADMIN_TELEGRAM_ID=your_telegram_id
   SECRET_KEY=your_secret_key_here
   PAYMENT_GATEWAY_API_KEY=your_payment_key
   PAYMENT_WEBHOOK_SECRET=your_webhook_secret
   DEBUG=False
   LOG_LEVEL=INFO
   ```

4. **Deploy the Service**
   - Click "Create Web Service"
   - Wait for the build to complete
   - Monitor the logs for any errors

### Step 5: Database Setup

1. **Connect to Database**
   Use the database connection details to run the schema:
   
   ```bash
   # If using PostgreSQL, convert MySQL schema to PostgreSQL
   # Or use a MySQL database service instead
   ```

2. **Initialize Database Schema**
   - Connect to your database using a client
   - Run the `database_schema.sql` file
   - Verify all tables are created

3. **Add Initial Data**
   ```sql
   -- Add your Telegram ID as main admin
   INSERT INTO main_admin (telegram_id, username, first_name) 
   VALUES (YOUR_TELEGRAM_ID, 'your_username', 'Your Name');
   ```

### Step 6: Configure Telegram Bot

1. **Set Webhook (Optional)**
   If you need webhook functionality for payments:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook" \
        -H "Content-Type: application/json" \
        -d '{"url": "https://your-render-app.onrender.com/webhook"}'
   ```

2. **Test Bot Commands**
   - Send `/start` to your bot
   - Verify it responds correctly
   - Test admin commands with your admin account

### Step 7: Verify Deployment

1. **Check Service Status**
   - Go to Render dashboard
   - Verify service is "Live"
   - Check logs for any errors

2. **Test Bot Functionality**
   - Test user registration flow
   - Test employee management features
   - Test admin commands
   - Verify database operations

3. **Monitor Performance**
   - Check response times
   - Monitor memory usage
   - Review error logs

## 🔧 Environment Variables Reference

### Required Variables
```env
BOT_TOKEN=              # From @BotFather
DB_HOST=                # Database host
DB_PORT=                # Database port (3306 for MySQL, 5432 for PostgreSQL)
DB_USER=                # Database username
DB_PASSWORD=            # Database password
DB_NAME=                # Database name
MAIN_ADMIN_TELEGRAM_ID= # Your Telegram user ID
```

### Optional Variables
```env
SECRET_KEY=             # For API key generation
PAYMENT_GATEWAY_API_KEY=# Payment gateway API key
PAYMENT_WEBHOOK_SECRET= # Webhook verification secret
DEBUG=False             # Set to False for production
LOG_LEVEL=INFO          # Logging level
```

## 🐛 Troubleshooting

### Common Deployment Issues

**Build Fails**
```bash
# Check requirements.txt format
# Ensure all dependencies are listed
# Verify Python version compatibility
```

**Database Connection Errors**
```bash
# Verify database URL format
# Check firewall settings
# Ensure database service is running
```

**Bot Not Responding**
```bash
# Check bot token validity
# Verify webhook configuration
# Review application logs
```

**Memory Issues**
```bash
# Monitor memory usage in Render dashboard
# Optimize database queries
# Consider upgrading to paid plan
```

### Debugging Steps

1. **Check Render Logs**
   ```bash
   # In Render dashboard, go to your service
   # Click on "Logs" tab
   # Look for error messages
   ```

2. **Test Database Connection**
   ```python
   # Add this to your bot.py for testing
   from database import db
   if db.connect():
       print("Database connected successfully")
   else:
       print("Database connection failed")
   ```

3. **Verify Environment Variables**
   ```python
   import os
   print("BOT_TOKEN:", "✓" if os.getenv('BOT_TOKEN') else "✗")
   print("DB_HOST:", "✓" if os.getenv('DB_HOST') else "✗")
   # Add other variables
   ```

## 📊 Monitoring & Maintenance

### Health Checks

1. **Set Up Monitoring**
   - Use Render's built-in monitoring
   - Set up uptime monitoring (UptimeRobot, etc.)
   - Monitor database performance

2. **Regular Maintenance**
   - Review logs weekly
   - Monitor database size
   - Update dependencies monthly
   - Backup database regularly

### Performance Optimization

1. **Database Optimization**
   ```sql
   -- Add indexes for frequently queried columns
   CREATE INDEX idx_companies_owner ON companies(owner_telegram_id);
   CREATE INDEX idx_employees_company ON employees(company_id);
   ```

2. **Code Optimization**
   - Use connection pooling
   - Implement caching where appropriate
   - Optimize database queries

## 🔄 Updates & Maintenance

### Deploying Updates

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Update: description of changes"
   git push origin main
   ```

2. **Automatic Deployment**
   - Render automatically deploys from GitHub
   - Monitor deployment in Render dashboard
   - Verify functionality after deployment

### Database Migrations

1. **Schema Changes**
   ```sql
   -- Create migration scripts
   -- Test on staging environment first
   -- Apply to production during low-traffic periods
   ```

2. **Data Backups**
   ```bash
   # Regular database backups
   # Store backups securely
   # Test restore procedures
   ```

## 🔐 Security Considerations

### Production Security

1. **Environment Variables**
   - Never commit secrets to GitHub
   - Use strong passwords
   - Rotate API keys regularly

2. **Database Security**
   - Use SSL connections
   - Implement proper access controls
   - Regular security updates

3. **Bot Security**
   - Validate all user inputs
   - Implement rate limiting
   - Monitor for suspicious activity

## 📞 Support

If you encounter issues during deployment:

1. Check the troubleshooting section above
2. Review Render.com documentation
3. Check GitHub repository issues
4. Contact support through the bot's support system

---

**Deployment completed successfully! Your Employee Management Bot is now live! 🎉**

