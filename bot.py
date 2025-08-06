"""
Main Telegram Bot for Employee Management System
"""

import asyncio
import logging
import os
from typing import Dict, Any, Optional
from datetime import datetime

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

from database import (
    UserManager, CompanyManager, EmployeeManager, LogManager, SettingsManager, db
)

# Load environment variables
load_dotenv('bot.env')

# Configure logging
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
MAIN_ADMIN_ID = int(os.getenv('MAIN_ADMIN_TELEGRAM_ID', '0'))

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required in bot.env file")

if MAIN_ADMIN_ID == 0:
    logger.warning("MAIN_ADMIN_TELEGRAM_ID not set in bot.env file")

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# FSM States
class RegistrationStates(StatesGroup):
    waiting_for_company_name = State()
    waiting_for_subscription_type = State()

class EmployeeStates(StatesGroup):
    waiting_for_employee_id = State()
    waiting_for_first_name = State()
    waiting_for_last_name = State()
    waiting_for_designation = State()
    waiting_for_phone = State()
    waiting_for_email = State()
    waiting_for_joining_date = State()
    waiting_for_salary = State()
    waiting_for_department = State()

class EditEmployeeStates(StatesGroup):
    waiting_for_employee_id = State()
    waiting_for_field_selection = State()
    waiting_for_new_value = State()

class ViewEmployeeStates(StatesGroup):
    waiting_for_employee_id = State()

class AdminStates(StatesGroup):
    waiting_for_company_id = State()
    waiting_for_subscription_type = State()

class SupportStates(StatesGroup):
    waiting_for_message = State()

# Utility functions
def create_subscription_keyboard() -> InlineKeyboardMarkup:
    """Create subscription selection keyboard."""
    pricing = SettingsManager.get_pricing()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"1 Month - ${pricing['1m']}", callback_data="sub_1m")],
        [InlineKeyboardButton(text=f"6 Months - ${pricing['6m']}", callback_data="sub_6m")],
        [InlineKeyboardButton(text=f"Lifetime - ${pricing['lifetime']}", callback_data="sub_lifetime")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel")]
    ])
    return keyboard

def create_main_menu_keyboard(user_role: str) -> ReplyKeyboardMarkup:
    """Create main menu keyboard based on user role."""
    if user_role == 'main_admin':
        buttons = [
            [KeyboardButton(text="📊 All Companies"), KeyboardButton(text="🔑 Generate API Key")],
            [KeyboardButton(text="📈 System Stats"), KeyboardButton(text="⚙️ Settings")]
        ]
    elif user_role == 'company_owner':
        buttons = [
            [KeyboardButton(text="👥 Employees"), KeyboardButton(text="➕ Add Employee")],
            [KeyboardButton(text="✏️ Edit Employee"), KeyboardButton(text="👤 View Employee")],
            [KeyboardButton(text="💳 Buy Subscription"), KeyboardButton(text="🆘 Support")]
        ]
    else:  # employee
        buttons = [
            [KeyboardButton(text="👤 My Profile"), KeyboardButton(text="🆘 Support")]
        ]
    
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def format_employee_info(employee: Dict) -> str:
    """Format employee information for display."""
    info = f"👤 **Employee Information**\n\n"
    info += f"🆔 **ID:** {employee['employee_id']}\n"
    info += f"👤 **Name:** {employee['first_name']}"
    if employee['last_name']:
        info += f" {employee['last_name']}"
    info += "\n"
    
    if employee['designation']:
        info += f"💼 **Designation:** {employee['designation']}\n"
    if employee['department']:
        info += f"🏢 **Department:** {employee['department']}\n"
    if employee['phone']:
        info += f"📞 **Phone:** {employee['phone']}\n"
    if employee['email']:
        info += f"📧 **Email:** {employee['email']}\n"
    if employee['joining_date']:
        info += f"📅 **Joining Date:** {employee['joining_date']}\n"
    if employee['salary']:
        info += f"💰 **Salary:** ${employee['salary']:,.2f}\n"
    
    info += f"📊 **Status:** {employee['status'].title()}\n"
    info += f"📅 **Added:** {employee['created_at'].strftime('%Y-%m-%d')}"
    
    return info

def format_company_info(company: Dict) -> str:
    """Format company information for display."""
    info = f"🏢 **Company Information**\n\n"
    info += f"🏢 **Name:** {company['company_name']}\n"
    info += f"🆔 **Code:** {company['company_code']}\n"
    info += f"👤 **Owner:** {company['owner_first_name'] or 'N/A'}"
    if company['owner_last_name']:
        info += f" {company['owner_last_name']}"
    info += f" (@{company['owner_username'] or 'N/A'})\n"
    info += f"📅 **Subscription:** {company['subscription_type'].upper()}\n"
    
    if company['subscription_end_date']:
        info += f"⏰ **Expires:** {company['subscription_end_date'].strftime('%Y-%m-%d %H:%M')}\n"
    else:
        info += f"⏰ **Expires:** Never (Lifetime)\n"
    
    status = "✅ Active" if company.get('is_subscription_active') else "❌ Expired"
    info += f"📊 **Status:** {status}\n"
    
    if 'employee_count' in company:
        info += f"👥 **Employees:** {company['employee_count']}\n"
    
    info += f"📅 **Created:** {company['created_at'].strftime('%Y-%m-%d')}"
    
    return info

