#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Скрипт для генерации тестовых пользо2вателей
Заполняет таблицу user реалистичными данными
Телефоны генерируются уникальными
"""

import random
import sqlite3
import os
from datetime import datetime

DB_PATH = "booking.db"
OUTPUT_FILE = "test_users.txt"

# База данных для генерации имен
FIRST_NAMES_MALE = [
    "Александр", "Дмитрий", "Максим", "Сергей", "Андрей",
    "Алексей", "Артём", "Илья", "Кирилл", "Михаил",
    "Никита", "Матвей", "Роман", "Егор", "Арсений",
    "Денис", "Павел", "Тимофей", "Владислав", "Иван"
]

FIRST_NAMES_FEMALE = [
    "Анна", "Мария", "Елена", "Дарья", "Екатерина",
    "Ольга", "Татьяна", "Ирина", "Юлия", "Наталья",
    "Анастасия", "Виктория", "Полина", "Светлана", "Ксения",
    "Алиса", "Валерия", "Александра", "Евгения", "Вероника"
]

LAST_NAMES_MALE = [
    "Иванов", "Петров", "Сидоров", "Смирнов", "Кузнецов",
    "Попов", "Васильев", "Соколов", "Михайлов", "Новиков",
    "Федоров", "Морозов", "Волков", "Алексеев", "Лебедев",
    "Семенов", "Егоров", "Павлов", "Козлов", "Степанов"
]

LAST_NAMES_FEMALE = [
    "Иванова", "Петрова", "Сидорова", "Смирнова", "Кузнецова",
    "Попова", "Васильева", "Соколова", "Михайлова", "Новикова",
    "Федорова", "Морозова", "Волкова", "Алексеева", "Лебедева",
    "Семенова", "Егорова", "Павлова", "Козлова", "Степанова"
]

PATRONYMICS_MALE = [
    "Александрович", "Дмитриевич", "Максимович", "Сергеевич", "Андреевич",
    "Алексеевич", "Артёмович", "Ильич", "Кириллович", "Михайлович",
    "Никитич", "Матвеевич", "Романович", "Егорович", "Арсеньевич",
    "Денисович", "Павлович", "Тимофеевич", "Владиславович", "Иванович"
]

PATRONYMICS_FEMALE = [
    "Александровна", "Дмитриевна", "Максимовна", "Сергеевна", "Андреевна",
    "Алексеевна", "Артёмовна", "Ильинична", "Кирилловна", "Михайловна",
    "Никитична", "Матвеевна", "Романовна", "Егоровна", "Арсеньевна",
    "Денисовна", "Павловна", "Тимофеевна", "Владиславовна", "Ивановна"
]

# База для генерации паролей (простые пароли для тестов)
PASSWORDS = [
    "password123", "qwerty123", "12345678", "user1234", "pass1234",
    "student123", "laundry2025", "booking123", "machine123", "test1234"
]

# Коды операторов для генерации телефонов
PHONE_CODES = ["901", "902", "903", "904", "905", "906", "909", "912", 
               "913", "914", "915", "916", "917", "918", "919", "920"]


def generate_phone(existing_phones):
    """
    Генерирует уникальный телефон в формате +7XXXXXXXXXX
    """
    while True:
        # Формат: +7 9XX XXX-XX-XX
        code = random.choice(PHONE_CODES)
        number = f"{random.randint(1000000, 9999999):07d}"
        phone = f"+7{code}{number}"
        
        if phone not in existing_phones:
            return phone


def generate_full_name(gender=None):
    """
    Генерирует полное имя (ФИО)
    """
    if gender is None:
        gender = random.choice(["male", "female"])
    
    if gender == "male":
        first = random.choice(FIRST_NAMES_MALE)
        last = random.choice(LAST_NAMES_MALE)
        patron = random.choice(PATRONYMICS_MALE)
    else:
        first = random.choice(FIRST_NAMES_FEMALE)
        last = random.choice(LAST_NAMES_FEMALE)
        patron = random.choice(PATRONYMICS_FEMALE)
    
    return f"{last} {first} {patron}"


def get_existing_phones(cursor):
    """
    Получает список уже существующих телефонов из БД
    """
    cursor.execute("SELECT phone FROM user")
    return [row[0] for row in cursor.fetchall()]


def generate_users_file(num_users=50):
    """
    Генерирует файл с тестовыми пользователями
    """
    print("=" * 60)
    print("ГЕНЕРАТОР ТЕСТОВЫХ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 60)
    
    # Подключаемся к БД для проверки существующих телефонов
    if os.path.exists(DB_PATH):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        existing_phones = get_existing_phones(cursor)
        conn.close()
        print(f"Найдено существующих пользователей в БД: {len(existing_phones)}")
    else:
        existing_phones = []
        print("База данных не найдена, будет создана новая")
    
    # Генерируем пользователей
    users = []
    phones_used = set(existing_phones)
    
    for i in range(num_users):
        # Генерируем уникальный телефон
        phone = generate_phone(phones_used)
        phones_used.add(phone)
        
        # Генерируем ФИО
        fio = generate_full_name()
        
        # Выбираем случайный пароль
        password = random.choice(PASSWORDS)
        
        users.append({
            'fio': fio,
            'phone': phone,
            'password': password
        })
    
    # Сохраняем в файл
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        # Заголовок
        f.write("fio|phone|password\n")
        
        for user in users:
            f.write(f"{user['fio']}|{user['phone']}|{user['password']}\n")
    
    print(f"\nСгенерировано пользователей: {len(users)}")
    print(f"Файл сохранён: {OUTPUT_FILE}")
    
    # Статистика
    males = sum(1 for u in users if u['fio'].split()[1][-1] != 'а')
    females = len(users) - males
    
    print(f"Мужчин: {males}, Женщин: {females}")
    
    return users


def load_users_to_db():
    """
    Загружает пользователей из файла в базу данных
    """
    print("\n" + "=" * 60)
    print("ЗАГРУЗКА ПОЛЬЗОВАТЕЛЕЙ В БАЗУ ДАННЫХ")
    print("=" * 60)
    
    if not os.path.exists(OUTPUT_FILE):
        print(f"Ошибка: Файл {OUTPUT_FILE} не найден!")
        print("Сначала запустите generate_users.py для создания файла")
        return
    
    # Подключаемся к БД
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Получаем существующие телефоны
    existing_phones = get_existing_phones(cursor)
    print(f"Существующих пользователей в БД: {len(existing_phones)}")
    
    # Читаем файл
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        # Пропускаем заголовок
        next(f)
        
        lines = f.readlines()
        added = 0
        skipped = 0
        
        for line in lines:
            parts = line.strip().split('|')
            if len(parts) != 3:
                continue
            
            fio, phone, password = parts
            
            # Проверяем, нет ли уже такого телефона
            cursor.execute("SELECT id FROM user WHERE phone = ?", (phone,))
            if cursor.fetchone():
                print(f"  Пропущен (уже существует): {phone}")
                skipped += 1
                continue
            
            # Добавляем пользователя
            cursor.execute(
                "INSERT INTO user (fio, phone, password) VALUES (?, ?, ?)",
                (fio, phone, password)
            )
            added += 1
            
            if added % 10 == 0:
                print(f"  Добавлено {added} пользователей...")
        
        conn.commit()
    
    print(f"\nРезультат загрузки:")
    print(f"  Добавлено: {added}")
    print(f"  Пропущено (уже есть): {skipped}")
    
    # Проверка итогового количества
    cursor.execute("SELECT COUNT(*) FROM user")
    total = cursor.fetchone()[0]
    print(f"  Всего пользователей в БД: {total}")
    
    conn.close()


def show_sample_users():
    """
    Показывает примеры сгенерированных пользователей
    """
    if not os.path.exists(OUTPUT_FILE):
        return
    
    print("\n" + "=" * 60)
    print("ПРИМЕРЫ СГЕНЕРИРОВАННЫХ ПОЛЬЗОВАТЕЛЕЙ")
    print("=" * 60)
    
    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        next(f)  # пропускаем заголовок
        lines = f.readlines()
        
        # Показываем первые 10 пользователей
        for i, line in enumerate(lines[:10], 1):
            fio, phone, password = line.strip().split('|')
            print(f"{i}. {fio} | {phone} | пароль: {password}")


if __name__ == "__main__":
    import sys
    
    print("Выберите действие:")
    print("1 - Сгенерировать файл с пользователями")
    print("2 - Загрузить пользователей в БД")
    print("3 - Сделать всё (генерировать и загрузить)")
    print("4 - Показать примеры пользователей")
    
    choice = input("\nВаш выбор (1/2/3/4): ").strip()
    
    if choice == "1":
        num = input("Сколько пользователей сгенерировать? (по умолчанию 50): ").strip()
        num = int(num) if num.isdigit() else 50
        generate_users_file(num)
        show_sample_users()
    
    elif choice == "2":
        load_users_to_db()
    
    elif choice == "3":
        num = input("Сколько пользователей сгенерировать? (по умолчанию 50): ").strip()
        num = int(num) if num.isdigit() else 50
        generate_users_file(num)
        load_users_to_db()
        show_sample_users()
    
    elif choice == "4":
        show_sample_users()
    
    else:
        print("Неверный выбор")