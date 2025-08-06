-- Employee Management System Database Schema
-- This schema supports multi-company employee management with subscription-based licensing

-- Create database
CREATE DATABASE IF NOT EXISTS employee_management_system;
USE employee_management_system;

-- Table for storing main admin information
CREATE TABLE main_admin (
    id INT PRIMARY KEY AUTO_INCREMENT,
    telegram_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(100),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Table for storing company information
CREATE TABLE companies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_name VARCHAR(255) NOT NULL,
    company_code VARCHAR(50) UNIQUE NOT NULL,
    owner_telegram_id BIGINT UNIQUE NOT NULL,
    owner_username VARCHAR(100),
    owner_first_name VARCHAR(100),
    owner_last_name VARCHAR(100),
    subscription_type ENUM('1m', '6m', 'lifetime') NOT NULL,
    subscription_start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    subscription_end_date TIMESTAMP NULL,
    api_key VARCHAR(255) UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_owner_telegram_id (owner_telegram_id),
    INDEX idx_api_key (api_key),
    INDEX idx_company_code (company_code)
);

-- Table for storing employee information
CREATE TABLE employees (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    employee_id VARCHAR(50) NOT NULL,
    telegram_id BIGINT UNIQUE,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100),
    full_name VARCHAR(200) GENERATED ALWAYS AS (CONCAT(first_name, ' ', COALESCE(last_name, ''))) STORED,
    designation VARCHAR(100),
    phone VARCHAR(20),
    email VARCHAR(100),
    joining_date DATE,
    salary DECIMAL(10, 2),
    department VARCHAR(100),
    status ENUM('active', 'inactive', 'terminated') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_employee_per_company (company_id, employee_id),
    INDEX idx_company_id (company_id),
    INDEX idx_telegram_id (telegram_id),
    INDEX idx_employee_id (employee_id),
    INDEX idx_status (status)
);

-- Table for storing payment transactions
CREATE TABLE payments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    transaction_id VARCHAR(255) UNIQUE NOT NULL,
    amount DECIMAL(10, 2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    subscription_type ENUM('1m', '6m', 'lifetime') NOT NULL,
    payment_method VARCHAR(50),
    payment_status ENUM('pending', 'completed', 'failed', 'refunded') DEFAULT 'pending',
    payment_gateway VARCHAR(50),
    gateway_transaction_id VARCHAR(255),
    payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    INDEX idx_company_id (company_id),
    INDEX idx_transaction_id (transaction_id),
    INDEX idx_payment_status (payment_status)
);

-- Table for storing API key generation logs
CREATE TABLE api_key_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    company_id INT NOT NULL,
    old_api_key VARCHAR(255),
    new_api_key VARCHAR(255) NOT NULL,
    generated_by_admin_id BIGINT NOT NULL,
    subscription_type ENUM('1m', '6m', 'lifetime') NOT NULL,
    expiry_date TIMESTAMP NULL,
    action_type ENUM('generate', 'renew', 'extend') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    FOREIGN KEY (generated_by_admin_id) REFERENCES main_admin(telegram_id),
    INDEX idx_company_id (company_id),
    INDEX idx_generated_by (generated_by_admin_id)
);

-- Table for storing bot usage logs
CREATE TABLE bot_usage_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_telegram_id BIGINT NOT NULL,
    user_type ENUM('main_admin', 'company_owner', 'employee') NOT NULL,
    company_id INT NULL,
    command VARCHAR(50) NOT NULL,
    action_details TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
    INDEX idx_user_telegram_id (user_telegram_id),
    INDEX idx_company_id (company_id),
    INDEX idx_command (command),
    INDEX idx_created_at (created_at)
);

-- Table for storing support messages
CREATE TABLE support_messages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    from_telegram_id BIGINT NOT NULL,
    from_user_type ENUM('company_owner', 'employee') NOT NULL,
    company_id INT NULL,
    message_text TEXT NOT NULL,
    status ENUM('open', 'in_progress', 'resolved', 'closed') DEFAULT 'open',
    admin_response TEXT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE SET NULL,
    INDEX idx_from_telegram_id (from_telegram_id),
    INDEX idx_company_id (company_id),
    INDEX idx_status (status)
);

-- Table for storing system settings
CREATE TABLE system_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(100) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- Insert default system settings
INSERT INTO system_settings (setting_key, setting_value, description) VALUES
('subscription_1m_price', '29.99', 'Price for 1-month subscription in USD'),
('subscription_6m_price', '149.99', 'Price for 6-month subscription in USD'),
('subscription_lifetime_price', '499.99', 'Price for lifetime subscription in USD'),
('max_employees_per_company', '1000', 'Maximum number of employees per company'),
('bot_version', '1.0.0', 'Current bot version'),
('maintenance_mode', 'false', 'Whether the bot is in maintenance mode');

-- Create views for easier data access

-- View for active companies with subscription details
CREATE VIEW active_companies_view AS
SELECT 
    c.id,
    c.company_name,
    c.company_code,
    c.owner_telegram_id,
    c.owner_username,
    c.owner_first_name,
    c.owner_last_name,
    c.subscription_type,
    c.subscription_start_date,
    c.subscription_end_date,
    c.api_key,
    CASE 
        WHEN c.subscription_type = 'lifetime' THEN TRUE
        WHEN c.subscription_end_date > NOW() THEN TRUE
        ELSE FALSE
    END as is_subscription_active,
    COUNT(e.id) as employee_count
