import openai
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        # Настройки для AITUNNEL (работает в РФ)
        self.api_key = os.getenv("AITUNNEL_API_KEY", "sk-aitunnel-dAut1vwt4gXAHGjwqXJ621cvxLpJ1kJP")
        self.base_url = "https://api.aitunnel.ru/v1"
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                self.client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
                logger.info("✅ AITUNNEL клиент инициализирован")
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации AITUNNEL: {e}")
                self.enabled = False
    
    async def get_daily_tip(self, user_data: Dict, last_workouts: List[Dict]) -> Optional[str]:
        """Персональный совет на сегодня (на основе последних тренировок)"""
        if not self.enabled:
            return None
        
        try:
            name = user_data.get('first_name', 'Спортсмен')
            streak = user_data.get('current_streak', 0)
            
            # Анализируем последние тренировки
            recent_exercises = []
            if last_workouts:
                for w in last_workouts[:3]:
                    recent_exercises.append(f"{w.get('exercise_name')} - {w.get('sets')}×{w.get('reps')} ({w.get('weight', 'б/в')} кг)")
            
            exercises_text = "\n".join(recent_exercises) if recent_exiles else "нет данных"
            
            prompt = f"""Ты — профессиональный персональный тренер с 10-летним стажем. Твой клиент {name}.

ДАННЫЕ О КЛИЕНТЕ:
- Серия тренировок: {streak} дней
- Последние упражнения: 
{exercises_text}

ЗАДАЧА:
Дай ОДИН конкретный совет на сегодня, который поможет клиенту:
1. Прогрессировать в слабых местах (если видишь из последних тренировок)
2. Улучшить технику конкретного упражнения
3. Правильно построить сегодняшнюю тренировку

ТРЕБОВАНИЯ К ОТВЕТУ:
- Максимально конкретно (с цифрами, подходами, кг)
- Только один совет, но очень полезный
- Без воды и общих фраз
- Дружелюбно, но профессионально
- Если данных мало — дай универсальный совет по прогрессии нагрузок

ПРИМЕР ХОРОШЕГО ОТВЕТА:
"Судя по твоим последним тренировкам, в жиме лежа вес застрял на 80 кг. Попробуй сегодня сделать 5×5 с 75 кг, но взрывной темп и с паузой в 2 секунды на груди. Это улучшит технику и прорвет плато."

ОТВЕТЬ НА РУССКОМ ЯЗЫКЕ:"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты профессиональный персональный тренер. Твои советы всегда конкретны, с цифрами и реальными протоколами тренировок."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.8
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка AITUNNEL: {e}")
            return None
    
    async def get_workout_plan(self, user_data: Dict) -> Optional[str]:
        """Сгенерировать план тренировки под цель"""
        if not self.enabled:
            return None
        
        try:
            goal = user_data.get('goal', 'общая физическая подготовка')
            experience = user_data.get('experience', 'средний')
            available_time = user_data.get('time', '60 минут')
            equipment = user_data.get('equipment', 'тренажерный зал')
            
            # Определяем уровень
            level_text = "новичок" if experience == "beginner" else "средний" if experience == "intermediate" else "продвинутый"
            
            prompt = f"""Ты — профессиональный тренер по силовой подготовке. Составь план одной тренировки.

ПАРАМЕТРЫ:
- Уровень: {level_text}
- Цель: {goal}
- Время: {available_time}
- Инвентарь: {equipment}

ТРЕБОВАНИЯ К ПЛАНУ:
1. РАЗМИНКА (10 мин) — конкретные упражнения (суставная гимнастика, разогрев)
2. ОСНОВНАЯ ЧАСТЬ (40 мин) — 4-5 упражнений с указанием:
   - Название упражнения
   - Количество подходов и повторений
   - Рабочий вес (% от 1ПМ или RPE)
   - Отдых между подходами
3. ЗАМИНКА (10 мин) — растяжка целевых мышц

ВАЖНО:
- Учитывай цель (сила/масса/выносливость/рельеф)
- Для силы: 3-5 повторений, 80-90% от 1ПМ
- Для массы: 8-12 повторений, 70-80% от 1ПМ
- Для выносливости: 15-20 повторений, 50-60% от 1ПМ