# Command handlers
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    """Handle /start command."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    # Log the interaction
    LogManager.log_bot_usage(
        user_id, user_role, '/start',
        company_id=user_data.get('company_id') if user_data else None
    )
    
    if user_role == 'main_admin':
        await message.answer(
            "🔧 **Main Admin Panel**\n\n"
            "Welcome to the Employee Management System admin panel. "
            "You can manage all companies and generate API keys.",
            reply_markup=create_main_menu_keyboard('main_admin'),
            parse_mode='Markdown'
        )
    
    elif user_role == 'company_owner':
        company_info = user_data
        if company_info['is_subscription_active']:
            await message.answer(
                f"🏢 **Welcome to {company_info['company_name']}**\n\n"
                f"Your subscription is active until: "
                f"{'Never (Lifetime)' if company_info['subscription_type'] == 'lifetime' else company_info['subscription_end_date'].strftime('%Y-%m-%d')}\n\n"
                "Use the menu below to manage your employees.",
                reply_markup=create_main_menu_keyboard('company_owner'),
                parse_mode='Markdown'
            )
        else:
            await message.answer(
                "⚠️ **Subscription Expired**\n\n"
                "Your subscription has expired. Please purchase a new subscription to continue using the bot.",
                reply_markup=create_subscription_keyboard(),
                parse_mode='Markdown'
            )
    
    elif user_role == 'employee':
        employee_info = user_data
        await message.answer(
            f"👋 **Welcome {employee_info['first_name']}!**\n\n"
            f"Company: {employee_info['company_name']}\n"
            f"Employee ID: {employee_info['employee_id']}\n\n"
            "Use the menu below to access your information.",
            reply_markup=create_main_menu_keyboard('employee'),
            parse_mode='Markdown'
        )
    
    else:
        # New user - start registration
        await message.answer(
            "👋 **Welcome to Employee Management System!**\n\n"
            "To get started, please enter your company name:",
            parse_mode='Markdown'
        )
        await state.set_state(RegistrationStates.waiting_for_company_name)

@dp.message(RegistrationStates.waiting_for_company_name)
async def process_company_name(message: types.Message, state: FSMContext):
    """Process company name during registration."""
    company_name = message.text.strip()
    
    if len(company_name) < 2:
        await message.answer("Company name must be at least 2 characters long. Please try again:")
        return
    
    await state.update_data(company_name=company_name)
    await message.answer(
        f"🏢 **Company:** {company_name}\n\n"
        "Please select your subscription type:",
        reply_markup=create_subscription_keyboard(),
        parse_mode='Markdown'
    )
    await state.set_state(RegistrationStates.waiting_for_subscription_type)

@dp.callback_query(F.data.startswith("sub_"))
async def process_subscription_selection(callback: types.CallbackQuery, state: FSMContext):
    """Process subscription type selection."""
    subscription_type = callback.data.split("_")[1]
    
    if subscription_type == "cancel":
        await callback.message.edit_text("Registration cancelled.")
        await state.clear()
        return
    
    data = await state.get_data()
    company_name = data.get('company_name')
    
    user = callback.from_user
    
    # Create company
    company = CompanyManager.create_company(
        company_name=company_name,
        owner_telegram_id=user.id,
        owner_username=user.username,
        owner_first_name=user.first_name,
        owner_last_name=user.last_name,
        subscription_type=subscription_type
    )
    
    if company:
        # Notify main admin
        if MAIN_ADMIN_ID:
            try:
                pricing = SettingsManager.get_pricing()
                admin_message = (
                    f"🆕 **New Company Registration**\n\n"
                    f"🏢 **Company:** {company_name}\n"
                    f"👤 **Owner:** {user.first_name or 'N/A'} {user.last_name or ''} (@{user.username or 'N/A'})\n"
                    f"📅 **Subscription:** {subscription_type.upper()}\n"
                    f"💰 **Amount:** ${pricing[subscription_type]}\n"
                    f"🆔 **Company Code:** {company['company_code']}\n"
                    f"🔑 **API Key:** `{company['api_key']}`\n\n"
                    f"Please generate the API key using /genkey command."
                )
                await bot.send_message(MAIN_ADMIN_ID, admin_message, parse_mode='Markdown')
            except Exception as e:
                logger.error(f"Failed to notify admin: {e}")
        
        await callback.message.edit_text(
            f"✅ **Registration Successful!**\n\n"
            f"🏢 **Company:** {company_name}\n"
            f"🆔 **Company Code:** {company['company_code']}\n"
            f"📅 **Subscription:** {subscription_type.upper()}\n\n"
            f"⚠️ **Important:** Your subscription is pending activation. "
            f"The admin will activate it shortly.\n\n"
            f"You will receive a confirmation message once activated.",
            parse_mode='Markdown'
        )
        
        # Log the registration
        LogManager.log_bot_usage(
            user.id, 'company_owner', 'registration',
            company_id=company['id'],
            action_details=f"Registered company: {company_name}",
            success=True
        )
    else:
        await callback.message.edit_text(
            "❌ **Registration Failed**\n\n"
            "There was an error creating your company. Please try again later or contact support."
        )
    
    await state.clear()

@dp.message(Command("buy"))
async def cmd_buy(message: types.Message):
    """Handle /buy command."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role not in ['company_owner', 'unknown']:
        await message.answer("❌ This command is only available for company owners.")
        return
    
    pricing = SettingsManager.get_pricing()
    
    price_text = (
        "💳 **Subscription Pricing**\n\n"
        f"📅 **1 Month:** ${pricing['1m']}\n"
        f"📅 **6 Months:** ${pricing['6m']} (Save 25%!)\n"
        f"♾️ **Lifetime:** ${pricing['lifetime']} (Best Value!)\n\n"
        "Select your preferred subscription:"
    )
    
    await message.answer(
        price_text,
        reply_markup=create_subscription_keyboard(),
        parse_mode='Markdown'
    )

