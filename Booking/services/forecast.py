import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlmodel import Session, select, func
import logging

from models.analytics import AnalyticsData
from models.discount import Discount

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
TIME_SLOTS = [
    "09:00-11:00", "11:00-13:00", "13:00-15:00",
    "15:00-17:00", "17:00-19:00", "19:00-21:00"
]

MACHINE_NUMBERS = [1, 2, 3]

# Коэффициенты для расчета прогноза (на основе анализа исторических данных)
WEIGHT_LAST_WEEK = 0.5      # вес прошлой недели
WEIGHT_LAST_MONTH = 0.3     # вес прошлого месяца
WEIGHT_SAME_DAY = 0.2       # вес аналогичных дней


class SimpleForecast:
    """
    Простой сервис прогнозирования без внешних библиотек
    Использует статистические методы на основе исторических данных
    """
    
    def __init__(self, session: Session):
        self.session = session
        
    def get_historical_data(self, days_back: int = 90) -> pd.DataFrame:
        """
        Получает исторические данные из таблицы аналитики
        """
        # Вычисляем дату, с которой берем данные
        start_date = datetime.now() - timedelta(days=days_back)
        
        # Получаем данные
        query = select(AnalyticsData).where(
            AnalyticsData.slot_datetime >= start_date
        )
        results = self.session.exec(query).all()
        
        if not results:
            return pd.DataFrame()
        
        # Преобразуем в DataFrame
        data = []
        for r in results:
            data.append({
                'datetime': r.slot_datetime,
                'date': r.booking_date,
                'time_slot': r.booking_time_slot,
                'machine': r.booking_machine_number,
                'was_booked': 1 if r.was_booked else 0,
                'day_of_week': r.day_of_week,
                'hour': r.hour_start
            })
        
        df = pd.DataFrame(data)
        return df
    
    def calculate_base_load(self, df: pd.DataFrame) -> Dict:
        """
        Рассчитывает базовую загрузку по слотам
        """
        if df.empty:
            return {}
        
        # Группируем по временным слотам
        slot_load = df.groupby('time_slot')['was_booked'].agg(['mean', 'count']).to_dict('index')
        
        # Преобразуем в проценты
        result = {}
        for slot, stats in slot_load.items():
            result[slot] = {
                'avg_load': round(stats['mean'] * 100, 1),
                'total_bookings': int(stats['count']),
                'max_possible': stats['count']  # для справки
            }
        
        return result
    
    def get_day_of_week_factor(self, day_of_week: int, df: pd.DataFrame) -> float:
        """
        Рассчитывает коэффициент для дня недели
        """
        if df.empty:
            return 1.0
        
        # Средняя загрузка по этому дню недели
        day_data = df[df['day_of_week'] == day_of_week]
        if len(day_data) == 0:
            return 1.0
        
        day_avg = day_data['was_booked'].mean()
        overall_avg = df['was_booked'].mean()
        
        if overall_avg == 0:
            return 1.0
        
        return day_avg / overall_avg
    
    def get_hour_factor(self, hour: int, df: pd.DataFrame) -> float:
        """
        Рассчитывает коэффициент для часа
        """
        if df.empty:
            return 1.0
        
        hour_data = df[df['hour'] == hour]
        if len(hour_data) == 0:
            return 1.0
        
        hour_avg = hour_data['was_booked'].mean()
        overall_avg = df['was_booked'].mean()
        
        if overall_avg == 0:
            return 1.0
        
        return hour_avg / overall_avg
    
    def get_recent_trend(self, days: int, df: pd.DataFrame) -> float:
        """
        Рассчитывает тренд за последние N дней
        """
        if df.empty:
            return 1.0
        
        # Последние дни
        last_date = df['datetime'].max()
        period_start = last_date - timedelta(days=days)
        
        recent = df[df['datetime'] >= period_start]
        older = df[df['datetime'] < period_start]
        
        if len(recent) == 0 or len(older) == 0:
            return 1.0
        
        recent_avg = recent['was_booked'].mean()
        older_avg = older['was_booked'].mean()
        
        if older_avg == 0:
            return 1.0
        
        return recent_avg / older_avg
    
    def predict_date(self, target_date: str) -> Dict:
        """
        Прогноз для конкретной даты
        """
        logger.info(f"Прогноз для даты: {target_date}")
        
        # Получаем исторические данные
        df = self.get_historical_data(days_back=90)
        
        if df.empty:
            # Если нет истории, возвращаем базовый прогноз
            return self._get_default_prediction(target_date)
        
        # Преобразуем целевую дату
        try:
            dt = datetime.strptime(target_date, "%d.%m.%Y")
        except ValueError:
            return {"error": "Неверный формат даты"}
        
        day_of_week = dt.weekday()
        
        # Рассчитываем коэффициенты
        day_factor = self.get_day_of_week_factor(day_of_week, df)
        recent_trend = self.get_recent_trend(days=14, df=df)
        
        # Базовая загрузка по слотам
        base_load = self.calculate_base_load(df)
        
        # Прогноз для каждого слота
        slots = []
        total_predicted = 0
        
        for slot in TIME_SLOTS:
            hour = int(slot.split(':')[0])
            hour_factor = self.get_hour_factor(hour, df)
            
            # Базовая вероятность для этого слота
            if slot in base_load:
                base_prob = base_load[slot]['avg_load'] / 100
            else:
                base_prob = 0.3  # значение по умолчанию
            
            # Комбинируем факторы
            predicted_prob = base_prob * day_factor * hour_factor * recent_trend
            
            # Ограничиваем вероятность
            predicted_prob = min(max(predicted_prob, 0.1), 0.9)
            
            # Прогнозируемое количество броней (максимум 3 машины)
            predicted_bookings = predicted_prob * len(MACHINE_NUMBERS)
            occupancy_percent = predicted_prob * 100
            
            slots.append({
                "time_slot": slot,
                "hour": hour,
                "predicted_bookings": round(predicted_bookings, 2),
                "occupancy_percent": round(occupancy_percent, 1),
                "load_level": self._get_load_level(occupancy_percent)
            })
            
            total_predicted += predicted_bookings
        
        return {
            "date": target_date,
            "day_of_week": self._get_day_name(day_of_week),
            "total_predicted": round(total_predicted, 2),
            "slots": slots,
            "factors_used": {
                "day_factor": round(day_factor, 2),
                "recent_trend": round(recent_trend, 2),
                "data_days": len(df) if not df.empty else 0
            }
        }
    
    def predict_period(self, start_date: str, days: int) -> Dict:
        """
        Прогноз на период (несколько дней)
        days: количество дней (7 - неделя, 30 - месяц)
        """
        try:
            dt = datetime.strptime(start_date, "%d.%m.%Y")
        except ValueError:
            return {"error": "Неверный формат даты"}
        
        predictions = []
        total_sum = 0
        
        for i in range(days):
            current_date = (dt + timedelta(days=i)).strftime("%d.%m.%Y")
            pred = self.predict_date(current_date)
            
            if "error" not in pred:
                predictions.append({
                    "date": current_date,
                    "total_predicted": pred["total_predicted"],
                    "day_of_week": pred["day_of_week"]
                })
                total_sum += pred["total_predicted"]
        
        period_name = "неделя" if days == 7 else "месяц"
        
        return {
            "period": period_name,
            "start_date": start_date,
            "end_date": (dt + timedelta(days=days-1)).strftime("%d.%m.%Y"),
            "days": days,
            "total_predicted": round(total_sum, 2),
            "avg_per_day": round(total_sum / days, 2),
            "predictions": predictions
        }
    
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
                    "occupancy": occupancy
                })
        
        self.session.commit()
        
        return {
            "message": f"Скидки для {target_date} созданы на основе прогноза",
            "date": target_date,
            "discounts_created": discounts_created,
            "total_slots": len(prediction["slots"]),
            "slots_with_discount": len(discounts_created)
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
    
    def _get_default_prediction(self, target_date: str) -> Dict:
        """Базовый прогноз при отсутствии истории"""
        dt = datetime.strptime(target_date, "%d.%m.%Y")
        day_of_week = dt.weekday()
        
        # Коэффициент для выходных
        weekend_factor = 1.4 if day_of_week >= 5 else 1.0
        
        slots = []
        for slot in TIME_SLOTS:
            hour = int(slot.split(':')[0])
            
            # Базовая вероятность по часам
            if hour == 13:
                base = 0.8
            elif hour in [11, 15]:
                base = 0.6
            elif hour == 9:
                base = 0.4
            else:  # 17, 19
                base = 0.3
            
            prob = base * weekend_factor
            slots.append({
                "time_slot": slot,
                "hour": hour,
                "predicted_bookings": round(prob * 3, 2),
                "occupancy_percent": round(prob * 100, 1),
                "load_level": self._get_load_level(prob * 100)
            })
        
        return {
            "date": target_date,
            "day_of_week": self._get_day_name(day_of_week),
            "total_predicted": sum(s["predicted_bookings"] for s in slots),
            "slots": slots,
            "note": "Прогноз на основе умолчаний (нет исторических данных)"
        }