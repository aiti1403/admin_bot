# Telegram Bot для управления задачами сотрудников магазина кроссовок

Этот бот позволяет эффективно управлять задачами сотрудников магазина кроссовок, отслеживать их выполнение и анализировать эффективность работы.

## Функциональность

### Для администраторов:
- Добавление и редактирование сотрудников
- Добавление и редактирование задач
- Назначение задач сотрудникам
- Отмена активных задач
- Просмотр аналитики (по сотрудникам, задачам, общая)
- Просмотр истории выполненных задач

### Для сотрудников:
- Взятие задач на выполнение
- Завершение задач
- Просмотр личной статистики

## Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/aiti1403/admin_bot
cd admin_bot
```

2. Установите необходимые зависимости:
```bash
pip install python-telegram-bot
```

3. Запустите бота:
```bash
python main.py
```

## Структура базы данных

Бот использует SQLite для хранения данных:

- **employees** - таблица сотрудников (id, name, salary, telegram_id, active)
- **tasks** - таблица задач (id, name, points, category)
- **active_tasks** - таблица активных задач (id, employee_id, task_id, start_time)
- **completed_tasks** - таблица выполненных задач (id, employee_id, task_id, start_time, end_time, points_earned, duration_seconds)

## Использование

### Регистрация сотрудника

Сотрудник может зарегистрироваться в боте с помощью команды:
```
/register ID
```
где ID - идентификатор сотрудника, полученный от администратора.

### Администрирование

Администраторы имеют доступ к расширенному функционалу бота через меню администратора:
- Управление сотрудниками (добавление, редактирование, деактивация)
- Управление задачами (добавление, редактирование, удаление)
- Назначение задач конкретным сотрудникам
- Отмена активных задач
- Просмотр аналитики за разные периоды (день, неделя, месяц, всё время)
- Просмотр истории выполненных задач

### Работа с задачами

Сотрудники могут:
- Брать задачи на выполнение (до 3 одновременно)
- Отмечать задачи как выполненные
- Просматривать свою статистику (выполненные задачи, заработанные очки, среднее время выполнения)

## Аналитика

Бот предоставляет различные виды аналитики:
- По сотрудникам (эффективность, время работы, стоимость очка)
- По задачам (частота выполнения, среднее время)
- Общая статистика (активность по дням недели, категориям задач)

## Категории задач

Задачи разделены на категории:
- Распаковка
- Логистика
- Продажи
- Маркетинг
- Закупка
- Другое

## Настройка

Для настройки бота отредактируйте следующие параметры в файле `main.py`:

- `ADMIN_IDS` - список ID администраторов в Telegram
- Токен бота в функции `main()`

## Требования

- Python 3.7+
- python-telegram-bot 20.0+
- SQLite3

## Лицензия

MIT