ОТВЕТЬ НА РУССКОМ, СТРУКТУРИРОВАННО:"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты тренер высшей категории. Твои планы всегда учитывают цель, уровень и доступное время."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=800,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка AITUNNEL: {e}")
            return None
    
    async def analyze_progress(self, user_data: Dict, history: List[Dict]) -> Optional[str]:
        """Глубокий анализ прогресса с рекомендациями"""
        if not self.enabled:
            return None
        
        try:
            name = user_data.get('first_name', 'Спортсмен')
            
            # Анализируем прогресс по упражнениям
            exercises = {}
            for h in history:
                ex_name = h.get('exercise_name')
                if ex_name not in exercises:
                    exercises[ex_name] = []
                exercises[ex_name].append({
                    'date': h.get('date'),
                    'weight': h.get('weight', 0),
                    'sets': h.get('sets', 0),
                    'reps': h.get('reps', 0)
                })
            
            # Формируем статистику для анализа
            analysis_data = ""
            for ex_name, data in exercises.items():
                if len(data) >= 2:
                    first = data[0]
                    last = data[-1]
                    progress = last['weight'] - first['weight']
                    analysis_data += f"{ex_name}: {first['weight']} кг → {last['weight']} кг (прогресс {progress} кг)\n"
            
            prompt = f"""Ты — спортивный аналитик и тренер. Проанализируй прогресс {name}.

ДАННЫЕ ЗА ПОСЛЕДНИЙ ПЕРИОД:
{analysis_data if analysis_data else "Недостаточно данных для анализа"}

ЗАДАЧА:
1. Оцени динамику по каждому упражнению (есть прогресс или нет)
2. Найди упражнения, где прогресс остановился (плато)
3. Дай 2-3 КОНКРЕТНЫЕ рекомендации:
   - Что изменить в технике
   - Какие вспомогательные упражнения добавить
   - Как изменить программу тренировок
4. Если есть прогресс — похвали и предложи как его ускорить

ТРЕБОВАНИЯ К ОТВЕТУ:
- Без общих фраз
- Только конкретика
- С цифрами и процентами
- Максимум пользы

ОТВЕТЬ НА РУССКОМ:"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты профессиональный спортивный аналитик. Видишь даже微小 прогресс и знаешь, как его улучшить."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка AITUNNEL: {e}")
            return None
    
    async def answer_question(self, question: str, user_data: Dict) -> Optional[str]:
        """Ответ на конкретный вопрос пользователя"""
        if not self.enabled:
            return None
        
        try:
            name = user_data.get('first_name', 'Спортсмен')
            level = user_data.get('experience', 'средний')
            
            prompt = f"""Ты — профессиональный тренер с ученой степенью в спортивной науке. Отвечай на вопросы клиента {name} (уровень: {level}).

ВОПРОС КЛИЕНТА: "{question}"

ПРАВИЛА ОТВЕТА:
1. Отвечай максимально конкретно и научно
2. Если вопрос про упражнение — объясни технику, частые ошибки, как прогрессировать
3. Если вопрос про питание — дай цифры (граммы, калории)
4. Если вопрос про восстановление — объясни физиологию и дай протокол
5. Ссылайся на исследования, если уместно
6. Будь дружелюбен, но профессиональен

ПРИМЕРЫ ХОРОШИХ ОТВЕТОВ:
- "Для приседаний оптимальная глубина — когда бедро параллельно полу. Исследования показывают, что неполные приседания дают на 30% меньше активации ягодичных."
- "После тренировки нужно 1.6-2 г белка на кг веса. При твоем весе 80 кг это 128-160 г белка в день, разделенных на 4-5 приемов."

ОТВЕТЬ НА РУССКОМ:"""

            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты профессиональный тренер и спортивный диетолог. Твои ответы точны, научны и полезны."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=600,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Ошибка AITUNNEL: {e}")
            return None

# Глобальный экземпляр
openai_service = OpenAIService()