@dp.message(F.text == "👥 Employees")
async def show_employees(message: types.Message):
    """Show all employees for company owner."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role != 'company_owner':
        await message.answer("❌ Access denied. This feature is for company owners only.")
        return
    
    if not user_data['is_subscription_active']:
        await message.answer("⚠️ Your subscription has expired. Please renew to access this feature.")
        return
    
    employees = EmployeeManager.get_employees_by_company(user_data['id'])
    
    if not employees:
        await message.answer(
            "👥 **No Employees Found**\n\n"
            "You haven't added any employees yet. Use 'Add Employee' to get started."
        )
        return
    
    employee_list = "👥 **Company Employees**\n\n"
    for i, emp in enumerate(employees, 1):
        employee_list += f"{i}. **{emp['first_name']}"
        if emp['last_name']:
            employee_list += f" {emp['last_name']}"
        employee_list += f"** (ID: {emp['employee_id']})\n"
        if emp['designation']:
            employee_list += f"   💼 {emp['designation']}\n"
        if emp['department']:
            employee_list += f"   🏢 {emp['department']}\n"
        employee_list += "\n"
    
    employee_list += f"**Total Employees:** {len(employees)}"
    
    await message.answer(employee_list, parse_mode='Markdown')
    
    # Log the action
    LogManager.log_bot_usage(
        user_id, 'company_owner', 'view_employees',
        company_id=user_data['id'],
        action_details=f"Viewed {len(employees)} employees"
    )

@dp.message(F.text == "➕ Add Employee")
async def start_add_employee(message: types.Message, state: FSMContext):
    """Start adding a new employee."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role != 'company_owner':
        await message.answer("❌ Access denied. This feature is for company owners only.")
        return
    
    if not user_data['is_subscription_active']:
        await message.answer("⚠️ Your subscription has expired. Please renew to access this feature.")
        return
    
    await state.update_data(company_id=user_data['id'])
    await message.answer(
        "➕ **Add New Employee**\n\n"
        "Please enter the employee ID (must be unique within your company):",
        parse_mode='Markdown'
    )
    await state.set_state(EmployeeStates.waiting_for_employee_id)

@dp.message(EmployeeStates.waiting_for_employee_id)
async def process_employee_id(message: types.Message, state: FSMContext):
    """Process employee ID input."""
    employee_id = message.text.strip()
    data = await state.get_data()
    company_id = data['company_id']
    
    # Check if employee ID already exists
    existing = EmployeeManager.get_employee_by_id(company_id, employee_id)
    if existing:
        await message.answer(
            f"❌ Employee ID '{employee_id}' already exists. Please choose a different ID:"
        )
        return
    
    await state.update_data(employee_id=employee_id)
    await message.answer("👤 Please enter the employee's first name:")
    await state.set_state(EmployeeStates.waiting_for_first_name)

@dp.message(EmployeeStates.waiting_for_first_name)
async def process_first_name(message: types.Message, state: FSMContext):
    """Process first name input."""
    first_name = message.text.strip()
    
    if len(first_name) < 1:
        await message.answer("First name cannot be empty. Please try again:")
        return
    
    await state.update_data(first_name=first_name)
    await message.answer("👤 Please enter the employee's last name (or type 'skip' to skip):")
    await state.set_state(EmployeeStates.waiting_for_last_name)

@dp.message(EmployeeStates.waiting_for_last_name)
async def process_last_name(message: types.Message, state: FSMContext):
    """Process last name input."""
    last_name = message.text.strip() if message.text.strip().lower() != 'skip' else None
    
    await state.update_data(last_name=last_name)
    await message.answer("💼 Please enter the employee's designation (or type 'skip' to skip):")
    await state.set_state(EmployeeStates.waiting_for_designation)

@dp.message(EmployeeStates.waiting_for_designation)
async def process_designation(message: types.Message, state: FSMContext):
    """Process designation input."""
    designation = message.text.strip() if message.text.strip().lower() != 'skip' else None
    
    await state.update_data(designation=designation)
    await message.answer("📞 Please enter the employee's phone number (or type 'skip' to skip):")
    await state.set_state(EmployeeStates.waiting_for_phone)

@dp.message(EmployeeStates.waiting_for_phone)
async def process_phone(message: types.Message, state: FSMContext):
    """Process phone input."""
    phone = message.text.strip() if message.text.strip().lower() != 'skip' else None
    
    await state.update_data(phone=phone)
    await message.answer("📧 Please enter the employee's email (or type 'skip' to skip):")
    await state.set_state(EmployeeStates.waiting_for_email)

@dp.message(EmployeeStates.waiting_for_email)
async def process_email(message: types.Message, state: FSMContext):
    """Process email input."""
    email = message.text.strip() if message.text.strip().lower() != 'skip' else None
    
    await state.update_data(email=email)
    await message.answer("📅 Please enter the joining date (YYYY-MM-DD format, or type 'skip' to skip):")
    await state.set_state(EmployeeStates.waiting_for_joining_date)

@dp.message(EmployeeStates.waiting_for_joining_date)
async def process_joining_date(message: types.Message, state: FSMContext):
    """Process joining date input."""
    joining_date = None
    
    if message.text.strip().lower() != 'skip':
        try:
            # Validate date format
            datetime.strptime(message.text.strip(), '%Y-%m-%d')
            joining_date = message.text.strip()
        except ValueError:
            await message.answer(
                "❌ Invalid date format. Please use YYYY-MM-DD format (e.g., 2024-01-15) or type 'skip':"
            )
            return
    
    await state.update_data(joining_date=joining_date)
    await message.answer("💰 Please enter the employee's salary (numbers only, or type 'skip' to skip):")
    await state.set_state(EmployeeStates.waiting_for_salary)

@dp.message(EmployeeStates.waiting_for_salary)
async def process_salary(message: types.Message, state: FSMContext):
    """Process salary input."""
    salary = None
    
    if message.text.strip().lower() != 'skip':
        try:
            salary = float(message.text.strip())
            if salary < 0:
                await message.answer("❌ Salary cannot be negative. Please enter a valid amount or type 'skip':")
                return
        except ValueError:
            await message.answer("❌ Invalid salary format. Please enter numbers only or type 'skip':")
            return
    
    await state.update_data(salary=salary)
    await message.answer("🏢 Please enter the employee's department (or type 'skip' to skip):")
    await state.set_state(EmployeeStates.waiting_for_department)

