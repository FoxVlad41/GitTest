import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlmodel import Session, select, func
import logging

from models.analytics import AnalyticsData
from models.discount import Discount
from models.bookings import Booking

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
TIME_SLOTS = [
    "09:00-11:00", "11:00-13:00", "13:00-15:00",
    "15:00-17:00", "17:00-19:00", "19:00-21:00"
]

MACHINE_NUMBERS = [1, 2, 3]


class SimpleForecast:
    """
    Сервис прогнозирования на основе исторических данных
    """

    def __init__(self, session: Session):
        self.session = session

    def get_historical_data(self, target_date: str) -> pd.DataFrame:
        """
        Получает исторические данные для анализа с учетом аналогичных дат
        """
        try:
            dt = datetime.strptime(target_date, "%d.%m.%Y")
        except ValueError:
            return pd.DataFrame()

        # Берем данные за все время (не только последние 90 дней)
        all_data = self.session.exec(select(AnalyticsData)).all()

        if not all_data:
            return pd.DataFrame()

        # Преобразуем в DataFrame
        data = []
        for r in all_data:
            data.append({
                'datetime': r.slot_datetime,
                'date': r.booking_date,
                'time_slot': r.booking_time_slot,
                'machine': r.booking_machine_number,
                'was_booked': 1 if r.was_booked else 0,
                'day_of_week': r.day_of_week,
                'hour': r.hour_start,
                'month': r.month,
                'day': int(r.booking_date.split('.')[0])  # число месяца
            })

        df = pd.DataFrame(data)

        # Добавляем информацию о том, была ли дата праздничной
        # (можно расширить позже)

        return df

    def calculate_slot_statistics(self, df: pd.DataFrame) -> Dict:
        """
        Рассчитывает реальную статистику по каждому слоту
        """
        if df.empty:
            return {}

        stats = {}

        for slot in TIME_SLOTS:
            slot_data = df[df['time_slot'] == slot]

            if len(slot_data) > 0:
                # Общее количество слотов (учитываем, что на каждую дату было 3 машины)
                unique_dates = slot_data['date'].nunique()
                total_possible = unique_dates * len(MACHINE_NUMBERS)

                # Фактическое количество бронирований
                actual_bookings = slot_data['was_booked'].sum()

                # Процент загрузки
                if total_possible > 0:
                    load_percent = (actual_bookings / total_possible) * 100
                else:
                    load_percent = 0

                stats[slot] = {
                    'avg_load': round(load_percent, 1),
                    'total_bookings': int(actual_bookings),
                    'total_possible': total_possible,
                    'unique_dates': unique_dates,
                    'bookings_per_day': round(actual_bookings / unique_dates, 2) if unique_dates > 0 else 0
                }
            else:
                stats[slot] = {
                    'avg_load': 0,
                    'total_bookings': 0,
                    'total_possible': 0,
                    'unique_dates': 0,
                    'bookings_per_day': 0
                }

        return stats

    def get_similar_dates_data(self, target_date: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Получает данные за аналогичные даты (тот же месяц и день недели)
        """
        try:
            dt = datetime.strptime(target_date, "%d.%m.%Y")
        except ValueError:
            return pd.DataFrame()

        target_month = dt.month
        target_day = dt.day
        target_weekday = dt.weekday()

        # Ищем даты с тем же месяцем и днем недели (или близким числом)
        similar_data = df[
            (df['month'] == target_month) &
            (df['day_of_week'] == target_weekday)
            ]

        # Если данных мало, расширяем поиск на соседние месяцы
        if len(similar_data) < 10:
            # Добавляем предыдущий и следующий месяц
            prev_month = target_month - 1 if target_month > 1 else 12
            next_month = target_month + 1 if target_month < 12 else 1

            similar_data = df[
                ((df['month'] == target_month) |
                 (df['month'] == prev_month) |
                 (df['month'] == next_month)) &
                (df['day_of_week'] == target_weekday)
                ]

        return similar_data

    def predict_date(self, target_date: str) -> Dict:
        """
        Прогноз для конкретной даты на основе реальной статистики
        """
        logger.info(f"Прогноз для даты: {target_date}")

        # Получаем все исторические данные
        df = self.get_historical_data(target_date)

        #if df.empty:
        #   return self._get_default_prediction(target_date, "Нет исторических данных")

        # Рассчитываем общую статистику по слотам
        slot_stats = self.calculate_slot_statistics(df)

        # Получаем данные за аналогичные даты
        similar_df = self.get_similar_dates_data(target_date, df)

        # Рассчитываем статистику по аналогичным датам
        similar_stats = self.calculate_slot_statistics(similar_df) if not similar_df.empty else slot_stats

        try:
            dt = datetime.strptime(target_date, "%d.%m.%Y")
        except ValueError:
            return {"error": "Неверный формат даты"}

        day_of_week = dt.weekday()
        is_weekend = day_of_week >= 5

        # Коэффициент выходного дня (из реальных данных)
        weekend_factor = self._calculate_weekend_factor(df)

        # Прогноз для каждого слота
        slots = []
        total_predicted = 0

        for slot in TIME_SLOTS:
            # Используем статистику по аналогичным датам как основу
            if slot in similar_stats and similar_stats[slot]['total_possible'] > 0:
                base_occupancy = similar_stats[slot]['avg_load']
                base_bookings = similar_stats[slot]['bookings_per_day']
            elif slot in slot_stats and slot_stats[slot]['total_possible'] > 0:
                # Если нет аналогичных, используем общую статистику
                base_occupancy = slot_stats[slot]['avg_load']
                base_bookings = slot_stats[slot]['bookings_per_day']
            else:
                base_occupancy = 30  # значение по умолчанию
                base_bookings = 0.9  # ~30% от 3 машин

            # Корректируем на выходной день
            if is_weekend:
                base_occupancy *= weekend_factor
                base_bookings *= weekend_factor

            # Ограничиваем значения
            base_occupancy = min(base_occupancy, 100)
            base_bookings = min(base_bookings, 3)

            # Прогнозируемое количество броней
            predicted_bookings = round(base_bookings, 2)

            slots.append({
                "time_slot": slot,
                "hour": int(slot.split(':')[0]),
                "predicted_bookings": predicted_bookings,
                "occupancy_percent": round(base_occupancy, 1),
                "load_level": self._get_load_level(base_occupancy),
                "based_on": "аналогичные даты" if slot in similar_stats else "общая статистика"
            })

            total_predicted += predicted_bookings

        # Добавляем информацию о реальных данных за 09.03.2025, если они есть
        historical_note = ""
        march_9_data = df[df['date'] == "09.03.2025"]
        if not march_9_data.empty:
            actual_9_mar = march_9_data['was_booked'].sum()
            historical_note = f"09.03.2025: {actual_9_mar} бронирований"

        return {
            "date": target_date,
            "day_of_week": self._get_day_name(day_of_week),
            "total_predicted": round(total_predicted, 2),
            "slots": slots,
            "statistics_used": {
                "total_days_in_history": df['date'].nunique() if not df.empty else 0,
                "similar_days_used": similar_df['date'].nunique() if not similar_df.empty else 0,
                "weekend_factor": round(weekend_factor, 2),
                "historical_note": historical_note
            }
        }

    def _calculate_weekend_factor(self, df: pd.DataFrame) -> float:
        """
        Рассчитывает коэффициент выходного дня на основе реальных данных
        """
        if df.empty:
            return 1.4  # значение по умолчанию

        weekend_data = df[df['day_of_week'] >= 5]
        weekday_data = df[df['day_of_week'] < 5]

        if len(weekend_data) == 0 or len(weekday_data) == 0:
            return 1.4

        weekend_avg = weekend_data['was_booked'].mean()
        weekday_avg = weekday_data['was_booked'].mean()

        if weekday_avg == 0:
            return 1.4

        return weekend_avg / weekday_avg

    def apply_discounts_from_prediction(self, target_date: str) -> Dict:
        """
        Создает скидки на основе прогноза для указанной даты
        """
        # Получаем прогноз
        prediction = self.predict_date(target_date)

        if "error" in prediction:
            return prediction

        # Удаляем старые скидки на эту дату
        old_discounts = self.session.exec(
            select(Discount).where(Discount.date == target_date)
        ).all()

        for d in old_discounts:
            self.session.delete(d)

        # Создаем новые скидки
        discounts_created = []

        for slot in prediction["slots"]:
            occupancy = slot["occupancy_percent"]

            # Определяем размер скидки в зависимости от загрузки
            if occupancy < 30:
                discount = 30
            elif occupancy < 50:
                discount = 15
            elif occupancy < 70:
                discount = 5
            else:
                discount = 0  # нет скидки при высокой загрузке

            if discount > 0:
                new_discount = Discount(
                    date=target_date,
                    time_slot=slot["time_slot"],
                    machine_number=None,  # на все машины
                    discount_percent=discount,
                    predicted_load=occupancy,
                    is_active=True
                )
                self.session.add(new_discount)
                discounts_created.append({
                    "time_slot": slot["time_slot"],
                    "discount": discount,
                    "occupancy": occupancy,
                    "based_on": slot.get("based_on", "прогноз")
                })

        self.session.commit()

        return {
            "message": f"Скидки для {target_date} созданы на основе прогноза",
            "date": target_date,
            "discounts_created": discounts_created,
            "total_slots": len(prediction["slots"]),
            "slots_with_discount": len(discounts_created),
            "prediction": prediction
        }

    def _get_load_level(self, occupancy: float) -> str:
        """Определяет уровень загрузки"""
        if occupancy >= 70:
            return "high"
        elif occupancy >= 40:
            return "medium"
        else:
            return "low"

    def _get_day_name(self, day_of_week: int) -> str:
        """Возвращает название дня недели"""
        days = ["понедельник", "вторник", "среда", "четверг",
                "пятница", "суббота", "воскресенье"]
        return days[day_of_week]

    def _get_default_prediction(self, target_date: str, reason: str) -> Dict:
        """Базовый прогноз при отсутствии истории"""
        try:
            dt = datetime.strptime(target_date, "%d.%m.%Y")
        except ValueError:
            return {"error": "Неверный формат даты"}

        day_of_week = dt.weekday()

        # Более реалистичные значения по умолчанию
        default_occupancies = {
            "09:00-11:00": 40,
            "11:00-13:00": 60,
            "13:00-15:00": 80,
            "15:00-17:00": 70,
            "17:00-19:00": 50,
            "19:00-21:00": 30
        }

        slots = []
        total_predicted = 0

        for slot, default_occ in default_occupancies.items():
            # Корректировка на выходной
            if day_of_week >= 5:  # выходной
                occupancy = default_occ * 1.3
            else:
                occupancy = default_occ

            occupancy = min(occupancy, 100)
            predicted_bookings = (occupancy / 100) * 3

            slots.append({
                "time_slot": slot,
                "hour": int(slot.split(':')[0]),
                "predicted_bookings": round(predicted_bookings, 2),
                "occupancy_percent": round(occupancy, 1),
                "load_level": self._get_load_level(occupancy),
                "based_on": "значения по умолчанию"
            })

            total_predicted += predicted_bookings

        return {
            "date": target_date,
            "day_of_week": self._get_day_name(day_of_week),
            "total_predicted": round(total_predicted, 2),
            "slots": slots,
            "note": f"Прогноз на основе умолчаний ({reason})"
        }