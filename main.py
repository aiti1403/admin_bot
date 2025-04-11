import logging
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import PicklePersistence
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ID администраторов (замените на реальные ID)
ADMIN_IDS = [7470235989, 1008609216, 801300839]

# Состояния для ConversationHandler
(
    MAIN_MENU,
    ADMIN_MENU,
    EMPLOYEE_MENU,
    ENTER_EMPLOYEE_NAME,
    ENTER_EMPLOYEE_SALARY,
    ENTER_TASK_NAME,
    ENTER_TASK_POINTS,
    ADD_TASK,
    TAKE_TASK,
    COMPLETE_TASK,
    SELECT_PERIOD,
    ANALYTICS,
    SELECT_EMPLOYEE,
    ASSIGN_TASK,
    SELECT_EMPLOYEE_EDIT,
    EDIT_EMPLOYEE,
    EDIT_EMPLOYEE_NAME,
    EDIT_EMPLOYEE_SALARY,
    SELECT_TASK_EDIT,
    EDIT_TASK,
    EDIT_TASK_NAME,
    EDIT_TASK_POINTS,
    EDIT_TASK_CATEGORY,
    SELECT_ACTIVE_TASK_CANCEL,
    VIEW_TASK_HISTORY

) = range(25)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    
    # Таблица сотрудников
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        salary REAL NOT NULL,
        telegram_id INTEGER UNIQUE,
        active BOOLEAN DEFAULT 1
    )
    ''')
    
    # Таблица задач
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        points INTEGER NOT NULL,
        category TEXT NOT NULL
    )
    ''')
    
    # Таблица активных задач
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS active_tasks (
        id INTEGER PRIMARY KEY,
        employee_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees (id),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    ''')
    
    # Таблица выполненных задач
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS completed_tasks (
        id INTEGER PRIMARY KEY,
        employee_id INTEGER NOT NULL,
        task_id INTEGER NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        points_earned INTEGER NOT NULL,
        duration_seconds REAL NOT NULL,
        FOREIGN KEY (employee_id) REFERENCES employees (id),
        FOREIGN KEY (task_id) REFERENCES tasks (id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Заполнение начальными данными
def fill_initial_data():
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже задачи в базе
    cursor.execute("SELECT COUNT(*) FROM tasks")
    if cursor.fetchone()[0] == 0:
        # Добавляем примеры задач
        tasks = [
            ("Разбор новой поставки", 10, "Распаковка"),
            ("Выкладка товара на витрину", 5, "Распаковка"),
            ("Инвентаризация склада", 15, "Логистика"),
            ("Заказ новой партии товара", 10, "Закупка"),
            ("Обработка возврата", 5, "Логистика"),
            ("Консультация клиента", 3, "Продажи"),
            ("Оформление продажи", 5, "Продажи"),
            ("Публикация в соцсетях", 8, "Маркетинг"),
            ("Создание рекламного баннера", 12, "Маркетинг"),
            ("Уборка торгового зала", 7, "Другое")
        ]
        
        cursor.executemany(
            "INSERT INTO tasks (name, points, category) VALUES (?, ?, ?)",
            tasks
        )
        
        conn.commit()
    
    conn.close()

# Проверка, является ли пользователь администратором
def is_admin(user_id):
    return user_id in ADMIN_IDS

# Проверка, зарегистрирован ли пользователь как сотрудник
def is_employee_registered(user_id):
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM employees WHERE telegram_id = ? AND active = 1", (user_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

# Получение ID сотрудника по Telegram ID
def get_employee_id(user_id):
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM employees WHERE telegram_id = ? AND active = 1", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

# Обработчик команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    await update.message.reply_text(
        f"Привет, {user_name}! Я бот для анализа эффективности сотрудников магазина кроссовок."
    )
    
    keyboard = []
    
    if is_admin(user_id):
        keyboard.append(["👨‍💼 Меню администратора"])
    
    if is_employee_registered(user_id):
        keyboard.append(["👷 Меню сотрудника"])
    else:
        await update.message.reply_text(
            "Если вы сотрудник, зарегистрируйтесь с помощью команды /register ID, "
            "где ID - ваш идентификатор сотрудника."
        )
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выберите режим работы:", reply_markup=reply_markup)
    
    return MAIN_MENU

# Обработчик главного меню
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    if text == "👨‍💼 Меню администратора" and is_admin(user_id):
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
        return ADMIN_MENU
    
    elif text == "👷 Меню сотрудника" and is_employee_registered(user_id):
        keyboard = [
            ["📝 Взять задачу", "✅ Завершить задачу"],
            ["📈 Моя статистика", "🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите действие:", reply_markup=reply_markup)
        return EMPLOYEE_MENU
    
    else:
        await update.message.reply_text("Неверная команда. Пожалуйста, используйте кнопки меню.")
        return MAIN_MENU

# Обработчик меню администратора
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "👤 Добавить сотрудника":
        await update.message.reply_text("Введите имя нового сотрудника:")
        return ENTER_EMPLOYEE_NAME
    
    elif text == "📋 Добавить задачу":
        await update.message.reply_text("Введите название новой задачи:")
        return ENTER_TASK_NAME
    
    elif text == "📊 Аналитика":
        keyboard = [
            ["За сегодня", "За неделю"],
            ["За месяц", "За всё время"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите период для анализа:", reply_markup=reply_markup)
        return SELECT_PERIOD
    
    elif text == "📝 Назначить задачу":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM employees WHERE active = 1 ORDER BY name")
        employees = cursor.fetchall()
        conn.close()
        
        if not employees:
            await update.message.reply_text("Нет активных сотрудников.")
            return ADMIN_MENU
        
        keyboard = []
        for emp_id, emp_name in employees:
            keyboard.append([f"{emp_name} - ID: {emp_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите сотрудника для назначения задачи:", reply_markup=reply_markup)
        return SELECT_EMPLOYEE
    
    elif text == "✏️ Изменить сотрудника":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, salary FROM employees WHERE active = 1 ORDER BY name")
        employees = cursor.fetchall()
        conn.close()
        
        if not employees:
            await update.message.reply_text("Нет активных сотрудников.")
            return ADMIN_MENU
        
        keyboard = []
        for emp_id, emp_name, emp_salary in employees:
            keyboard.append([f"{emp_name} (ЗП: {emp_salary} руб.) - ID: {emp_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите сотрудника для редактирования:", reply_markup=reply_markup)
        return SELECT_EMPLOYEE_EDIT
    
    elif text == "✏️ Изменить задачу":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, points, category FROM tasks ORDER BY category, name")
        tasks = cursor.fetchall()
        conn.close()
        
        if not tasks:
            await update.message.reply_text("Нет доступных задач.")
            return ADMIN_MENU
        
        keyboard = []
        current_category = None
        
        for task in tasks:
            task_id, task_name, points, category = task
            
            if category != current_category:
                if keyboard:
                    keyboard.append([])
                current_category = category
                keyboard.append([f"--- {category} ---"])
            
            keyboard.append([f"{task_name} ({points} очков) - ID: {task_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите задачу для редактирования:", reply_markup=reply_markup)
        return SELECT_TASK_EDIT
    
    elif text == "❌ Отменить активную задачу":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем все активные задачи
        cursor.execute("""
            SELECT a.id, e.name as employee_name, t.name as task_name, a.start_time
            FROM active_tasks a
            JOIN employees e ON a.employee_id = e.id
            JOIN tasks t ON a.task_id = t.id
            ORDER BY a.start_time
        """)
        
        active_tasks = cursor.fetchall()
        conn.close()
        
        if not active_tasks:
            await update.message.reply_text("Нет активных задач.")
            return ADMIN_MENU
        
        keyboard = []
        for task_id, employee_name, task_name, start_time in active_tasks:
            start_datetime = datetime.fromisoformat(start_time)
            duration = (datetime.now() - start_datetime).total_seconds() / 60.0
            
            keyboard.append([f"{employee_name}: {task_name} ({round(duration, 2)} мин.) - ID: {task_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите задачу для отмены:", reply_markup=reply_markup)
        return SELECT_ACTIVE_TASK_CANCEL
    
    elif text == "📋 История задач":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM employees WHERE active = 1 ORDER BY name")
        employees = cursor.fetchall()
        conn.close()
        
        if not employees:
            await update.message.reply_text("Нет активных сотрудников.")
            return ADMIN_MENU
        
        keyboard = []
        for emp_id, emp_name in employees:
            keyboard.append([f"{emp_name} - ID: {emp_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите сотрудника для просмотра истории задач:", reply_markup=reply_markup)
        return VIEW_TASK_HISTORY
    
    elif text == "🔙 Назад":
        keyboard = []
        user_id = update.effective_user.id
        
        if is_admin(user_id):
            keyboard.append(["👨‍💼 Меню администратора"])
        
        if is_employee_registered(user_id):
            keyboard.append(["👷 Меню сотрудника"])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Главное меню", reply_markup=reply_markup)
        return MAIN_MENU
    
    else:
        await update.message.reply_text("Неверная команда. Пожалуйста, используйте кнопки меню.")
        return ADMIN_MENU

# Обработчик меню сотрудника
async def employee_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    employee_id = get_employee_id(user_id)
    
    if text == "📝 Взять задачу":
        # Проверяем, сколько активных задач у сотрудника
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM active_tasks WHERE employee_id = ?", (employee_id,))
        active_count = cursor.fetchone()[0]
        
        if active_count >= 3:
            conn.close()
            await update.message.reply_text(
                "У вас уже есть 3 активные задачи. Завершите хотя бы одну, прежде чем брать новую."
            )
            return EMPLOYEE_MENU
        
        # Получаем список доступных задач
        cursor.execute("""
            SELECT t.id, t.name, t.points, t.category
            FROM tasks t
            ORDER BY t.category, t.name
        """)
        tasks = cursor.fetchall()
        conn.close()
        
        if not tasks:
            await update.message.reply_text("Нет доступных задач.")
            return EMPLOYEE_MENU
        
        keyboard = []
        current_category = None
        
        for task in tasks:
            task_id, task_name, points, category = task
            
            if category != current_category:
                if keyboard:
                    keyboard.append([])
                current_category = category
                keyboard.append([f"--- {category} ---"])
            
            keyboard.append([f"{task_name} ({points} очков) - ID: {task_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите задачу:", reply_markup=reply_markup)
        return TAKE_TASK
    
    elif text == "✅ Завершить задачу":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем активные задачи сотрудника
        cursor.execute("""
            SELECT a.id, t.name, t.points, a.start_time
            FROM active_tasks a
            JOIN tasks t ON a.task_id = t.id
            WHERE a.employee_id = ?
        """, (employee_id,))
        active_tasks = cursor.fetchall()
        conn.close()
        
        if not active_tasks:
            await update.message.reply_text("У вас нет активных задач.")
            return EMPLOYEE_MENU
        
        keyboard = []
        for task in active_tasks:
            task_id, task_name, points, start_time = task
            start_datetime = datetime.fromisoformat(start_time)
            duration = (datetime.now() - start_datetime).total_seconds() / 60.0  # в минутах
            
            keyboard.append([f"{task_name} ({points} очков, {round(duration, 2)} мин.) - ID: {task_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите задачу для завершения:", reply_markup=reply_markup)
        return COMPLETE_TASK
    
    elif text == "📈 Моя статистика":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем статистику сотрудника
        cursor.execute("""
            SELECT 
                COUNT(*) as total_tasks,
                SUM(points_earned) as total_points,
                AVG(duration_seconds) / 60.0 as avg_duration,
                SUM(duration_seconds) / 3600.0 as total_duration
            FROM completed_tasks
            WHERE employee_id = ?
        """, (employee_id,))
        stats = cursor.fetchone()
        
        # Получаем статистику по категориям
        cursor.execute("""
            SELECT 
                t.category,
                COUNT(*) as category_count,
                SUM(c.points_earned) as category_points
            FROM completed_tasks c
            JOIN tasks t ON c.task_id = t.id
            WHERE c.employee_id = ?
            GROUP BY t.category
            ORDER BY category_points DESC
        """, (employee_id,))
        category_stats = cursor.fetchall()
        
        # Получаем активные задачи
        cursor.execute("""
            SELECT 
                t.name,
                t.points,
                a.start_time
            FROM active_tasks a
            JOIN tasks t ON a.task_id = t.id
            WHERE a.employee_id = ?
        """, (employee_id,))
        active_tasks = cursor.fetchall()
        
        # Получаем имя сотрудника
        cursor.execute("SELECT name FROM employees WHERE id = ?", (employee_id,))
        employee_name = cursor.fetchone()[0]
        
        conn.close()
        
        total_tasks, total_points, avg_duration, total_duration = stats
        
        response = f"📊 *Статистика сотрудника {employee_name}*\n\n"
        response += f"📝 Всего выполнено задач: {total_tasks or 0}\n"
        response += f"🏆 Всего заработано очков: {total_points or 0}\n"
        response += f"⏱ Среднее время на задачу: {round(avg_duration or 0, 2)} мин.\n"
        response += f"⌛ Общее время работы: {round(total_duration or 0, 2)} ч.\n\n"
        
        if category_stats:
            response += "*Статистика по категориям:*\n"
            for category, count, points in category_stats:
                response += f"• {category}: {count} задач, {points} очков\n"
            response += "\n"
        
        if active_tasks:
            response += "*Активные задачи:*\n"
            for name, points, start_time in active_tasks:
                start_datetime = datetime.fromisoformat(start_time)
                duration = (datetime.now() - start_datetime).total_seconds() / 60.0
                response += f"• {name} ({points} очков) - в работе {round(duration, 2)} мин.\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        return EMPLOYEE_MENU
    
    elif text == "🔙 Назад":
        keyboard = []
        
        if is_admin(user_id):
            keyboard.append(["👨‍💼 Меню администратора"])
        
        if is_employee_registered(user_id):
            keyboard.append(["👷 Меню сотрудника"])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Главное меню", reply_markup=reply_markup)
        return MAIN_MENU
    
    else:
        await update.message.reply_text("Неверная команда. Пожалуйста, используйте кнопки меню.")
        return EMPLOYEE_MENU

# Обработчик ввода имени сотрудника
async def enter_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['employee_name'] = name
    
    await update.message.reply_text(f"Введите зарплату для сотрудника {name}:")
    return ENTER_EMPLOYEE_SALARY

# Обработчик ввода зарплаты сотрудника
async def enter_employee_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        salary = float(update.message.text)
        name = context.user_data['employee_name']
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT INTO employees (name, salary, active) VALUES (?, ?, 1)",
            (name, salary)
        )
        
        employee_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ Сотрудник {name} успешно добавлен с зарплатой {salary} руб.\n"
            f"ID сотрудника: {employee_id}\n\n"
            f"Сотрудник может зарегистрироваться в боте с помощью команды:\n"
            f"/register {employee_id}"
        )
        
        # Возвращаемся в меню администратора
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для зарплаты.")
        return ENTER_EMPLOYEE_SALARY

# Обработчик ввода названия задачи
async def enter_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text
    context.user_data['task_name'] = name
    
    await update.message.reply_text(f"Введите количество очков за задачу '{name}':")
    return ENTER_TASK_POINTS

# Обработчик ввода очков за задачу
async def enter_task_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        points = int(update.message.text)
        name = context.user_data['task_name']
        
        if points <= 0:
            await update.message.reply_text("Количество очков должно быть положительным числом.")
            return ENTER_TASK_POINTS
        
        context.user_data['task_points'] = points
        
        # Предлагаем выбрать категорию
        keyboard = [
            ["Распаковка", "Логистика"],
            ["Продажи", "Маркетинг"],
            ["Закупка", "Другое"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(
            f"Выберите категорию для задачи '{name}':",
            reply_markup=reply_markup
        )
        return ADD_TASK
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное целое число для очков.")
        return ENTER_TASK_POINTS

# Обработчик добавления задачи
async def add_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    category = update.message.text
    name = context.user_data['task_name']
    points = context.user_data['task_points']
    
    # Проверяем, что категория выбрана из предложенных
    valid_categories = ["Распаковка", "Логистика", "Продажи", "Маркетинг", "Закупка", "Другое"]
    if category not in valid_categories:
        await update.message.reply_text("Пожалуйста, выберите категорию из предложенных вариантов.")
        return ADD_TASK
    
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    
    cursor.execute(
        "INSERT INTO tasks (name, points, category) VALUES (?, ?, ?)",
        (name, points, category)
    )
    
    conn.commit()
    conn.close()
    
    await update.message.reply_text(
        f"✅ Задача '{name}' успешно добавлена.\n"
        f"Категория: {category}\n"
        f"Очки: {points}"
    )
    
    # Возвращаемся в меню администратора
    keyboard = [
        ["👤 Добавить сотрудника", "📋 Добавить задачу"],
        ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
        ["📝 Назначить задачу", "📊 Аналитика"],
        ["📋 История задач", "❌ Отменить активную задачу"],
        ["🔙 Назад"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
    return ADMIN_MENU

# Обработчик взятия задачи
async def take_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    employee_id = get_employee_id(user_id)
    
    if text == "🔙 Назад":
        keyboard = [
            ["📝 Взять задачу", "✅ Завершить задачу"],
            ["📈 Моя статистика", "🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню сотрудника", reply_markup=reply_markup)
        return EMPLOYEE_MENU
    
    # Проверяем, что это не заголовок категории
    if text.startswith("--- ") and text.endswith(" ---"):
        await update.message.reply_text("Это заголовок категории. Пожалуйста, выберите задачу.")
        return TAKE_TASK
    
    try:
        task_id = int(text.split("ID: ")[1])
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем информацию о задаче
        cursor.execute("SELECT name, points FROM tasks WHERE id = ?", (task_id,))
        task_info = cursor.fetchone()
        
        if not task_info:
            conn.close()
            await update.message.reply_text("Задача не найдена.")
            return TAKE_TASK
        
        task_name, points = task_info
        
        # Проверяем, не взята ли уже эта задача этим сотрудником
        cursor.execute(
            "SELECT id FROM active_tasks WHERE employee_id = ? AND task_id = ?",
            (employee_id, task_id)
        )
        if cursor.fetchone():
            conn.close()
            await update.message.reply_text("Вы уже взяли эту задачу.")
            return TAKE_TASK
        
        # Добавляем задачу в активные
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO active_tasks (employee_id, task_id, start_time) VALUES (?, ?, ?)",
            (employee_id, task_id, now)
        )
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ Вы взяли задачу '{task_name}' ({points} очков).\n"
            f"Время начала: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
        )
        
        # Возвращаемся в меню сотрудника
        keyboard = [
            ["📝 Взять задачу", "✅ Завершить задачу"],
            ["📈 Моя статистика", "🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню сотрудника", reply_markup=reply_markup)
        return EMPLOYEE_MENU
        
    except (IndexError, ValueError):
        await update.message.reply_text("Не удалось определить ID задачи. Пожалуйста, выберите задачу из списка.")
        return TAKE_TASK

# Обработчик завершения задачи
async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user_id = update.effective_user.id
    employee_id = get_employee_id(user_id)
    
    if text == "🔙 Назад":
        keyboard = [
            ["📝 Взять задачу", "✅ Завершить задачу"],
            ["📈 Моя статистика", "🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню сотрудника", reply_markup=reply_markup)
        return EMPLOYEE_MENU
    
    try:
        active_task_id = int(text.split("ID: ")[1])
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем информацию об активной задаче
        cursor.execute("""
            SELECT a.task_id, t.name, t.points, a.start_time
            FROM active_tasks a
            JOIN tasks t ON a.task_id = t.id
            WHERE a.id = ? AND a.employee_id = ?
        """, (active_task_id, employee_id))
        
        task_info = cursor.fetchone()
        
        if not task_info:
            conn.close()
            await update.message.reply_text("Задача не найдена или не принадлежит вам.")
            return COMPLETE_TASK
        
        task_id, task_name, points, start_time = task_info
        
        # Рассчитываем длительность выполнения
        start_datetime = datetime.fromisoformat(start_time)
        end_datetime = datetime.now()
        duration_seconds = (end_datetime - start_datetime).total_seconds()
        
        # Добавляем в выполненные задачи
        cursor.execute("""
            INSERT INTO completed_tasks 
            (employee_id, task_id, start_time, end_time, points_earned, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            employee_id, 
            task_id, 
            start_time, 
            end_datetime.isoformat(), 
            points, 
            duration_seconds
        ))
        
        # Удаляем из активных задач
        cursor.execute("DELETE FROM active_tasks WHERE id = ?", (active_task_id,))
        
        conn.commit()
        conn.close()
        
        duration_minutes = duration_seconds / 60.0
        
        await update.message.reply_text(
            f"✅ Задача '{task_name}' успешно завершена!\n"
            f"Заработано очков: {points}\n"
            f"Время выполнения: {round(duration_minutes, 2)} мин."
        )
        
        # Возвращаемся в меню сотрудника
        keyboard = [
            ["📝 Взять задачу", "✅ Завершить задачу"],
            ["📈 Моя статистика", "🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню сотрудника", reply_markup=reply_markup)
        return EMPLOYEE_MENU
        
    except (IndexError, ValueError):
        await update.message.reply_text("Не удалось определить ID задачи. Пожалуйста, выберите задачу из списка.")
        return COMPLETE_TASK

# Обработчик выбора периода для аналитики
async def select_period(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🔙 Назад":
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
    
    # Определяем период для аналитики
    now = datetime.now()
    
    if text == "За сегодня":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_name = "сегодня"
    elif text == "За неделю":
        start_date = now - timedelta(days=7)
        period_name = "последнюю неделю"
    elif text == "За месяц":
        start_date = now - timedelta(days=30)
        period_name = "последний месяц"
    elif text == "За всё время":
        start_date = datetime(2000, 1, 1)  # Достаточно давно
        period_name = "всё время"
    else:
        await update.message.reply_text("Пожалуйста, выберите период из предложенных вариантов.")
        return SELECT_PERIOD
    
    # Сохраняем период для использования в аналитике
    context.user_data['analytics_start_date'] = start_date.isoformat()
    context.user_data['analytics_period_name'] = period_name
    
    # Переходим к выбору типа аналитики
    keyboard = [
        ["👥 По сотрудникам", "🎯 По задачам"],
        ["📈 Общая статистика", "🔙 Назад"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"Выберите тип аналитики за {period_name}:", reply_markup=reply_markup)
    return ANALYTICS

# Обработчик аналитики
async def analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    start_date = datetime.fromisoformat(context.user_data['analytics_start_date'])
    period_name = context.user_data['analytics_period_name']
    
    if text == "👥 По сотрудникам":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем статистику по сотрудникам за выбранный период
        # Проверяем, нужно ли показывать всех сотрудников или только активных
        show_all = context.user_data.get('show_all_employees', False)
        
        query = """
            SELECT 
                e.id,
                e.name,
                COUNT(c.id) as completed_count,
                SUM(c.points_earned) as total_points,
                AVG(c.duration_seconds) / 60.0 as avg_duration,
                SUM(c.duration_seconds) / 3600.0 as total_hours,
                e.salary,
                e.active
            FROM employees e
            LEFT JOIN completed_tasks c ON e.id = c.employee_id AND c.end_time >= ?
        """
        
        if not show_all:
            query += " WHERE e.active = 1"
        
        query += " GROUP BY e.id ORDER BY total_points DESC"
        
        cursor.execute(query, (start_date.isoformat(),))
        employees_stats = cursor.fetchall()
        conn.close()
        
        if not employees_stats:
            await update.message.reply_text("Нет данных о сотрудниках.")
            return ANALYTICS
        
        # Добавляем кнопку для переключения режима отображения
        keyboard = [
            ["👥 Показать всех" if not show_all else "👥 Только активные"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        response = f"📊 *Аналитика по сотрудникам за {period_name}*\n"
        if show_all:
            response += "_(показаны все сотрудники, включая неактивных)_\n\n"
        else:
            response += "_(показаны только активные сотрудники)_\n\n"
        
        for emp in employees_stats:
            emp_id, name, completed, points, avg_duration, total_hours, salary, active = emp
            
            # Преобразуем None в 0 для безопасных вычислений
            completed = completed or 0
            points = points or 0
            avg_duration = avg_duration or 0
            total_hours = total_hours or 0
            
            # Расчет эффективности (очков в час)
            # Если времени работы мало, используем среднее время на задачу для расчета
            if completed > 0 and avg_duration > 0:
                # Сколько задач можно выполнить за час при текущей скорости
                tasks_per_hour = 60 / avg_duration
                # Сколько очков можно заработать за час
                points_per_hour = round((points / completed) * tasks_per_hour, 2)
            elif total_hours > 0:
                # Стандартный расчет, если есть время работы
                points_per_hour = round(points / total_hours, 2)
            else:
                points_per_hour = 0
            
            # Расчет стоимости очка (руб/очко)
            # Используем месячную зарплату и предполагаемое количество очков за месяц
            if points_per_hour > 0:
                # Предполагаем 160 рабочих часов в месяц (8 часов * 20 дней)
                monthly_points_estimate = points_per_hour * 160
                # Стоимость одного очка
                salary_per_point = round(salary / monthly_points_estimate, 2)
            else:
                salary_per_point = 0
            
            status = "✅ Активен" if active else "❌ Неактивен"
            response += f"*{name}* (ID: {emp_id}) - {status}\n"
            response += f"📝 Выполнено задач: {completed}\n"
            response += f"🏆 Всего очков: {points}\n"
            response += f"⏱ Среднее время на задачу: {round(avg_duration, 2)} мин.\n"
            response += f"⌛ Общее время работы: {round(total_hours, 2)} ч.\n"
            response += f"📈 Эффективность: {points_per_hour} очков/час\n"
            response += f"💰 Стоимость очка: {salary_per_point} руб.\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown', reply_markup=reply_markup)
        return ANALYTICS
    
    elif text == "👥 Показать всех":
        context.user_data['show_all_employees'] = True
        # Повторно вызываем аналитику по сотрудникам
        context.user_data['last_analytics_command'] = "👥 По сотрудникам"
        return await analytics(update, context)
    
    elif text == "👥 Только активные":
        context.user_data['show_all_employees'] = False
        # Повторно вызываем аналитику по сотрудникам
        context.user_data['last_analytics_command'] = "👥 По сотрудникам"
        return await analytics(update, context)
    elif text == "🎯 По задачам":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем статистику по задачам за выбранный период
        cursor.execute("""
            SELECT 
                t.id,
                t.name,
                t.category,
                COUNT(c.id) as completed_count,
                AVG(c.duration_seconds) / 60.0 as avg_duration,
                t.points
            FROM tasks t
            LEFT JOIN completed_tasks c ON t.id = c.task_id AND c.end_time >= ?
            GROUP BY t.id
            ORDER BY completed_count DESC
        """, (start_date.isoformat(),))
        tasks_stats = cursor.fetchall()
        conn.close()
        
        if not tasks_stats:
            await update.message.reply_text("Нет данных о задачах.")
            return ANALYTICS
        
        response = f"📊 *Аналитика по задачам за {period_name}*\n\n"
        
        current_category = None
        for task in tasks_stats:
            task_id, name, category, completed, avg_duration, points = task
            
            # Преобразуем None в 0
            completed = completed or 0
            avg_duration = avg_duration or 0
            
            if category != current_category:
                response += f"\n*{category}*\n"
                current_category = category
            
            response += f"• {name} ({points} очков)\n"
            response += f"  Выполнено: {completed} раз\n"
            response += f"  Среднее время: {round(avg_duration, 2)} мин.\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        return ANALYTICS
    
    elif text == "📈 Общая статистика":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Общая статистика за выбранный период
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT c.employee_id) as active_employees,
                COUNT(c.id) as total_completed,
                SUM(c.points_earned) as total_points,
                AVG(c.duration_seconds) / 60.0 as avg_task_duration,
                SUM(c.duration_seconds) / 3600.0 as total_hours
            FROM completed_tasks c
            JOIN employees e ON c.employee_id = e.id
            WHERE c.end_time >= ? AND e.active = 1
        """, (start_date.isoformat(),))
        general_stats = cursor.fetchone()
        
        # Статистика по категориям за выбранный период
        cursor.execute("""
            SELECT 
                t.category,
                COUNT(c.id) as category_count,
                SUM(c.points_earned) as category_points,
                AVG(c.duration_seconds) / 60.0 as category_avg_duration
            FROM completed_tasks c
            JOIN tasks t ON c.task_id = t.id
            JOIN employees e ON c.employee_id = e.id
            WHERE c.end_time >= ? AND e.active = 1
            GROUP BY t.category
            ORDER BY category_points DESC
        """, (start_date.isoformat(),))
        category_stats = cursor.fetchall()
        
        # Статистика по дням недели за выбранный период
        cursor.execute("""
            SELECT 
                strftime('%w', substr(c.end_time, 1, 10)) as day_of_week,
                COUNT(c.id) as day_count,
                SUM(c.points_earned) as day_points
            FROM completed_tasks c
            JOIN employees e ON c.employee_id = e.id
            WHERE c.end_time >= ? AND e.active = 1
            GROUP BY day_of_week
            ORDER BY day_of_week
        """, (start_date.isoformat(),))
        day_stats = cursor.fetchall()
        
        conn.close()
        
        if not general_stats[0]:
            await update.message.reply_text(f"Нет данных для анализа за {period_name}.")
            return ANALYTICS
        
        active_employees, total_completed, total_points, avg_task_duration, total_hours = general_stats
        
        # Преобразуем None в 0
        active_employees = active_employees or 0
        total_completed = total_completed or 0
        total_points = total_points or 0
        avg_task_duration = avg_task_duration or 0
        total_hours = total_hours or 0
        
        response = f"📊 *Общая статистика за {period_name}*\n\n"
        response += f"👥 Активных сотрудников: {active_employees}\n"
        response += f"📝 Всего выполнено задач: {total_completed}\n"
        response += f"🏆 Всего заработано очков: {total_points}\n"
        response += f"⏱ Среднее время на задачу: {round(avg_task_duration, 2)} мин.\n"
        response += f"⌛ Общее время работы: {round(total_hours, 2)} ч.\n\n"
        
        if category_stats:
            response += "*Статистика по категориям:*\n"
            for category, count, points, avg_duration in category_stats:
                # Преобразуем None в 0
                count = count or 0
                points = points or 0
                avg_duration = avg_duration or 0
                
                response += f"• {category}: {count} задач, {points} очков, {round(avg_duration, 2)} мин. в среднем\n"
            response += "\n"
        
        if day_stats:
            days = ["Воскресенье", "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота"]
            response += "*Статистика по дням недели:*\n"
            for day_num, count, points in day_stats:
                # Преобразуем None в 0
                count = count or 0
                points = points or 0
                
                day_name = days[int(day_num)]
                response += f"• {day_name}: {count} задач, {points} очков\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        return ANALYTICS
    
    elif text == "🔙 Назад":
        keyboard = [
            ["За сегодня", "За неделю"],
            ["За месяц", "За всё время"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите период для анализа:", reply_markup=reply_markup)
        return SELECT_PERIOD
    
    else:
        await update.message.reply_text("Неверная команда. Пожалуйста, используйте кнопки меню.")
        return ANALYTICS

# Обработчик выбора сотрудника для назначения задачи
async def select_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🔙 Назад":
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
    
    try:
        employee_id = int(text.split("ID: ")[1])
        employee_name = text.split(" - ID:")[0]
        context.user_data['selected_employee_id'] = employee_id
        context.user_data['selected_employee_name'] = employee_name
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, points, category FROM tasks ORDER BY category")
        tasks = cursor.fetchall()
        conn.close()
        
        if not tasks:
            await update.message.reply_text("Нет доступных задач.")
            return ADMIN_MENU
        
        keyboard = []
        current_category = None
        
        for task in tasks:
            task_id, task_name, points, category = task
            
            if category != current_category:
                if keyboard:
                    keyboard.append([])
                current_category = category
                keyboard.append([f"--- {category} ---"])
            
            keyboard.append([f"{task_name} ({points} очков) - ID: {task_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(f"Выберите задачу для сотрудника {employee_name}:", reply_markup=reply_markup)
        return ASSIGN_TASK
        
    except (IndexError, ValueError):
        await update.message.reply_text("Не удалось определить ID сотрудника. Пожалуйста, выберите сотрудника из списка.")
        return SELECT_EMPLOYEE

# Обработчик назначения задачи сотруднику
async def assign_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🔙 Назад":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name FROM employees WHERE active = 1 ORDER BY name")
        employees = cursor.fetchall()
        conn.close()
        
        keyboard = []
        for emp_id, emp_name in employees:
            keyboard.append([f"{emp_name} - ID: {emp_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите сотрудника для назначения задачи:", reply_markup=reply_markup)
        return SELECT_EMPLOYEE
    
    # Проверяем, что это не заголовок категории
    if text.startswith("--- ") and text.endswith(" ---"):
        await update.message.reply_text("Это заголовок категории. Пожалуйста, выберите задачу.")
        return ASSIGN_TASK
    
    try:
        task_id = int(text.split("ID: ")[1])
        employee_id = context.user_data['selected_employee_id']
        employee_name = context.user_data['selected_employee_name']
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем информацию о задаче
        cursor.execute("SELECT name, points FROM tasks WHERE id = ?", (task_id,))
        task_info = cursor.fetchone()
        
        if not task_info:
            conn.close()
            await update.message.reply_text("Задача не найдена.")
            return ASSIGN_TASK
        
        task_name, points = task_info
        
        # Добавляем задачу в активные для выбранного сотрудника
        now = datetime.now().isoformat()
        cursor.execute(
            "INSERT INTO active_tasks (employee_id, task_id, start_time) VALUES (?, ?, ?)",
            (employee_id, task_id, now)
        )
        conn.commit()
        
        # Получаем telegram_id сотрудника для уведомления
        cursor.execute("SELECT telegram_id FROM employees WHERE id = ?", (employee_id,))
        telegram_id = cursor.fetchone()[0]
        
        conn.close()
        
        await update.message.reply_text(
            f"✅ Задача '{task_name}' ({points} очков) успешно назначена сотруднику {employee_name}."
        )
        
        # Уведомляем сотрудника, если у него есть привязанный аккаунт
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🔔 Вам назначена новая задача: '{task_name}' ({points} очков).\n"
                         f"Время начала: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}"
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление сотруднику: {e}")
        
        # Возвращаемся в меню администратора
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
        
    except (IndexError, ValueError, KeyError):
        await update.message.reply_text("Не удалось определить ID задачи или сотрудника. Пожалуйста, попробуйте снова.")
        return ASSIGN_TASK

# Обработчик выбора сотрудника для редактирования
async def select_employee_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🔙 Назад":
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
    
    try:
        employee_id = int(text.split("ID: ")[1])
        employee_name = text.split(" (ЗП:")[0]
        
        context.user_data['edit_employee_id'] = employee_id
        context.user_data['edit_employee_name'] = employee_name
        
        keyboard = [
            ["Изменить имя", "Изменить зарплату"],
            ["Деактивировать сотрудника", "🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(f"Выберите действие для сотрудника {employee_name}:", reply_markup=reply_markup)
        return EDIT_EMPLOYEE
        
    except (IndexError, ValueError):
        await update.message.reply_text("Не удалось определить ID сотрудника. Пожалуйста, выберите сотрудника из списка.")
        return SELECT_EMPLOYEE_EDIT

# Обработчик редактирования сотрудника
async def edit_employee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    employee_id = context.user_data.get('edit_employee_id')
    employee_name = context.user_data.get('edit_employee_name')
    
    if not employee_id:
        await update.message.reply_text("Ошибка: не выбран сотрудник для редактирования.")
        return ADMIN_MENU
    
    if text == "Изменить имя":
        await update.message.reply_text(f"Введите новое имя для сотрудника {employee_name}:")
        return EDIT_EMPLOYEE_NAME
    
    elif text == "Изменить зарплату":
        await update.message.reply_text(f"Введите новую зарплату для сотрудника {employee_name}:")
        return EDIT_EMPLOYEE_SALARY
    
    elif text == "Деактивировать сотрудника":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Проверяем, есть ли у сотрудника активные задачи
        cursor.execute("SELECT COUNT(*) FROM active_tasks WHERE employee_id = ?", (employee_id,))
        active_count = cursor.fetchone()[0]
        
        if active_count > 0:
            conn.close()
            await update.message.reply_text(
                f"Невозможно деактивировать сотрудника {employee_name}, так как у него есть активные задачи. "
                f"Сначала отмените все активные задачи."
            )
            return EDIT_EMPLOYEE
        
        # Вместо удаления, меняем статус на неактивный
        cursor.execute("UPDATE employees SET active = 0 WHERE id = ?", (employee_id,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Сотрудник {employee_name} успешно деактивирован.")
        
        # Возвращаемся в меню администратора
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
    
    elif text == "🔙 Назад":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, salary FROM employees WHERE active = 1 ORDER BY name")
        employees = cursor.fetchall()
        conn.close()
        
        keyboard = []
        for emp_id, emp_name, emp_salary in employees:
            keyboard.append([f"{emp_name} (ЗП: {emp_salary} руб.) - ID: {emp_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите сотрудника для редактирования:", reply_markup=reply_markup)
        return SELECT_EMPLOYEE_EDIT
    
    else:
        await update.message.reply_text("Неверная команда. Пожалуйста, используйте кнопки меню.")
        return EDIT_EMPLOYEE

# Обработчик изменения имени сотрудника
async def edit_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    employee_id = context.user_data.get('edit_employee_id')
    old_name = context.user_data.get('edit_employee_name')
    
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    
    cursor.execute("UPDATE employees SET name = ? WHERE id = ?", (new_name, employee_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Имя сотрудника изменено с '{old_name}' на '{new_name}'.")
    
    # Возвращаемся к списку сотрудников
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, salary FROM employees WHERE active = 1 ORDER BY name")
    employees = cursor.fetchall()
    conn.close()
    
    keyboard = []
    for emp_id, emp_name, emp_salary in employees:
        keyboard.append([f"{emp_name} (ЗП: {emp_salary} руб.) - ID: {emp_id}"])
    
    keyboard.append(["🔙 Назад"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text("Выберите сотрудника для редактирования:", reply_markup=reply_markup)
    return SELECT_EMPLOYEE_EDIT

# Обработчик изменения зарплаты сотрудника
async def edit_employee_salary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_salary = float(update.message.text)
        employee_id = context.user_data.get('edit_employee_id')
        employee_name = context.user_data.get('edit_employee_name')
        
        if new_salary <= 0:
            await update.message.reply_text("Зарплата должна быть положительным числом.")
            return EDIT_EMPLOYEE_SALARY
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        cursor.execute("UPDATE employees SET salary = ? WHERE id = ?", (new_salary, employee_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Зарплата сотрудника {employee_name} изменена на {new_salary} руб.")
        
        # Возвращаемся к списку сотрудников
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, salary FROM employees WHERE active = 1 ORDER BY name")
        employees = cursor.fetchall()
        conn.close()
        
        keyboard = []
        for emp_id, emp_name, emp_salary in employees:
            keyboard.append([f"{emp_name} (ЗП: {emp_salary} руб.) - ID: {emp_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите сотрудника для редактирования:", reply_markup=reply_markup)
        return SELECT_EMPLOYEE_EDIT
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное число для зарплаты.")
        return EDIT_EMPLOYEE_SALARY

# Обработчик выбора задачи для редактирования
async def select_task_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🔙 Назад":
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
    
    # Проверяем, что это не заголовок категории
    if text.startswith("--- ") and text.endswith(" ---"):
        await update.message.reply_text("Это заголовок категории. Пожалуйста, выберите задачу.")
        return SELECT_TASK_EDIT
    
    try:
        task_id = int(text.split("ID: ")[1])
        task_name = text.split(" (")[0]
        
        context.user_data['edit_task_id'] = task_id
        context.user_data['edit_task_name'] = task_name
        
        keyboard = [
            ["Изменить название", "Изменить очки"],
            ["Изменить категорию", "Удалить задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(f"Выберите действие для задачи '{task_name}':", reply_markup=reply_markup)
        return EDIT_TASK
        
    except (IndexError, ValueError):
        await update.message.reply_text("Не удалось определить ID задачи. Пожалуйста, выберите задачу из списка.")
        return SELECT_TASK_EDIT

# Обработчик редактирования задачи
async def edit_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    task_id = context.user_data.get('edit_task_id')
    task_name = context.user_data.get('edit_task_name')
    
    if not task_id:
        await update.message.reply_text("Ошибка: не выбрана задача для редактирования.")
        return ADMIN_MENU
    
    if text == "Изменить название":
        await update.message.reply_text(f"Введите новое название для задачи '{task_name}':")
        return EDIT_TASK_NAME
    
    elif text == "Изменить очки":
        await update.message.reply_text(f"Введите новое количество очков для задачи '{task_name}':")
        return EDIT_TASK_POINTS
    
    elif text == "Изменить категорию":
        keyboard = [
            ["Распаковка", "Логистика"],
            ["Продажи", "Маркетинг"],
            ["Закупка", "Другое"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text(f"Выберите новую категорию для задачи '{task_name}':", reply_markup=reply_markup)
        return EDIT_TASK_CATEGORY
    
    elif text == "Удалить задачу":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Проверяем, есть ли активные задачи с этой задачей
        cursor.execute("SELECT COUNT(*) FROM active_tasks WHERE task_id = ?", (task_id,))
        active_count = cursor.fetchone()[0]
        
        if active_count > 0:
            conn.close()
            await update.message.reply_text(
                f"Невозможно удалить задачу '{task_name}', так как она сейчас выполняется. "
                f"Сначала отмените все активные задачи с этой задачей."
            )
            return EDIT_TASK
        
        # Удаляем задачу
        cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Задача '{task_name}' успешно удалена.")
        
        # Возвращаемся в меню администратора
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
    
    elif text == "🔙 Назад":
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, points, category FROM tasks ORDER BY category, name")
        tasks = cursor.fetchall()
        conn.close()
        
        keyboard = []
        current_category = None
        
        for task in tasks:
            task_id, task_name, points, category = task
            
            if category != current_category:
                if keyboard:
                    keyboard.append([])
                current_category = category
                keyboard.append([f"--- {category} ---"])
            
            keyboard.append([f"{task_name} ({points} очков) - ID: {task_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите задачу для редактирования:", reply_markup=reply_markup)
        return SELECT_TASK_EDIT
    
    else:
        await update.message.reply_text("Неверная команда. Пожалуйста, используйте кнопки меню.")
        return EDIT_TASK

# Обработчик изменения названия задачи
async def edit_task_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text
    task_id = context.user_data.get('edit_task_id')
    old_name = context.user_data.get('edit_task_name')
    
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    
    cursor.execute("UPDATE tasks SET name = ? WHERE id = ?", (new_name, task_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Название задачи изменено с '{old_name}' на '{new_name}'.")
    
    # Возвращаемся к списку задач
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, points, category FROM tasks ORDER BY category, name")
    tasks = cursor.fetchall()
    conn.close()
    
    keyboard = []
    current_category = None
    
    for task in tasks:
        task_id, task_name, points, category = task
        
        if category != current_category:
            if keyboard:
                keyboard.append([])
            current_category = category
            keyboard.append([f"--- {category} ---"])
        
        keyboard.append([f"{task_name} ({points} очков) - ID: {task_id}"])
    
    keyboard.append(["🔙 Назад"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text("Выберите задачу для редактирования:", reply_markup=reply_markup)
    return SELECT_TASK_EDIT

# Обработчик изменения очков задачи
async def edit_task_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        new_points = int(update.message.text)
        task_id = context.user_data.get('edit_task_id')
        task_name = context.user_data.get('edit_task_name')
        
        if new_points <= 0:
            await update.message.reply_text("Количество очков должно быть положительным числом.")
            return EDIT_TASK_POINTS
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        cursor.execute("UPDATE tasks SET points = ? WHERE id = ?", (new_points, task_id))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(f"✅ Количество очков для задачи '{task_name}' изменено на {new_points}.")
        
        # Возвращаемся к списку задач
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, name, points, category FROM tasks ORDER BY category, name")
        tasks = cursor.fetchall()
        conn.close()
        
        keyboard = []
        current_category = None
        
        for task in tasks:
            task_id, task_name, points, category = task
            
            if category != current_category:
                if keyboard:
                    keyboard.append([])
                current_category = category
                keyboard.append([f"--- {category} ---"])
            
            keyboard.append([f"{task_name} ({points} очков) - ID: {task_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите задачу для редактирования:", reply_markup=reply_markup)
        return SELECT_TASK_EDIT
        
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректное целое число для очков.")
        return EDIT_TASK_POINTS

# Обработчик изменения категории задачи
async def edit_task_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_category = update.message.text
    task_id = context.user_data.get('edit_task_id')
    task_name = context.user_data.get('edit_task_name')
    
    # Проверяем, что категория выбрана из предложенных
    valid_categories = ["Распаковка", "Логистика", "Продажи", "Маркетинг", "Закупка", "Другое"]
    if new_category not in valid_categories:
        await update.message.reply_text("Пожалуйста, выберите категорию из предложенных вариантов.")
        return EDIT_TASK_CATEGORY
    
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    
    cursor.execute("UPDATE tasks SET category = ? WHERE id = ?", (new_category, task_id))
    conn.commit()
    conn.close()
    
    await update.message.reply_text(f"✅ Категория задачи '{task_name}' изменена на '{new_category}'.")
    
    # Возвращаемся к списку задач
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, points, category FROM tasks ORDER BY category, name")
    tasks = cursor.fetchall()
    conn.close()
    
    keyboard = []
    current_category = None
    
    for task in tasks:
        task_id, task_name, points, category = task
        
        if category != current_category:
            if keyboard:
                keyboard.append([])
            current_category = category
            keyboard.append([f"--- {category} ---"])
        
        keyboard.append([f"{task_name} ({points} очков) - ID: {task_id}"])
    
    keyboard.append(["🔙 Назад"])
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text("Выберите задачу для редактирования:", reply_markup=reply_markup)
    return SELECT_TASK_EDIT

# Обработчик выбора активной задачи для отмены
async def select_active_task_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🔙 Назад":
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
    
    try:
        active_task_id = int(text.split("ID: ")[1])
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем информацию об активной задаче
        cursor.execute("""
            SELECT a.id, e.name as employee_name, t.name as task_name, a.start_time, e.telegram_id
            FROM active_tasks a
            JOIN employees e ON a.employee_id = e.id
            JOIN tasks t ON a.task_id = t.id
            WHERE a.id = ?
        """, (active_task_id,))
        
        task_info = cursor.fetchone()
        
        if not task_info:
            conn.close()
            await update.message.reply_text("Задача не найдена.")
            return SELECT_ACTIVE_TASK_CANCEL
        
        _, employee_name, task_name, start_time, telegram_id = task_info
        
        # Удаляем активную задачу
        cursor.execute("DELETE FROM active_tasks WHERE id = ?", (active_task_id,))
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ Задача '{task_name}' отменена для сотрудника {employee_name}."
        )
        
        # Уведомляем сотрудника, если у него есть привязанный аккаунт
        if telegram_id:
            try:
                await context.bot.send_message(
                    chat_id=telegram_id,
                    text=f"🔔 Ваша задача '{task_name}' была отменена администратором."
                )
            except Exception as e:
                logger.error(f"Не удалось отправить уведомление сотруднику: {e}")
        
        # Возвращаемся к списку активных задач
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT a.id, e.name as employee_name, t.name as task_name, a.start_time
            FROM active_tasks a
            JOIN employees e ON a.employee_id = e.id
            JOIN tasks t ON a.task_id = t.id
            ORDER BY e.name, a.start_time
        """)
        
        active_tasks = cursor.fetchall()
        conn.close()
        
        if not active_tasks:
            await update.message.reply_text("Нет активных задач.")
            
            keyboard = [
                ["👤 Добавить сотрудника", "📋 Добавить задачу"],
                ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
                ["📝 Назначить задачу", "📊 Аналитика"],
                ["📋 История задач", "❌ Отменить активную задачу"],
                ["🔙 Назад"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
            return ADMIN_MENU
        
        keyboard = []
        current_employee = None
        
        for task in active_tasks:
            task_id, employee_name, task_name, start_time = task
            start_datetime = datetime.fromisoformat(start_time)
            duration = (datetime.now() - start_datetime).total_seconds() / 60.0  # в минутах
            
            if employee_name != current_employee:
                if keyboard:
                    keyboard.append([])
                current_employee = employee_name
                keyboard.append([f"--- {employee_name} ---"])
            
            keyboard.append([f"{task_name} ({round(duration, 2)} мин.) - ID: {task_id}"])
        
        keyboard.append(["🔙 Назад"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выберите активную задачу для отмены:", reply_markup=reply_markup)
        return SELECT_ACTIVE_TASK_CANCEL
        
    except (IndexError, ValueError):
        await update.message.reply_text("Не удалось определить ID задачи. Пожалуйста, выберите задачу из списка.")
        return SELECT_ACTIVE_TASK_CANCEL

# Обработчик просмотра истории задач
async def view_task_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text == "🔙 Назад":
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
    
    try:
        employee_id = int(text.split("ID: ")[1])
        employee_name = text.split(" - ID:")[0]
        
        conn = sqlite3.connect('shoeshop.db')
        cursor = conn.cursor()
        
        # Получаем последние 20 выполненных задач сотрудника
        cursor.execute("""
            SELECT 
                c.id,
                t.name as task_name,
                c.points_earned,
                c.start_time,
                c.end_time,
                c.duration_seconds / 60.0 as duration_minutes
            FROM completed_tasks c
            JOIN tasks t ON c.task_id = t.id
            WHERE c.employee_id = ?
            ORDER BY c.end_time DESC
            LIMIT 20
        """, (employee_id,))
        
        completed_tasks = cursor.fetchall()
        conn.close()
        
        if not completed_tasks:
            await update.message.reply_text(f"У сотрудника {employee_name} нет выполненных задач в истории.")
            
            keyboard = [
                ["👤 Добавить сотрудника", "📋 Добавить задачу"],
                ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
                ["📝 Назначить задачу", "📊 Аналитика"],
                ["📋 История задач", "❌ Отменить активную задачу"],
                ["🔙 Назад"]
            ]
            reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
            await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
            return ADMIN_MENU
        
        response = f"📋 *История выполненных задач сотрудника {employee_name} (последние 20)*\n\n"
        
        for task in completed_tasks:
            _, task_name, points, start_time, end_time, duration = task
            
            start_datetime = datetime.fromisoformat(start_time)
            end_datetime = datetime.fromisoformat(end_time)
            
            response += f"📝 *{task_name}*\n"
            response += f"🏆 Очки: {points}\n"
            response += f"⏱ Время выполнения: {round(duration, 2)} мин.\n"
            response += f"🕒 Начало: {start_datetime.strftime('%d.%m.%Y %H:%M')}\n"
            response += f"🏁 Завершение: {end_datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        await update.message.reply_text(response, parse_mode='Markdown')
        
        keyboard = [
            ["👤 Добавить сотрудника", "📋 Добавить задачу"],
            ["✏️ Изменить сотрудника", "✏️ Изменить задачу"],
            ["📝 Назначить задачу", "📊 Аналитика"],
            ["📋 История задач", "❌ Отменить активную задачу"],
            ["🔙 Назад"]
        ]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Меню администратора", reply_markup=reply_markup)
        return ADMIN_MENU
        
    except (IndexError, ValueError):
        await update.message.reply_text("Не удалось определить ID сотрудника. Пожалуйста, выберите сотрудника из списка.")
        return VIEW_TASK_HISTORY

# Обработчик команды регистрации сотрудника
# Обработчик команды регистрации сотрудника
async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # Проверяем, зарегистрирован ли уже пользователь
    conn = sqlite3.connect('shoeshop.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM employees WHERE telegram_id = ?", (user_id,))
    existing_employee = cursor.fetchone()
    
    if existing_employee:
        conn.close()
        await update.message.reply_text(
            f"Вы уже зарегистрированы как сотрудник {existing_employee[1]} (ID: {existing_employee[0]})."
        )
        return
    
    # Проверяем, передан ли ID сотрудника
    if not context.args:
        conn.close()
        await update.message.reply_text(
            "Для регистрации укажите ваш ID сотрудника: /register ID\n"
            "Например: /register 123"
        )
        return
    
    try:
        employee_id = int(context.args[0])
        
        # Проверяем, существует ли сотрудник с таким ID
        cursor.execute("SELECT name, active FROM employees WHERE id = ?", (employee_id,))
        employee = cursor.fetchone()
        
        if not employee:
            conn.close()
            await update.message.reply_text(f"Сотрудник с ID {employee_id} не найден.")
            return
        
        employee_name, is_active = employee
        
        if not is_active:
            conn.close()
            await update.message.reply_text(f"Сотрудник с ID {employee_id} деактивирован. Обратитесь к администратору.")
            return
        
        # Проверяем, не привязан ли уже этот сотрудник к другому аккаунту
        cursor.execute("SELECT telegram_id FROM employees WHERE id = ?", (employee_id,))
        telegram_id = cursor.fetchone()[0]
        
        if telegram_id and telegram_id != user_id:
            conn.close()
            await update.message.reply_text("Этот сотрудник уже привязан к другому аккаунту Telegram.")
            return
        
        # Привязываем Telegram ID к сотруднику
        cursor.execute(
            "UPDATE employees SET telegram_id = ? WHERE id = ?",
            (user_id, employee_id)
        )
        
        conn.commit()
        conn.close()
        
        await update.message.reply_text(
            f"✅ Вы успешно зарегистрированы как сотрудник {employee_name}.\n"
            f"Теперь вы можете использовать функции бота для сотрудников."
        )
        
        # Показываем главное меню
        keyboard = []
        
        if is_admin(user_id):
            keyboard.append(["👨‍💼 Меню администратора"])
        
        keyboard.append(["👷 Меню сотрудника"])
        
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Выберите режим работы:", reply_markup=reply_markup)
        
    except ValueError:
        conn.close()
        await update.message.reply_text("ID сотрудника должен быть числом.")


# Основная функция
def main():
    # Инициализация базы данных
    init_db()
    fill_initial_data()
    
    # Создание механизма персистентности для сохранения состояния разговоров
    persistence = PicklePersistence(filepath="shoeshop_bot_data.pickle")
    
    # Создание приложения с персистентностью
    application = Application.builder().token("7661062439:AAGcUacoYmkvExmgsr9EGEShn8aSjXLVFss").persistence(persistence).build()
    
    # Регистрация обработчиков
    application.add_handler(CommandHandler("register", register))
    
    # Обработчик разговора
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            MAIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, main_menu)],
            ADMIN_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_menu)],
            EMPLOYEE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, employee_menu)],
            ENTER_EMPLOYEE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_employee_name)],
            ENTER_EMPLOYEE_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_employee_salary)],
            ENTER_TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_task_name)],
            ENTER_TASK_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_task_points)],
            ADD_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_task)],
            TAKE_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, take_task)],
            COMPLETE_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, complete_task)],
            SELECT_PERIOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_period)],
            ANALYTICS: [MessageHandler(filters.TEXT & ~filters.COMMAND, analytics)],
            SELECT_EMPLOYEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_employee)],
            ASSIGN_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, assign_task)],
            SELECT_EMPLOYEE_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_employee_edit)],
            EDIT_EMPLOYEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_employee)],
            EDIT_EMPLOYEE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_employee_name)],
            EDIT_EMPLOYEE_SALARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_employee_salary)],
            SELECT_TASK_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_task_edit)],
            EDIT_TASK: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task)],
            EDIT_TASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_name)],
            EDIT_TASK_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_points)],
            EDIT_TASK_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_task_category)],
            SELECT_ACTIVE_TASK_CANCEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_active_task_cancel)],
            VIEW_TASK_HISTORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, view_task_history)],
        },
        fallbacks=[CommandHandler("start", start)],
        name="main_conversation",
        persistent=True
    )
    
    application.add_handler(conv_handler)
    
    # Запуск бота
    application.run_polling()

if __name__ == "__main__":
    main()