@dp.message(EmployeeStates.waiting_for_department)
async def process_department(message: types.Message, state: FSMContext):
    """Process department input and create employee."""
    department = message.text.strip() if message.text.strip().lower() != 'skip' else None
    
    data = await state.get_data()
    
    # Create employee
    success = EmployeeManager.add_employee(
        company_id=data['company_id'],
        employee_id=data['employee_id'],
        first_name=data['first_name'],
        last_name=data.get('last_name'),
        designation=data.get('designation'),
        phone=data.get('phone'),
        email=data.get('email'),
        joining_date=data.get('joining_date'),
        salary=data.get('salary'),
        department=department
    )
    
    if success:
        # Create summary
        summary = f"✅ **Employee Added Successfully!**\n\n"
        summary += f"🆔 **ID:** {data['employee_id']}\n"
        summary += f"👤 **Name:** {data['first_name']}"
        if data.get('last_name'):
            summary += f" {data['last_name']}"
        summary += "\n"
        
        if data.get('designation'):
            summary += f"💼 **Designation:** {data['designation']}\n"
        if data.get('department'):
            summary += f"🏢 **Department:** {department}\n"
        if data.get('phone'):
            summary += f"📞 **Phone:** {data['phone']}\n"
        if data.get('email'):
            summary += f"📧 **Email:** {data['email']}\n"
        if data.get('joining_date'):
            summary += f"📅 **Joining Date:** {data['joining_date']}\n"
        if data.get('salary'):
            summary += f"💰 **Salary:** ${data['salary']:,.2f}\n"
        
        await message.answer(summary, parse_mode='Markdown')
        
        # Log the action
        LogManager.log_bot_usage(
            message.from_user.id, 'company_owner', 'add_employee',
            company_id=data['company_id'],
            action_details=f"Added employee: {data['employee_id']} - {data['first_name']}",
            success=True
        )
    else:
        await message.answer(
            "❌ **Failed to add employee**\n\n"
            "There was an error adding the employee. Please try again."
        )
        
        # Log the error
        LogManager.log_bot_usage(
            message.from_user.id, 'company_owner', 'add_employee',
            company_id=data['company_id'],
            action_details=f"Failed to add employee: {data['employee_id']}",
            success=False,
            error_message="Database error"
        )
    
    await state.clear()

