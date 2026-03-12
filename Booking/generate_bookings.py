#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для генерации и загрузки тестовых бронирований за 2025 год
Учитывает сезонность, выходные, праздники и реальных пользователей из БД
Интерактивный режим с выбором параметров
"""

import random
import sqlite3
import os
from datetime import datetime, timedelta, date
import sys

# Конфигурация
DB_PATH = "booking.db"
OUTPUT_FILE = "test_bookings_2025.txt"

# Временные слоты (как в приложении)
TIME_SLOTS = [
    "09:00-11:00", "11:00-13:00", "13:00-15:00",
    "15:00-17:00", "17:00-19:00", "19:00-21:00"
]

# Номера машин
MACHINE_NUMBERS = [1, 2, 3]

# Праздничные дни в России (2025 год)
HOLIDAYS_2025 = [
    "01.01.2025", "02.01.2025", "03.01.2025", "04.01.2025", "05.01.2025", "06.01.2025", "07.01.2025", "08.01.2025",
    # Новогодние
    "23.02.2025",  # День защитника Отечества
    "08.03.2025",  # Международный женский день
    "01.05.2025", "02.05.2025",  # Праздник весны и труда
    "09.05.2025", "10.05.2025",  # День Победы
    "12.06.2025",  # День России
    "04.11.2025",  # День народного единства
    "31.12.2025",  # Канун Нового года
]

# Сезонные коэффициенты (поправка к вероятности бронирования)
SEASONAL_FACTORS = {
    "winter": 1.3,  # зимой стираются чаще
    "spring": 1.1,
    "summer": 0.7,  # летом многие в отпусках
    "autumn": 1.2,
}

# Дневные коэффициенты по часам
HOUR_FACTORS = {
    9: 0.8,  # 9-11 утра - средняя активность
    11: 1.2,  # 11-13 - пик перед обедом
    13: 1.5,  # 13-15 - самый популярный слот (после обеда)
    15: 1.3,  # 15-17 - высокая активность
    17: 1.0,  # 17-19 - средняя
    19: 0.6,  # 19-21 - низкая
}

# Специальные события (повышенный спрос)
SPECIAL_EVENTS = {
    "01.09.2025": 1.8,  # День знаний
    "25.01.2025": 1.5,  # Татьянин день (студенческий)
    "14.02.2025": 1.3,  # День святого Валентина
    "23.02.2025": 1.4,  # 23 февраля
    "08.03.2025": 1.4,  # 8 марта
}


def clear_screen():
    """Очищает экран консоли"""
    os.system('cls' if os.name == 'nt' else 'clear')


def print_header(title):
    """Печатает красивый заголовок"""
    print("=" * 70)
    print(f"{title:^70}")
    print("=" * 70)


def print_menu():
    """Печатает меню выбора"""
    print("\n" + "-" * 70)
    print("ГЛАВНОЕ МЕНЮ:")
    print("1. Сгенерировать бронирования за весь 2025 год")
    print("2. Сгенерировать бронирования за конкретный месяц")
    print("3. Сгенерировать бронирования за конкретный период")
    print("4. Загрузить бронирования из файла в БД")
    print("5. Посмотреть статистику по пользователям")
    print("6. Очистить таблицу бронирований")
    print("7. Выйти")
    print("-" * 70)


def get_season(month):
    """Определяет сезон по месяцу"""
    if month in [12, 1, 2]:
        return "winter"
    elif month in [3, 4, 5]:
        return "spring"
    elif month in [6, 7, 8]:
        return "summer"
    else:
        return "autumn"


def is_holiday(date_str):
    """Проверяет, является ли дата праздничной"""
    return date_str in HOLIDAYS_2025


def get_special_event_factor(date_str):
    """Возвращает коэффициент для специальных событий"""
    return SPECIAL_EVENTS.get(date_str, 1.0)


def get_users_from_db():
    """Получает список пользователей из базы данных"""
    if not os.path.exists(DB_PATH):
        print(f"\n❌ Ошибка: База данных {DB_PATH} не найдена!")
        print("Сначала запустите приложение и создайте пользователей")
        return None

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT id, fio, phone FROM user ORDER BY id")
        users = cursor.fetchall()
        conn.close()

        if not users:
            print("\n❌ В базе данных нет пользователей!")
            print("Сначала запустите generate_users.py для создания пользователей")
            return None

        return users
    except Exception as e:
        print(f"\n❌ Ошибка при чтении БД: {e}")
        return None


def show_users_stats(users):
    """Показывает статистику по пользователям"""
    print("\n" + "-" * 70)
    print("СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ:")
    print(f"Всего пользователей в БД: {len(users)}")

    # Показываем первых 5 пользователей
    print("\nПервые 5 пользователей:")
    for i, user in enumerate(users[:5], 1):
        user_id, fio, phone = user
        print(f"  {i}. ID: {user_id} | {fio} | {phone}")

    if len(users) > 5:
        print(f"  ... и ещё {len(users) - 5} пользователей")

    print("-" * 70)


def generate_booking_probability(base_date, hour):
    """
    Рассчитывает вероятность бронирования для конкретного часа
    с учётом всех факторов
    """
    dt = datetime.strptime(base_date, "%d.%m.%Y")
    month = dt.month
    day_of_week = dt.weekday()
    date_str = base_date

    # Базовая вероятность
    prob = 0.3

    # Фактор выходного дня
    if day_of_week >= 5:  # суббота или воскресенье
        prob *= 1.4

    # Фактор праздника
    if is_holiday(date_str):
        prob *= 1.6

    # Специальные события
    prob *= get_special_event_factor(date_str)

    # Сезонный фактор
    season = get_season(month)
    prob *= SEASONAL_FACTORS[season]

    # Часовой фактор
    prob *= HOUR_FACTORS.get(hour, 1.0)

    # Ограничиваем вероятность от 0 до 1
    return min(prob, 0.95)


def generate_bookings(users, start_date, end_date, show_progress=True):
    """
    Генерирует бронирования за указанный период
    """
    bookings = []
    current_date = start_date

    total_days = (end_date - start_date).days + 1
    day_count = 0

    while current_date <= end_date:
        date_str = current_date.strftime("%d.%m.%Y")

        # Для каждой машины и каждого слота
        for machine in MACHINE_NUMBERS:
            for slot in TIME_SLOTS:
                hour = int(slot.split(':')[0])

                # Рассчитываем вероятность бронирования
                prob = generate_booking_probability(date_str, hour)

                # Решаем, будет ли бронь
                if random.random() < prob:
                    # Выбираем случайного пользователя
                    user = random.choice(users)
                    user_id, user_fio, user_phone = user

                    bookings.append({
                        'date': date_str,
                        'time_slot': slot,
                        'machine_number': machine,
                        'user_id': user_id,
                        'user_fio': user_fio,
                        'user_phone': user_phone
                    })

        day_count += 1
        if show_progress and day_count % 30 == 0:
            print(f"  Обработано {day_count}/{total_days} дней...")

        current_date += timedelta(days=1)

    return bookings


def save_bookings_to_file(bookings, filename):
    """Сохраняет бронирования в файл"""
    with open(filename, 'w', encoding='utf-8') as f:
        f.write("date|time_slot|machine_number|user_id|user_fio|user_phone\n")

        for booking in bookings:
            f.write(f"{booking['date']}|{booking['time_slot']}|{booking['machine_number']}|"
                    f"{booking['user_id']}|{booking['user_fio']}|{booking['user_phone']}\n")

    print(f"\n📁 Файл сохранён: {filename}")


def load_bookings_to_db(filename):
    """
    Загружает бронирования из файла в таблицу booking
    """
    print("\n" + "=" * 70)
    print("ЗАГРУЗКА БРОНИРОВАНИЙ В БАЗУ ДАННЫХ")
    print("=" * 70)

    if not os.path.exists(filename):
        print(f"\n❌ Ошибка: Файл {filename} не найден!")
        return False

    # Подключаемся к БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем структуру таблицы booking
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='booking'
    """)

    if not cursor.fetchone():
        print("\n❌ Таблица booking не существует!")
        print("Сначала запустите приложение, чтобы создать таблицы")
        conn.close()
        return False

    # Получаем существующие бронирования для проверки дубликатов
    cursor.execute("SELECT date, time_slot, machine_number FROM booking")
    existing = set(cursor.fetchall())

    print(f"\n📊 Существующих бронирований в БД: {len(existing)}")

    # Читаем файл
    with open(filename, 'r', encoding='utf-8') as f:
        # Пропускаем заголовок
        next(f)

        lines = f.readlines()
        print(f"📄 Записей в файле: {len(lines)}")

        added = 0
        skipped = 0
        errors = 0

        print("\n⏳ Начинаю загрузку...")

        for i, line in enumerate(lines, 1):
            try:
                parts = line.strip().split('|')
                if len(parts) != 6:
                    errors += 1
                    continue

                date_str, time_slot, machine_str, user_id_str, user_fio, user_phone = parts

                machine_number = int(machine_str)
                user_id = int(user_id_str)

                # Проверяем, существует ли уже такое бронирование
                key = (date_str, time_slot, machine_number)
                if key in existing:
                    skipped += 1
                    continue

                # Вставляем бронирование
                cursor.execute("""
                    INSERT INTO booking 
                    (user_id, date, time_slot, machine_number, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    user_id,
                    date_str,
                    time_slot,
                    machine_number,
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                ))

                added += 1
                existing.add(key)  # добавляем в множество, чтобы избежать дубликатов в рамках одной загрузки

                # Показываем прогресс каждые 500 записей
                if added % 500 == 0:
                    print(f"  Загружено {added} записей...")

            except Exception as e:
                errors += 1
                if errors <= 5:  # показываем только первые 5 ошибок
                    print(f"  Ошибка в строке {i}: {e}")

        conn.commit()

    print(f"\n✅ Загрузка завершена!")
    print(f"  • Добавлено: {added}")
    print(f"  • Пропущено (дубликаты): {skipped}")
    print(f"  • Ошибок: {errors}")

    # Проверка итогового количества
    cursor.execute("SELECT COUNT(*) FROM booking")
    total = cursor.fetchone()[0]
    print(f"\n📊 Всего бронирований в БД: {total}")

    conn.close()
    return True


def clear_bookings_table():
    """Очищает таблицу бронирований"""
    print("\n" + "=" * 70)
    print("ОЧИСТКА ТАБЛИЦЫ БРОНИРОВАНИЙ")
    print("=" * 70)

    confirm = input("\n⚠️  Вы уверены? Все бронирования будут удалены! (да/нет): ").strip().lower()

    if confirm not in ['да', 'yes', 'y', 'д']:
        print("❌ Операция отменена")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Получаем количество до очистки
    cursor.execute("SELECT COUNT(*) FROM booking")
    before = cursor.fetchone()[0]

    # Очищаем таблицу
    cursor.execute("DELETE FROM booking")
    conn.commit()

    print(f"\n✅ Удалено записей: {before}")
    print("Таблица бронирований очищена")

    conn.close()

    input("\nНажмите Enter для продолжения...")


def calculate_statistics(bookings):
    """Рассчитывает статистику по сгенерированным бронированиям"""
    total_slots = len(MACHINE_NUMBERS) * len(TIME_SLOTS)

    # Группировка по месяцам
    monthly_stats = {}
    for booking in bookings:
        month = int(booking['date'].split('.')[1])
        monthly_stats[month] = monthly_stats.get(month, 0) + 1

    # Группировка по часам
    hourly_stats = {}
    for booking in bookings:
        hour = int(booking['time_slot'].split(':')[0])
        hourly_stats[hour] = hourly_stats.get(hour, 0) + 1

    # Группировка по машинам
    machine_stats = {}
    for booking in bookings:
        machine = booking['machine_number']
        machine_stats[machine] = machine_stats.get(machine, 0) + 1

    return {
        'total': len(bookings),
        'by_month': monthly_stats,
        'by_hour': hourly_stats,
        'by_machine': machine_stats
    }


def print_statistics(stats, total_days):
    """Печатает статистику в красивом виде"""
    total_slots_per_day = len(MACHINE_NUMBERS) * len(TIME_SLOTS)
    total_possible = total_days * total_slots_per_day

    print("\n" + "=" * 70)
    print("СТАТИСТИКА СГЕНЕРИРОВАННЫХ БРОНИРОВАНИЙ")
    print("=" * 70)

    print(f"\n📊 ОБЩАЯ СТАТИСТИКА:")
    print(f"  • Всего бронирований: {stats['total']}")
    print(f"  • Всего возможных слотов: {total_possible}")
    print(f"  • Средняя загрузка: {stats['total'] / total_possible * 100:.1f}%")

    print(f"\n📅 ПО МЕСЯЦАМ:")
    months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
              "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]

    for month_num, month_name in enumerate(months, 1):
        if month_num in stats['by_month']:
            count = stats['by_month'][month_num]
            days_in_month = (date(2025, month_num % 12 + 1, 1) - date(2025, month_num, 1)).days
            slots_in_month = days_in_month * total_slots_per_day
            load = count / slots_in_month * 100
            bar = "█" * int(load / 5) + "░" * (20 - int(load / 5))
            print(f"  {month_name:10} | {bar} | {load:5.1f}% ({count:4d} броней)")

    print(f"\n🕐 ПО ЧАСАМ:")
    for hour in [9, 11, 13, 15, 17, 19]:
        if hour in stats['by_hour']:
            count = stats['by_hour'][hour]
            slot_name = f"{hour:02d}:00-{hour + 2}:00"
            percentage = count / stats['total'] * 100
            bar = "█" * int(percentage / 2) + "░" * (50 - int(percentage / 2))
            print(f"  {slot_name:13} | {bar} | {percentage:5.1f}%")

    print(f"\n🔄 ПО МАШИНАМ:")
    for machine in MACHINE_NUMBERS:
        if machine in stats['by_machine']:
            count = stats['by_machine'][machine]
            percentage = count / stats['total'] * 100
            print(f"  Машина {machine}: {count} броней ({percentage:.1f}%)")


def generate_full_year(users):
    """Генерирует бронирования за весь 2025 год"""
    clear_screen()
    print_header("ГЕНЕРАЦИЯ БРОНИРОВАНИЙ ЗА 2025 ГОД")

    start_date = date(2025, 1, 1)
    end_date = date(2025, 12, 31)
    total_days = 365

    print(f"\n📅 Период: с 01.01.2025 по 31.12.2025")
    print(f"📊 Всего дней: {total_days}")
    print(f"👥 Пользователей: {len(users)}")
    print(f"\n⏳ Начинаю генерацию...\n")

    bookings = generate_bookings(users, start_date, end_date)

    # Сохраняем в файл
    save_bookings_to_file(bookings, OUTPUT_FILE)

    print(f"\n✅ Генерация завершена!")

    # Спрашиваем, загрузить ли сразу в БД
    load_now = input("\n📥 Загрузить бронирования в базу данных? (да/нет): ").strip().lower()
    if load_now in ['да', 'yes', 'y', 'д']:
        load_bookings_to_db(OUTPUT_FILE)

    # Статистика
    stats = calculate_statistics(bookings)
    print_statistics(stats, total_days)

    input("\n\nНажмите Enter для продолжения...")


def generate_by_month(users):
    """Генерирует бронирования за конкретный месяц"""
    clear_screen()
    print_header("ГЕНЕРАЦИЯ БРОНИРОВАНИЙ ЗА МЕСЯЦ")

    months = {
        "1": ("Январь", 1), "2": ("Февраль", 2), "3": ("Март", 3),
        "4": ("Апрель", 4), "5": ("Май", 5), "6": ("Июнь", 6),
        "7": ("Июль", 7), "8": ("Август", 8), "9": ("Сентябрь", 9),
        "10": ("Октябрь", 10), "11": ("Ноябрь", 11), "12": ("Декабрь", 12)
    }

    print("\nВыберите месяц:")
    for key, (name, num) in months.items():
        print(f"  {key}. {name}")
    print("  0. Назад")

    choice = input("\nВаш выбор: ").strip()

    if choice == "0":
        return

    if choice in months:
        month_name, month_num = months[choice]

        # Определяем первый и последний день месяца
        start_date = date(2025, month_num, 1)
        if month_num == 12:
            end_date = date(2025, 12, 31)
        else:
            end_date = date(2025, month_num + 1, 1) - timedelta(days=1)

        total_days = (end_date - start_date).days + 1

        print(f"\n📅 Месяц: {month_name} 2025")
        print(f"📊 Дней в месяце: {total_days}")
        print(f"👥 Пользователей: {len(users)}")
        print(f"\n⏳ Начинаю генерацию...\n")

        filename = f"test_bookings_{month_name.lower()}_2025.txt"
        bookings = generate_bookings(users, start_date, end_date)
        save_bookings_to_file(bookings, filename)

        print(f"\n✅ Генерация завершена!")

        # Спрашиваем, загрузить ли сразу в БД
        load_now = input("\n📥 Загрузить бронирования в базу данных? (да/нет): ").strip().lower()
        if load_now in ['да', 'yes', 'y', 'д']:
            load_bookings_to_db(filename)

        stats = calculate_statistics(bookings)
        print_statistics(stats, total_days)

        input("\n\nНажмите Enter для продолжения...")


def generate_by_period(users):
    """Генерирует бронирования за произвольный период"""
    clear_screen()
    print_header("ГЕНЕРАЦИЯ БРОНИРОВАНИЙ ЗА ПЕРИОД")

    print("\nВведите даты в формате ДД.ММ.ГГГГ")
    print("Например: 01.06.2025")

    try:
        start_str = input("\nНачальная дата: ").strip()
        end_str = input("Конечная дата: ").strip()

        start_date = datetime.strptime(start_str, "%d.%m.%Y").date()
        end_date = datetime.strptime(end_str, "%d.%m.%Y").date()

        if start_date > end_date:
            print("\n❌ Ошибка: начальная дата больше конечной!")
            input("\nНажмите Enter...")
            return

        #if start_date.year != 2025 or end_date.year != 2025:
        #    print("\n❌ Ошибка: даты должны быть в 2025 году!")
        #    input("\nНажмите Enter...")
        #    return

        total_days = (end_date - start_date).days + 1

        print(f"\n📅 Период: с {start_str} по {end_str}")
        print(f"📊 Всего дней: {total_days}")
        print(f"👥 Пользователей: {len(users)}")
        print(f"\n⏳ Начинаю генерацию...\n")

        filename = f"test_bookings_{start_str}_{end_str}.txt".replace('.', '-')
        bookings = generate_bookings(users, start_date, end_date)
        save_bookings_to_file(bookings, filename)

        print(f"\n✅ Генерация завершена!")

        # Спрашиваем, загрузить ли сразу в БД
        load_now = input("\n📥 Загрузить бронирования в базу данных? (да/нет): ").strip().lower()
        if load_now in ['да', 'yes', 'y', 'д']:
            load_bookings_to_db(filename)

        stats = calculate_statistics(bookings)
        print_statistics(stats, total_days)

    except ValueError:
        print("\n❌ Ошибка: неверный формат даты!")

    input("\n\nНажмите Enter для продолжения...")


def load_bookings_menu():
    """Меню загрузки бронирований из файла"""
    clear_screen()
    print_header("ЗАГРУЗКА БРОНИРОВАНИЙ ИЗ ФАЙЛА")

    # Показываем доступные txt файлы
    txt_files = [f for f in os.listdir('.') if f.startswith('test_bookings') and f.endswith('.txt')]

    if not txt_files:
        print("\n❌ Нет файлов с бронированиями!")
        print("Сначала сгенерируйте бронирования (пункты 1-3)")
        input("\nНажмите Enter...")
        return

    print("\n📄 Доступные файлы:")
    for i, file in enumerate(txt_files, 1):
        size = os.path.getsize(file) / 1024  # размер в КБ
        print(f"  {i}. {file} ({size:.1f} КБ)")

    print("\n0. Назад")

    try:
        choice = input("\nВыберите файл для загрузки: ").strip()

        if choice == "0":
            return

        idx = int(choice) - 1
        if 0 <= idx < len(txt_files):
            filename = txt_files[idx]
            load_bookings_to_db(filename)
        else:
            print("\n❌ Неверный выбор!")

    except ValueError:
        print("\n❌ Неверный ввод!")

    input("\nНажмите Enter для продолжения...")


def main():
    """Главная функция"""
    while True:
        clear_screen()
        print_header("ГЕНЕРАТОР ТЕСТОВЫХ БРОНИРОВАНИЙ ДЛЯ ПРАЧЕЧНОЙ")

        # Получаем пользователей из БД
        users = get_users_from_db()

        if users:
            show_users_stats(users)
            print_menu()

            choice = input("\nВаш выбор: ").strip()

            if choice == "1":
                generate_full_year(users)
            elif choice == "2":
                generate_by_month(users)
            elif choice == "3":
                generate_by_period(users)
            elif choice == "4":
                load_bookings_menu()
            elif choice == "5":
                clear_screen()
                print_header("СТАТИСТИКА ПОЛЬЗОВАТЕЛЕЙ")
                show_users_stats(users)
                input("\nНажмите Enter для продолжения...")
            elif choice == "6":
                clear_bookings_table()
            elif choice == "7":
                print("\n👋 До свидания!")
                break
            else:
                print("\n❌ Неверный выбор!")
                input("Нажмите Enter...")
        else:
            print("\n❌ Не удалось загрузить пользователей!")
            print("\n1. Попробовать снова")
            print("2. Выйти")

            choice = input("\nВаш выбор: ").strip()
            if choice == "2":
                break
            input("Нажмите Enter...")


if __name__ == "__main__":
    main()