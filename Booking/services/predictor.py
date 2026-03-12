import pandas as pd
import numpy as np
from prophet import Prophet
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from sqlmodel import Session, select
import logging
import pickle
import os

from models.analytics import AnalyticsData
from models.discount import Discount

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TIME_SLOTS = [
    "09:00-11:00", "11:00-13:00", "13:00-15:00",
    "15:00-17:00", "17:00-19:00", "19:00-21:00"
]

MACHINE_NUMBERS = [1, 2, 3]
MODEL_PATH = "models/prophet_model.pkl"


class ProphetPredictor:
    """Прогнозирование с использованием Facebook Prophet"""

    def __init__(self, session: Session):
        self.session = session
        self.model = None
        self.holidays = self._create_holidays()

    def _create_holidays(self):
        """Создает DataFrame с праздничными днями"""
        holidays_dates = [
            "2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05",
            "2025-01-06", "2025-01-07", "2025-01-08",  # Новогодние
            "2025-02-23",  # День защитника Отечества
            "2025-03-08",  # Международный женский день
            "2025-05-01", "2025-05-02",  # Праздник весны и труда
            "2025-05-09", "2025-05-10",  # День Победы
            "2025-06-12",  # День России
            "2025-11-04",  # День народного единства
        ]

        holidays_df = pd.DataFrame({
            'ds': pd.to_datetime(holidays_dates),
            'holiday': 'russian_holidays',
            'lower_window': 0,
            'upper_window': 1,
        })
        return holidays_df

    def prepare_data(self) -> pd.DataFrame:
        """
        Подготавливает данные из БД для Prophet
        Возвращает DataFrame с колонками ds (datetime) и y (количество бронирований)
        """
        # Получаем все данные из аналитики
        analytics_data = self.session.exec(select(AnalyticsData)).all()

        if not analytics_data:
            return pd.DataFrame()

        # Преобразуем в список словарей
        data = []
        for a in analytics_data:
            data.append({
                'ds': a.slot_datetime,
                'y': 1 if a.was_booked else 0
            })

        df = pd.DataFrame(data)

        # Группируем по часам (суммируем количество бронирований в час)
        df = df.groupby('ds').agg({'y': 'sum'}).reset_index()

        # Сортируем по времени
        df = df.sort_values('ds')

        # Заполняем пропущенные часы нулями
        if not df.empty:
            full_range = pd.date_range(
                start=df['ds'].min(),
                end=df['ds'].max(),
                freq='H'
            )
            df = df.set_index('ds').reindex(full_range, fill_value=0).reset_index()
            df.columns = ['ds', 'y']

        logger.info(f"Подготовлено {len(df)} записей для обучения")
        return df

    def train(self, force_retrain: bool = False):
        """
        Обучает модель Prophet на исторических данных
        """
        # Проверяем, есть ли уже сохраненная модель
        if not force_retrain and os.path.exists(MODEL_PATH):
            logger.info("Загрузка сохраненной модели")
            with open(MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
            return self.model

        # Получаем данные
        df = self.prepare_data()

        if df.empty:
            raise ValueError("Нет данных для обучения модели")

        logger.info(f"Обучение модели на {len(df)} точках данных")

        # Создаем модель Prophet
        self.model = Prophet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=True,
            holidays=self.holidays,
            seasonality_mode='multiplicative',
            changepoint_prior_scale=0.05,
            seasonality_prior_scale=10.0,
            holidays_prior_scale=10.0,
        )

        # Добавляем специальные сезонности
        self.model.add_seasonality(
            name='monthly',
            period=30.5,
            fourier_order=5
        )

        # Обучаем
        self.model.fit(df)

        # Сохраняем модель
        os.makedirs('models', exist_ok=True)
        with open(MODEL_PATH, 'wb') as f:
            pickle.dump(self.model, f)

        logger.info("Модель успешно обучена и сохранена")
        return self.model

    def load_model(self):
        """Загружает сохраненную модель"""
        if os.path.exists(MODEL_PATH):
            with open(MODEL_PATH, 'rb') as f:
                self.model = pickle.load(f)
            return True
        return False

    def predict_date(self, target_date: str) -> Dict:
        """
        Прогноз для конкретной даты с fallback на статистические средние
        """
        try:
            dt = datetime.strptime(target_date, "%d.%m.%Y")
        except ValueError:
            return {"error": "Неверный формат даты"}

        # Загружаем модель, если не загружена
        if not self.model:
            if not self.load_model():
                logger.warning("Модель не загружена, использую fallback prediction")
                return self._fallback_prediction(target_date)

        try:
            # Создаем DataFrame с часами для целевой даты
            future = pd.DataFrame({
                'ds': pd.date_range(start=dt, end=dt + timedelta(days=1), freq='H')[:-1]
            })

            # Делаем прогноз
            forecast = self.model.predict(future)

            # Проверяем, не нулевой ли прогноз
            total_predicted_raw = forecast['yhat'].sum()

            # Если прогноз очень маленький или нулевой, используем fallback
            if total_predicted_raw < 0.1:
                logger.info(f"Прогноз для {target_date} близок к нулю ({total_predicted_raw:.2f}), использую fallback")
                return self._fallback_prediction(target_date)

            # Формируем результат из прогноза Prophet
            slots = []
            total_predicted = 0

            # Группируем по слотам
            slots_by_time = {}

            for _, row in forecast.iterrows():
                hour = row['ds'].hour

                # Определяем слот по часу
                if 9 <= hour < 11:
                    slot = "09:00-11:00"
                elif 11 <= hour < 13:
                    slot = "11:00-13:00"
                elif 13 <= hour < 15:
                    slot = "13:00-15:00"
                elif 15 <= hour < 17:
                    slot = "15:00-17:00"
                elif 17 <= hour < 19:
                    slot = "17:00-19:00"
                elif 19 <= hour < 21:
                    slot = "19:00-21:00"
                else:
                    continue

                predicted = max(0, row['yhat'])

                if slot not in slots_by_time:
                    slots_by_time[slot] = {
                        "count": 0,
                        "predicted_sum": 0,
                        "lower_sum": 0,
                        "upper_sum": 0
                    }

                slots_by_time[slot]["count"] += 1
                slots_by_time[slot]["predicted_sum"] += predicted
                slots_by_time[slot]["lower_sum"] += max(0, row['yhat_lower'])
                slots_by_time[slot]["upper_sum"] += max(0, row['yhat_upper'])
                total_predicted += predicted

            # Усредняем по слотам
            for slot_name, values in slots_by_time.items():
                avg_predicted = values["predicted_sum"] / values["count"]
                occupancy_percent = (avg_predicted / len(MACHINE_NUMBERS)) * 100

                slots.append({
                    "time_slot": slot_name,
                    "hour": int(slot_name.split(':')[0]),
                    "predicted_bookings": round(avg_predicted, 2),
                    "occupancy_percent": round(occupancy_percent, 1),
                    "load_level": self._get_load_level(occupancy_percent),
                    "lower_bound": round(values["lower_sum"] / values["count"], 2),
                    "upper_bound": round(min(3, values["upper_sum"] / values["count"]), 2)
                })

            # Сортируем по часу
            slots.sort(key=lambda x: x["hour"])

            return {
                "date": target_date,
                "day_of_week": self._get_day_name(dt.weekday()),
                "total_predicted": round(total_predicted, 2),
                "slots": slots,
                "model_info": {
                    "type": "Prophet with fallback",
                    "used_fallback": False,
                    "seasonalities": ["yearly", "weekly", "daily", "monthly"]
                }
            }

        except Exception as e:
            logger.error(f"Ошибка при прогнозе Prophet: {e}, использую fallback")
            return self._fallback_prediction(target_date)

    def _fallback_prediction(self, target_date: str) -> Dict:
        """
        Запасной вариант прогноза на основе статистических средних
        Используется когда модель Prophet не уверена или нет данных
        """
        try:
            dt = datetime.strptime(target_date, "%d.%m.%Y")
        except ValueError:
            return {"error": "Неверный формат даты"}

        day_of_week = dt.weekday()
        month = dt.month

        # Получаем исторические данные для расчета средних
        df = self.prepare_data()

        if not df.empty:
            # Рассчитываем средние из реальных данных
            df['day_of_week'] = df['ds'].dt.weekday
            df['month'] = df['ds'].dt.month
            df['hour'] = df['ds'].dt.hour

            # Среднее по дню недели
            dow_avg = df.groupby('day_of_week')['y'].mean().to_dict()
            base_dow = dow_avg.get(day_of_week, 1.5)

            # Среднее по месяцу
            month_avg = df.groupby('month')['y'].mean().to_dict()
            month_factor = month_avg.get(month, 1.0) / df['y'].mean() if df['y'].mean() > 0 else 1.0

            # Среднее по часу
            hour_avg = df.groupby('hour')['y'].mean().to_dict()
        else:
            # Если нет истории, используем разумные значения по умолчанию
            base_dow = {
                0: 1.5,  # понедельник
                1: 1.5,  # вторник
                2: 1.5,  # среда
                3: 1.6,  # четверг
                4: 1.8,  # пятница
                5: 2.2,  # суббота
                6: 2.1,  # воскресенье
            }.get(day_of_week, 1.5)

            month_factor = {
                1: 1.2,  # январь (праздники)
                2: 1.0,  # февраль
                3: 1.1,  # март
                4: 1.0,  # апрель
                5: 1.1,  # май (праздники)
                6: 0.8,  # июнь (сессия?)
                7: 0.7,  # июль (каникулы)
                8: 0.7,  # август (каникулы)
                9: 1.2,  # сентябрь (начало учебы)
                10: 1.1,  # октябрь
                11: 1.0,  # ноябрь
                12: 1.3,  # декабрь (сессия)
            }.get(month, 1.0)

        # Коэффициенты для разных часов
        hour_factors = {
            9: 0.7,  # 09:00-11:00
            11: 1.0,  # 11:00-13:00
            13: 1.5,  # 13:00-15:00 (пик)
            15: 1.2,  # 15:00-17:00
            17: 0.8,  # 17:00-19:00
            19: 0.4,  # 19:00-21:00
        }

        # Базовое значение для расчёта
        base_value = base_dow * month_factor

        slots = []
        total_predicted = 0

        for slot in TIME_SLOTS:
            hour = int(slot.split(':')[0])
            hour_factor = hour_factors.get(hour, 0.5)

            # Прогноз для этого слота
            predicted = base_value * hour_factor

            # Если есть почасовая статистика, используем её
            if not df.empty and hour in hour_avg:
                historical_hour = hour_avg.get(hour, predicted)
                # Смешиваем с историческими данными (30% история, 70% модель)
                predicted = 0.3 * historical_hour + 0.7 * predicted

            # Ограничиваем разумными пределами
            predicted = min(max(predicted, 0.2), 2.5)

            occupancy_percent = (predicted / len(MACHINE_NUMBERS)) * 100

            slots.append({
                "time_slot": slot,
                "hour": hour,
                "predicted_bookings": round(predicted, 2),
                "occupancy_percent": round(occupancy_percent, 1),
                "load_level": self._get_load_level(occupancy_percent),
                "based_on": "статистическое среднее"
            })

            total_predicted += predicted

        return {
            "date": target_date,
            "day_of_week": self._get_day_name(day_of_week),
            "total_predicted": round(total_predicted, 2),
            "slots": slots,
            "model_info": {
                "type": "Statistical Fallback",
                "used_fallback": True,
                "data_available": not df.empty
            },
            "note": "Прогноз на основе статистических средних (Prophet не дал уверенного прогноза)"
        }

    def predict_period(self, start_date: str, days: int) -> Dict:
        """
        Прогноз на период (несколько дней) с поддержкой fallback
        """
        try:
            dt = datetime.strptime(start_date, "%d.%m.%Y")
        except ValueError:
            return {"error": "Неверный формат даты"}

        predictions = []
        total_sum = 0

        for i in range(days):
            current_date = (dt + timedelta(days=i)).strftime("%d.%m.%Y")
            # Используем predict_date, который уже содержит fallback
            pred = self.predict_date(current_date)

            if "error" not in pred:
                predictions.append({
                    "date": current_date,
                    "total_predicted": pred["total_predicted"],
                    "day_of_week": pred["day_of_week"],
                    "used_fallback": pred.get("model_info", {}).get("used_fallback", False)
                })
                total_sum += pred["total_predicted"]

        period_name = "неделя" if days == 7 else "месяц" if days == 30 else f"{days} дней"

        # Считаем, сколько дней использовали fallback
        fallback_days = sum(1 for p in predictions if p.get("used_fallback", False))

        return {
            "period": period_name,
            "start_date": start_date,
            "end_date": (dt + timedelta(days=days - 1)).strftime("%d.%m.%Y"),
            "days": days,
            "total_predicted": round(total_sum, 2),
            "avg_per_day": round(total_sum / days, 2) if days > 0 else 0,
            "predictions": predictions,
            "fallback_used": fallback_days,
            "prophet_used": days - fallback_days,
            "model_info": {
                "type": "Prophet with fallback",
                "fallback_percentage": round((fallback_days / days) * 100, 1) if days > 0 else 0
            }
        }

    def apply_discounts_from_prediction(self, target_date: str) -> Dict:
        """
        Создает скидки на основе прогноза (Prophet или fallback)
        """
        # Получаем прогноз (уже с fallback)
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
            if occupancy < 20:
                discount = 40
            elif occupancy < 30:
                discount = 30
            elif occupancy < 40:
                discount = 20
            elif occupancy < 50:
                discount = 10
            elif occupancy < 60:
                discount = 5
            else:
                discount = 0

            if discount > 0:
                new_discount = Discount(
                    date=target_date,
                    time_slot=slot["time_slot"],
                    machine_number=None,
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
            "slots_with_discount": len(discounts_created),
            "prediction": prediction,
            "used_fallback": prediction.get("model_info", {}).get("used_fallback", False)
        }

    def _get_load_level(self, occupancy: float) -> str:
        if occupancy >= 70:
            return "high"
        elif occupancy >= 40:
            return "medium"
        else:
            return "low"

    def _get_day_name(self, day_of_week: int) -> str:
        days = ["понедельник", "вторник", "среда", "четверг",
                "пятница", "суббота", "воскресенье"]
        return days[day_of_week]