# Main admin commands
@dp.message(Command("genkey"))
async def cmd_genkey(message: types.Message):
    """Generate API key for a company (main admin only)."""
    user_id = message.from_user.id
    
    if not UserManager.is_main_admin(user_id):
        await message.answer("❌ Access denied. This command is for main admins only.")
        return
    
    # Parse command arguments
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 2:
        await message.answer(
            "📝 **Generate API Key**\n\n"
            "Usage: `/genkey <company_id> <subscription_type>`\n\n"
            "Subscription types:\n"
            "• `1m` - 1 month\n"
            "• `6m` - 6 months\n"
            "• `lifetime` - Lifetime access\n\n"
            "Example: `/genkey 1 lifetime`",
            parse_mode='Markdown'
        )
        return
    
    try:
        company_id = int(args[0])
        subscription_type = args[1].lower()
        
        if subscription_type not in ['1m', '6m', 'lifetime']:
            await message.answer("❌ Invalid subscription type. Use: 1m, 6m, or lifetime")
            return
        
        # Update subscription
        success = CompanyManager.update_subscription(company_id, subscription_type, user_id)
        
        if success:
            # Get updated company info
            company_query = "SELECT * FROM companies WHERE id = %s"
            company_result = db.execute_query(company_query, (company_id,))
            
            if company_result:
                company = company_result[0]
                await message.answer(
                    f"✅ **API Key Generated Successfully!**\n\n"
                    f"🏢 **Company:** {company['company_name']}\n"
                    f"🆔 **Company ID:** {company_id}\n"
                    f"📅 **Subscription:** {subscription_type.upper()}\n"
                    f"🔑 **New API Key:** `{company['api_key']}`\n\n"
                    f"The company owner has been notified.",
                    parse_mode='Markdown'
                )
                
                # Notify company owner
                try:
                    owner_message = (
                        f"🎉 **Subscription Activated!**\n\n"
                        f"Your {subscription_type.upper()} subscription has been activated.\n"
                        f"You can now use all bot features.\n\n"
                        f"Thank you for choosing our Employee Management System!"
                    )
                    await bot.send_message(company['owner_telegram_id'], owner_message, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Failed to notify company owner: {e}")
            else:
                await message.answer("❌ Company not found.")
        else:
            await message.answer("❌ Failed to generate API key. Please check the company ID.")
    
    except ValueError:
        await message.answer("❌ Invalid company ID. Please provide a valid number.")
    except Exception as e:
        logger.error(f"Error in genkey command: {e}")
        await message.answer("❌ An error occurred while generating the API key.")

@dp.message(F.text == "📊 All Companies")
async def show_all_companies(message: types.Message):
    """Show all companies (main admin only)."""
    user_id = message.from_user.id
    
    if not UserManager.is_main_admin(user_id):
        await message.answer("❌ Access denied. This feature is for main admins only.")
        return
    
    companies = CompanyManager.get_all_companies()
    
    if not companies:
        await message.answer("📊 **No Companies Found**\n\nNo companies have registered yet.")
        return
    
    companies_text = "📊 **All Companies**\n\n"
    
    for i, company in enumerate(companies, 1):
        status = "✅" if company['is_subscription_active'] else "❌"
        companies_text += f"{i}. {status} **{company['company_name']}**\n"
        companies_text += f"   🆔 ID: {company['id']} | Code: {company['company_code']}\n"
        companies_text += f"   👤 Owner: @{company['owner_username'] or 'N/A'}\n"
        companies_text += f"   📅 Sub: {company['subscription_type'].upper()}\n"
        companies_text += f"   👥 Employees: {company['employee_count']}\n\n"
    
    companies_text += f"**Total Companies:** {len(companies)}"
    
    # Split message if too long
    if len(companies_text) > 4000:
        chunks = [companies_text[i:i+4000] for i in range(0, len(companies_text), 4000)]
        for chunk in chunks:
            await message.answer(chunk, parse_mode='Markdown')
    else:
        await message.answer(companies_text, parse_mode='Markdown')

# Support command
@dp.message(F.text == "🆘 Support")
async def start_support(message: types.Message, state: FSMContext):
    """Start support message process."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role == 'main_admin':
        await message.answer("❌ Main admins don't need to use support. You ARE the support! 😄")
        return
    
    if user_role == 'unknown':
        await message.answer("❌ Please register first using /start command.")
        return
    
    await message.answer(
        "🆘 **Support**\n\n"
        "Please describe your issue or question. Your message will be sent to the admin:",
        parse_mode='Markdown'
    )
    await state.set_state(SupportStates.waiting_for_message)

@dp.message(SupportStates.waiting_for_message)
async def process_support_message(message: types.Message, state: FSMContext):
    """Process support message."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    support_text = message.text.strip()
    
    if len(support_text) < 10:
        await message.answer("Please provide a more detailed message (at least 10 characters):")
        return
    
    # Save to database
    company_id = user_data.get('id') if user_role == 'company_owner' else user_data.get('company_id')
    
    success = LogManager.add_support_message(
        from_telegram_id=user_id,
        from_user_type=user_role,
        message_text=support_text,
        company_id=company_id
    )
    
    if success and MAIN_ADMIN_ID:
        # Send to main admin
        user = message.from_user
        admin_message = (
            f"🆘 **New Support Message**\n\n"
            f"👤 **From:** {user.first_name or 'N/A'} {user.last_name or ''} (@{user.username or 'N/A'})\n"
            f"🆔 **User ID:** {user_id}\n"
            f"👥 **Role:** {user_role.replace('_', ' ').title()}\n"
        )
        
        if user_role == 'company_owner' and user_data:
            admin_message += f"🏢 **Company:** {user_data['company_name']}\n"
        elif user_role == 'employee' and user_data:
            admin_message += f"🏢 **Company:** {user_data['company_name']}\n"
        
        admin_message += f"\n💬 **Message:**\n{support_text}"
        
        try:
            await bot.send_message(MAIN_ADMIN_ID, admin_message, parse_mode='Markdown')
            await message.answer(
                "✅ **Support message sent!**\n\n"
                "Your message has been forwarded to the admin. "
                "You will receive a response soon."
            )
        except Exception as e:
            logger.error(f"Failed to send support message to admin: {e}")
            await message.answer(
                "✅ **Message saved!**\n\n"
                "Your support message has been saved. "
                "The admin will respond as soon as possible."
            )
    else:
        await message.answer("❌ Failed to send support message. Please try again later.")
    
    await state.clear()

# Error handler
@dp.error()
async def error_handler(event, exception):
    """Handle errors."""
    logger.error(f"An error occurred: {exception}")
    
    if hasattr(event, 'message') and event.message:
        try:
            await event.message.answer(
                "❌ **An error occurred**\n\n"
                "Please try again later or contact support if the problem persists."
            )
        except:
            pass

# Main function
async def main():
    """Main function to start the bot."""
    logger.info("Starting Employee Management Bot...")
    
    # Initialize main admin if not exists
    if MAIN_ADMIN_ID:
        UserManager.add_main_admin(MAIN_ADMIN_ID)
        logger.info(f"Main admin initialized: {MAIN_ADMIN_ID}")
    
    # Start polling
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        await bot.session.close()
        db.disconnect()

if __name__ == "__main__":
    asyncio.run(main())


# Additional employee management handlers

@dp.message(F.text == "✏️ Edit Employee")
async def start_edit_employee(message: types.Message, state: FSMContext):
    """Start editing an employee."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role != 'company_owner':
        await message.answer("❌ Access denied. This feature is for company owners only.")
        return
    
    if not user_data['is_subscription_active']:
        await message.answer("⚠️ Your subscription has expired. Please renew to access this feature.")
        return
    
    await state.update_data(company_id=user_data['id'])
    await message.answer(
        "✏️ **Edit Employee**\n\n"
        "Please enter the employee ID you want to edit:",
        parse_mode='Markdown'
    )
    await state.set_state(EditEmployeeStates.waiting_for_employee_id)

@dp.message(EditEmployeeStates.waiting_for_employee_id)
async def process_edit_employee_id(message: types.Message, state: FSMContext):
    """Process employee ID for editing."""
    employee_id = message.text.strip()
    data = await state.get_data()
    company_id = data['company_id']
    
    # Check if employee exists
    employee = EmployeeManager.get_employee_by_id(company_id, employee_id)
    if not employee:
        await message.answer(
            f"❌ Employee with ID '{employee_id}' not found. Please check the ID and try again:"
        )
        return
    
    await state.update_data(employee_id=employee_id, employee_data=employee)
    
    # Create field selection keyboard
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 First Name", callback_data="edit_first_name")],
        [InlineKeyboardButton(text="👤 Last Name", callback_data="edit_last_name")],
        [InlineKeyboardButton(text="💼 Designation", callback_data="edit_designation")],
        [InlineKeyboardButton(text="📞 Phone", callback_data="edit_phone")],
        [InlineKeyboardButton(text="📧 Email", callback_data="edit_email")],
        [InlineKeyboardButton(text="📅 Joining Date", callback_data="edit_joining_date")],
        [InlineKeyboardButton(text="💰 Salary", callback_data="edit_salary")],
        [InlineKeyboardButton(text="🏢 Department", callback_data="edit_department")],
        [InlineKeyboardButton(text="❌ Cancel", callback_data="cancel_edit")]
    ])
    
    current_info = format_employee_info(employee)
    await message.answer(
        f"{current_info}\n\n**Select the field you want to edit:**",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    await state.set_state(EditEmployeeStates.waiting_for_field_selection)

@dp.callback_query(F.data.startswith("edit_"))
async def process_field_selection(callback: types.CallbackQuery, state: FSMContext):
    """Process field selection for editing."""
    field = callback.data.split("_", 1)[1]
    
    if field == "cancel":
        await callback.message.edit_text("✏️ Edit cancelled.")
        await state.clear()
        return
    
    await state.update_data(edit_field=field)
    
    field_names = {
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'designation': 'Designation',
        'phone': 'Phone',
        'email': 'Email',
        'joining_date': 'Joining Date (YYYY-MM-DD)',
        'salary': 'Salary',
        'department': 'Department'
    }
    
    await callback.message.edit_text(
        f"✏️ **Edit {field_names[field]}**\n\n"
        f"Please enter the new value for {field_names[field].lower()}:"
    )
    await state.set_state(EditEmployeeStates.waiting_for_new_value)

@dp.message(EditEmployeeStates.waiting_for_new_value)
async def process_new_value(message: types.Message, state: FSMContext):
    """Process new value for employee field."""
    new_value = message.text.strip()
    data = await state.get_data()
    field = data['edit_field']
    employee_id = data['employee_id']
    company_id = data['company_id']
    
    # Validate input based on field type
    if field == 'joining_date' and new_value.lower() != 'clear':
        try:
            datetime.strptime(new_value, '%Y-%m-%d')
        except ValueError:
            await message.answer(
                "❌ Invalid date format. Please use YYYY-MM-DD format (e.g., 2024-01-15) or type 'clear' to remove:"
            )
            return
    
    if field == 'salary' and new_value.lower() != 'clear':
        try:
            salary_value = float(new_value)
            if salary_value < 0:
                await message.answer("❌ Salary cannot be negative. Please enter a valid amount or type 'clear' to remove:")
                return
            new_value = salary_value
        except ValueError:
            await message.answer("❌ Invalid salary format. Please enter numbers only or type 'clear' to remove:")
            return
    
    # Handle 'clear' command
    if new_value.lower() == 'clear':
        new_value = None
    
    # Update employee
    update_data = {field: new_value}
    success = EmployeeManager.update_employee(company_id, employee_id, **update_data)
    
    if success:
        # Get updated employee info
        updated_employee = EmployeeManager.get_employee_by_id(company_id, employee_id)
        updated_info = format_employee_info(updated_employee)
        
        await message.answer(
            f"✅ **Employee Updated Successfully!**\n\n{updated_info}",
            parse_mode='Markdown'
        )
        
        # Log the action
        LogManager.log_bot_usage(
            message.from_user.id, 'company_owner', 'edit_employee',
            company_id=company_id,
            action_details=f"Updated {field} for employee {employee_id}",
            success=True
        )
    else:
        await message.answer("❌ Failed to update employee. Please try again.")
        
        # Log the error
        LogManager.log_bot_usage(
            message.from_user.id, 'company_owner', 'edit_employee',
            company_id=company_id,
            action_details=f"Failed to update {field} for employee {employee_id}",
            success=False,
            error_message="Database update failed"
        )
    
    await state.clear()

@dp.message(F.text == "👤 View Employee")
async def start_view_employee(message: types.Message, state: FSMContext):
    """Start viewing a specific employee."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role != 'company_owner':
        await message.answer("❌ Access denied. This feature is for company owners only.")
        return
    
    if not user_data['is_subscription_active']:
        await message.answer("⚠️ Your subscription has expired. Please renew to access this feature.")
        return
    
    await state.update_data(company_id=user_data['id'])
    await message.answer(
        "👤 **View Employee**\n\n"
        "Please enter the employee ID you want to view:",
        parse_mode='Markdown'
    )
    await state.set_state(ViewEmployeeStates.waiting_for_employee_id)

@dp.message(ViewEmployeeStates.waiting_for_employee_id)
async def process_view_employee_id(message: types.Message, state: FSMContext):
    """Process employee ID for viewing."""
    employee_id = message.text.strip()
    data = await state.get_data()
    company_id = data['company_id']
    
    # Get employee info
    employee = EmployeeManager.get_employee_by_id(company_id, employee_id)
    if not employee:
        await message.answer(
            f"❌ Employee with ID '{employee_id}' not found. Please check the ID and try again:"
        )
        return
    
    employee_info = format_employee_info(employee)
    await message.answer(employee_info, parse_mode='Markdown')
    
    # Log the action
    LogManager.log_bot_usage(
        message.from_user.id, 'company_owner', 'view_employee',
        company_id=company_id,
        action_details=f"Viewed employee {employee_id}",
        success=True
    )
    
    await state.clear()

@dp.message(F.text == "👤 My Profile")
async def show_my_profile(message: types.Message):
    """Show employee's own profile."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role != 'employee':
        await message.answer("❌ This feature is only available for employees.")
        return
    
    employee_info = format_employee_info(user_data)
    await message.answer(
        f"👤 **Your Profile**\n\n{employee_info}",
        parse_mode='Markdown'
    )
    
    # Log the action
    LogManager.log_bot_usage(
        user_id, 'employee', 'view_profile',
        company_id=user_data.get('company_id'),
        action_details="Viewed own profile",
        success=True
    )

@dp.message(F.text == "💳 Buy Subscription")
async def buy_subscription_menu(message: types.Message):
    """Show subscription purchase menu."""
    await cmd_buy(message)

@dp.message(F.text == "🔑 Generate API Key")
async def generate_api_key_menu(message: types.Message):
    """Show API key generation instructions for main admin."""
    user_id = message.from_user.id
    
    if not UserManager.is_main_admin(user_id):
        await message.answer("❌ Access denied. This feature is for main admins only.")
        return
    
    await message.answer(
        "🔑 **Generate API Key**\n\n"
        "To generate an API key for a company, use:\n"
        "`/genkey <company_id> <subscription_type>`\n\n"
        "**Subscription Types:**\n"
        "• `1m` - 1 month subscription\n"
        "• `6m` - 6 months subscription\n"
        "• `lifetime` - Lifetime subscription\n\n"
        "**Example:**\n"
        "`/genkey 1 lifetime`\n\n"
        "Use '📊 All Companies' to see company IDs.",
        parse_mode='Markdown'
    )

@dp.message(F.text == "📈 System Stats")
async def show_system_stats(message: types.Message):
    """Show system statistics for main admin."""
    user_id = message.from_user.id
    
    if not UserManager.is_main_admin(user_id):
        await message.answer("❌ Access denied. This feature is for main admins only.")
        return
    
    # Get statistics
    stats_queries = {
        'total_companies': "SELECT COUNT(*) as count FROM companies WHERE is_active = TRUE",
        'active_subscriptions': """
            SELECT COUNT(*) as count FROM companies 
            WHERE is_active = TRUE AND (
                subscription_type = 'lifetime' OR 
                subscription_end_date > NOW()
            )
        """,
        'total_employees': "SELECT COUNT(*) as count FROM employees WHERE status = 'active'",
        'recent_registrations': """
            SELECT COUNT(*) as count FROM companies 
            WHERE created_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """,
        'subscription_breakdown': """
            SELECT subscription_type, COUNT(*) as count 
            FROM companies 
            WHERE is_active = TRUE 
            GROUP BY subscription_type
        """
    }
    
    stats = {}
    for key, query in stats_queries.items():
        result = db.execute_query(query)
        if key == 'subscription_breakdown':
            stats[key] = {row['subscription_type']: row['count'] for row in result} if result else {}
        else:
            stats[key] = result[0]['count'] if result else 0
    
    stats_text = (
        "📈 **System Statistics**\n\n"
        f"🏢 **Total Companies:** {stats['total_companies']}\n"
        f"✅ **Active Subscriptions:** {stats['active_subscriptions']}\n"
        f"👥 **Total Employees:** {stats['total_employees']}\n"
        f"🆕 **New This Week:** {stats['recent_registrations']}\n\n"
        "**Subscription Breakdown:**\n"
    )
    
    breakdown = stats['subscription_breakdown']
    stats_text += f"• 1 Month: {breakdown.get('1m', 0)}\n"
    stats_text += f"• 6 Months: {breakdown.get('6m', 0)}\n"
    stats_text += f"• Lifetime: {breakdown.get('lifetime', 0)}\n"
    
    await message.answer(stats_text, parse_mode='Markdown')

@dp.message(F.text == "⚙️ Settings")
async def show_settings(message: types.Message):
    """Show system settings for main admin."""
    user_id = message.from_user.id
    
    if not UserManager.is_main_admin(user_id):
        await message.answer("❌ Access denied. This feature is for main admins only.")
        return
    
    pricing = SettingsManager.get_pricing()
    max_employees = SettingsManager.get_setting('max_employees_per_company')
    bot_version = SettingsManager.get_setting('bot_version')
    
    settings_text = (
        "⚙️ **System Settings**\n\n"
        "**Pricing:**\n"
        f"• 1 Month: ${pricing['1m']}\n"
        f"• 6 Months: ${pricing['6m']}\n"
        f"• Lifetime: ${pricing['lifetime']}\n\n"
        f"**Max Employees per Company:** {max_employees}\n"
        f"**Bot Version:** {bot_version}\n\n"
        "To modify settings, update the database directly."
    )
    
    await message.answer(settings_text, parse_mode='Markdown')

# Handle unknown messages
@dp.message()
async def handle_unknown_message(message: types.Message):
    """Handle unknown messages."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role == 'unknown':
        await message.answer(
            "👋 Welcome! Please use /start to begin registration.",
            reply_markup=None
        )
    else:
        await message.answer(
            "❓ I didn't understand that command. Please use the menu buttons or type /start for help.",
            reply_markup=create_main_menu_keyboard(user_role)
        )


# Import payment handling
from payment_handler import SubscriptionManager, format_payment_info, get_pricing_text

# Enhanced buy command with payment integration
@dp.callback_query(F.data.startswith("sub_") & ~F.data.endswith("cancel"))
async def process_payment_subscription(callback: types.CallbackQuery, state: FSMContext):
    """Process subscription payment."""
    subscription_type = callback.data.split("_")[1]
    user = callback.from_user
    
    # Check if user is already a company owner
    user_role, user_data = UserManager.get_user_role(user.id)
    
    if user_role == 'company_owner':
        # Existing company owner wants to renew/upgrade
        company_id = user_data['id']
        
        # Create payment
        payment_data = SubscriptionManager.create_subscription_payment(
            company_id=company_id,
            subscription_type=subscription_type
        )
        
        if payment_data:
            payment_info = format_payment_info(payment_data)
            
            await callback.message.edit_text(
                f"💳 **Subscription Renewal**\n\n{payment_info}",
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
            # Notify admin about payment initiation
            if MAIN_ADMIN_ID:
                try:
                    admin_message = (
                        f"💳 **Payment Initiated**\n\n"
                        f"🏢 **Company:** {user_data['company_name']}\n"
                        f"👤 **Owner:** {user.first_name or 'N/A'} (@{user.username or 'N/A'})\n"
                        f"📅 **Subscription:** {subscription_type.upper()}\n"
                        f"💰 **Amount:** ${payment_data['amount']:.2f}\n"
                        f"🆔 **Transaction:** `{payment_data['transaction_id']}`\n\n"
                        f"Waiting for payment completion..."
                    )
                    await bot.send_message(MAIN_ADMIN_ID, admin_message, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Failed to notify admin about payment: {e}")
        else:
            await callback.message.edit_text(
                "❌ **Payment Error**\n\n"
                "Failed to create payment. Please try again later or contact support."
            )
    
    else:
        # New user registration flow (existing code)
        data = await state.get_data()
        company_name = data.get('company_name')
        
        if not company_name:
            await callback.message.edit_text(
                "❌ **Session Expired**\n\n"
                "Please start registration again with /start command."
            )
            await state.clear()
            return
        
        # Create company
        company = CompanyManager.create_company(
            company_name=company_name,
            owner_telegram_id=user.id,
            owner_username=user.username,
            owner_first_name=user.first_name,
            owner_last_name=user.last_name,
            subscription_type=subscription_type
        )
        
        if company:
            # Create payment for new company
            payment_data = SubscriptionManager.create_subscription_payment(
                company_id=company['id'],
                subscription_type=subscription_type
            )
            
            if payment_data:
                payment_info = format_payment_info(payment_data)
                
                await callback.message.edit_text(
                    f"🏢 **Company Registered!**\n\n"
                    f"**Company:** {company_name}\n"
                    f"**Code:** {company['company_code']}\n\n"
                    f"{payment_info}",
                    parse_mode='Markdown',
                    disable_web_page_preview=True
                )
                
                # Notify admin about new registration and payment
                if MAIN_ADMIN_ID:
                    try:
                        admin_message = (
                            f"🆕 **New Registration + Payment**\n\n"
                            f"🏢 **Company:** {company_name}\n"
                            f"👤 **Owner:** {user.first_name or 'N/A'} (@{user.username or 'N/A'})\n"
                            f"🆔 **Company Code:** {company['company_code']}\n"
                            f"📅 **Subscription:** {subscription_type.upper()}\n"
                            f"💰 **Amount:** ${payment_data['amount']:.2f}\n"
                            f"🆔 **Transaction:** `{payment_data['transaction_id']}`\n\n"
                            f"Waiting for payment completion to activate subscription."
                        )
                        await bot.send_message(MAIN_ADMIN_ID, admin_message, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Failed to notify admin: {e}")
            else:
                await callback.message.edit_text(
                    f"🏢 **Company Registered!**\n\n"
                    f"**Company:** {company_name}\n"
                    f"**Code:** {company['company_code']}\n\n"
                    f"❌ **Payment Error:** Failed to create payment link.\n"
                    f"Please contact support for manual activation."
                )
        else:
            await callback.message.edit_text(
                "❌ **Registration Failed**\n\n"
                "There was an error creating your company. Please try again later."
            )
        
        await state.clear()

# Enhanced buy command
@dp.message(Command("buy"))
async def cmd_buy_enhanced(message: types.Message):
    """Enhanced buy command with detailed pricing."""
    user_id = message.from_user.id
    user_role, user_data = UserManager.get_user_role(user_id)
    
    if user_role == 'main_admin':
        await message.answer("❌ Main admins don't need subscriptions! 😄")
        return
    
    if user_role == 'employee':
        await message.answer("❌ Employees cannot purchase subscriptions. Please contact your company admin.")
        return
    
    pricing_text = get_pricing_text()
    
    if user_role == 'company_owner':
        current_sub = user_data['subscription_type'].upper()
        if user_data['is_subscription_active']:
            if user_data['subscription_type'] == 'lifetime':
                pricing_text += f"\n\n✅ **Current Plan:** {current_sub} (Active Forever)"
            else:
                end_date = user_data['subscription_end_date'].strftime('%Y-%m-%d %H:%M')
                pricing_text += f"\n\n✅ **Current Plan:** {current_sub} (Expires: {end_date})"
        else:
            pricing_text += f"\n\n⚠️ **Current Plan:** {current_sub} (Expired)"
        
        pricing_text += "\n\nSelect a plan to renew or upgrade:"
    else:
        pricing_text += "\n\nSelect your preferred subscription to get started:"
    
    await message.answer(
        pricing_text,
        reply_markup=create_subscription_keyboard(),
        parse_mode='Markdown'
    )

# Webhook handler for payment notifications (for future web deployment)
async def handle_payment_webhook(request_data: Dict) -> bool:
    """Handle payment webhook notifications."""
    try:
        success = SubscriptionManager.handle_payment_webhook(request_data)
        
        if success and request_data.get('status') == 'completed':
            # Get payment info
            transaction_id = request_data.get('transaction_id')
            
            # Get company info from payment
            payment_query = """
            SELECT p.*, c.owner_telegram_id, c.company_name 
            FROM payments p 
            JOIN companies c ON p.company_id = c.id 
            WHERE p.transaction_id = %s
            """
            
            payment_result = db.execute_query(payment_query, (transaction_id,))
            
            if payment_result:
                payment = payment_result[0]
                
                # Notify company owner
                try:
                    owner_message = (
                        f"🎉 **Payment Successful!**\n\n"
                        f"Your {payment['subscription_type'].upper()} subscription has been activated!\n"
                        f"💰 **Amount:** ${payment['amount']:.2f}\n"
                        f"🆔 **Transaction:** `{transaction_id}`\n\n"
                        f"You can now use all bot features. Welcome aboard! 🚀"
                    )
                    await bot.send_message(payment['owner_telegram_id'], owner_message, parse_mode='Markdown')
                except Exception as e:
                    logger.error(f"Failed to notify company owner about successful payment: {e}")
                
                # Notify admin
                if MAIN_ADMIN_ID:
                    try:
                        admin_message = (
                            f"✅ **Payment Completed!**\n\n"
                            f"🏢 **Company:** {payment['company_name']}\n"
                            f"📅 **Subscription:** {payment['subscription_type'].upper()}\n"
                            f"💰 **Amount:** ${payment['amount']:.2f}\n"
                            f"🆔 **Transaction:** `{transaction_id}`\n\n"
                            f"Subscription has been automatically activated."
                        )
                        await bot.send_message(MAIN_ADMIN_ID, admin_message, parse_mode='Markdown')
                    except Exception as e:
                        logger.error(f"Failed to notify admin about completed payment: {e}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error in payment webhook handler: {e}")
        return False

# Command to simulate payment completion (for testing)
@dp.message(Command("simulate_payment"))
async def cmd_simulate_payment(message: types.Message):
    """Simulate payment completion for testing (main admin only)."""
    user_id = message.from_user.id
    
    if not UserManager.is_main_admin(user_id):
        await message.answer("❌ Access denied. This command is for testing by main admins only.")
        return
    
    args = message.text.split()[1:] if len(message.text.split()) > 1 else []
    
    if len(args) < 1:
        await message.answer(
            "📝 **Simulate Payment**\n\n"
            "Usage: `/simulate_payment <transaction_id>`\n\n"
            "This will mark the payment as completed for testing purposes.",
            parse_mode='Markdown'
        )
        return
    
    transaction_id = args[0]
    
    # Simulate webhook data
    webhook_data = {
        'transaction_id': transaction_id,
        'status': 'completed',
        'gateway_transaction_id': f"sim_{transaction_id[:8]}"
    }
    
    success = await handle_payment_webhook(webhook_data)
    
    if success:
        await message.answer(
            f"✅ **Payment Simulated Successfully!**\n\n"
            f"Transaction `{transaction_id}` has been marked as completed.",
            parse_mode='Markdown'
        )
    else:
        await message.answer(
            f"❌ **Simulation Failed**\n\n"
            f"Could not simulate payment for transaction `{transaction_id}`. "
            f"Please check if the transaction exists.",
            parse_mode='Markdown'
        )