FROM companies c
LEFT JOIN employees e ON c.id = e.company_id AND e.status = 'active'
WHERE c.is_active = TRUE
GROUP BY c.id;

-- View for employee details with company information
CREATE VIEW employee_details_view AS
SELECT 
    e.id,
    e.employee_id,
    e.telegram_id,
    e.first_name,
    e.last_name,
    e.full_name,
    e.designation,
    e.phone,
    e.email,
    e.joining_date,
    e.salary,
    e.department,
    e.status,
    c.company_name,
    c.company_code,
    c.owner_telegram_id as company_owner_telegram_id
FROM employees e
JOIN companies c ON e.company_id = c.id;

-- Create stored procedures for common operations

DELIMITER //

-- Procedure to check if a company's subscription is active
CREATE PROCEDURE CheckSubscriptionStatus(IN company_api_key VARCHAR(255))
BEGIN
    SELECT 
        c.id as company_id,
        c.company_name,
        c.subscription_type,
        c.subscription_end_date,
        CASE 
            WHEN c.subscription_type = 'lifetime' THEN TRUE
            WHEN c.subscription_end_date > NOW() THEN TRUE
            ELSE FALSE
        END as is_active
    FROM companies c
    WHERE c.api_key = company_api_key AND c.is_active = TRUE;
END //

-- Procedure to generate a new API key for a company
CREATE PROCEDURE GenerateAPIKey(
    IN p_company_id INT,
    IN p_subscription_type ENUM('1m', '6m', 'lifetime'),
    IN p_admin_telegram_id BIGINT,
    IN p_new_api_key VARCHAR(255)
)
BEGIN
    DECLARE old_key VARCHAR(255);
    DECLARE expiry_date TIMESTAMP;
    
    -- Get the old API key
    SELECT api_key INTO old_key FROM companies WHERE id = p_company_id;
    
    -- Calculate expiry date based on subscription type
    CASE p_subscription_type
        WHEN '1m' THEN SET expiry_date = DATE_ADD(NOW(), INTERVAL 1 MONTH);
        WHEN '6m' THEN SET expiry_date = DATE_ADD(NOW(), INTERVAL 6 MONTH);
        WHEN 'lifetime' THEN SET expiry_date = NULL;
    END CASE;
    
    -- Update company with new API key and subscription details
    UPDATE companies 
    SET 
        api_key = p_new_api_key,
        subscription_type = p_subscription_type,
        subscription_start_date = NOW(),
        subscription_end_date = expiry_date,
        is_active = TRUE,
        updated_at = NOW()
    WHERE id = p_company_id;
    
    -- Log the API key generation
    INSERT INTO api_key_logs (
        company_id, 
        old_api_key, 
        new_api_key, 
        generated_by_admin_id, 
        subscription_type, 
        expiry_date, 
        action_type
    ) VALUES (
        p_company_id, 
        old_key, 
        p_new_api_key, 
        p_admin_telegram_id, 
        p_subscription_type, 
        expiry_date, 
        'generate'
    );
END //

-- Procedure to add a new employee
CREATE PROCEDURE AddEmployee(
    IN p_company_id INT,
    IN p_employee_id VARCHAR(50),
    IN p_first_name VARCHAR(100),
    IN p_last_name VARCHAR(100),
    IN p_designation VARCHAR(100),
    IN p_phone VARCHAR(20),
    IN p_email VARCHAR(100),
    IN p_joining_date DATE,
    IN p_salary DECIMAL(10,2),
    IN p_department VARCHAR(100)
)
BEGIN
    INSERT INTO employees (
        company_id,
        employee_id,
        first_name,
        last_name,
        designation,
        phone,
        email,
        joining_date,
        salary,
        department,
        status
    ) VALUES (
        p_company_id,
        p_employee_id,
        p_first_name,
        p_last_name,
        p_designation,
        p_phone,
        p_email,
        p_joining_date,
        p_salary,
        p_department,
        'active'
    );
END //

DELIMITER ;

-- Create triggers for audit logging

DELIMITER //

-- Trigger to log employee changes
CREATE TRIGGER employee_audit_trigger
AFTER UPDATE ON employees
FOR EACH ROW
BEGIN
    INSERT INTO bot_usage_logs (
        user_telegram_id,
        user_type,
        company_id,
        command,
        action_details,
        success
    ) VALUES (
        0, -- Will be updated by application logic
        'company_owner',
        NEW.company_id,
        'edit_employee',
        CONCAT('Employee ', NEW.employee_id, ' updated'),
        TRUE
    );
END //

DELIMITER ;

-- Create indexes for performance optimization
CREATE INDEX idx_employees_company_status ON employees(company_id, status);
CREATE INDEX idx_companies_subscription_end ON companies(subscription_end_date);
CREATE INDEX idx_payments_date_status ON payments(payment_date, payment_status);
CREATE INDEX idx_usage_logs_date_command ON bot_usage_logs(created_at, command);

-- Grant permissions (adjust as needed for your deployment)
-- CREATE USER 'bot_user'@'%' IDENTIFIED BY 'secure_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON employee_management_system.* TO 'bot_user'@'%';
-- FLUSH PRIVILEGES;

