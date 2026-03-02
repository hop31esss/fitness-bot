import openai
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class OpenAIService:
    def __init__(self):
        # Вместо OpenAI используем российский агрегатор
        self.client = openai.OpenAI(
            api_key="sk-aitunnel-dAut1vwt4gXAHGjwqXJ621cvxLpJ1kJP",  # Ключ от /AITUNNEL
            base_url="https://api.aitunnel.ru/v1"
        )
        self.enabled = True  # Всегда включено
    
    async def get_training_advice(self, user_data: Dict) -> Optional[str]:
        """Получить персональный совет по тренировке"""
        if not self.enabled:
            return None
        
        try:
            # Формируем промпт на основе данных пользователя
            prompt = self._create_training_prompt(user_data)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты профессиональный фитнес-тренер. Давай краткие, конкретные советы."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return None
    
    async def get_workout_plan(self, user_data: Dict) -> Optional[str]:
        """Сгенерировать план тренировки"""
        if not self.enabled:
            return None
        
        try:
            prompt = self._create_workout_plan_prompt(user_data)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты профессиональный фитнес-тренер. Составь эффективный план тренировки."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return None
    
    async def analyze_progress(self, user_data: Dict, history: List[Dict]) -> Optional[str]:
        """Проанализировать прогресс и дать рекомендации"""
        if not self.enabled:
            return None
        
        try:
            prompt = self._create_analysis_prompt(user_data, history)
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "Ты профессиональный фитнес-тренер. Проанализируй прогресс и дай рекомендации."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.7
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI error: {e}")
            return None
    
    def _create_training_prompt(self, user_data: Dict) -> str:
        """Создать промпт для совета по тренировке"""
        name = user_data.get('first_name', 'Пользователь')
        workouts = user_data.get('total_workouts', 0)
        streak = user_data.get('current_streak', 0)
        
        return (
            f"Пользователь: {name}\n"
            f"Всего тренировок: {workouts}\n"
            f"Текущая серия: {streak} дней\n\n"
            f"Дай один конкретный совет, как улучшить эффективность тренировок. "
            f"Ответ должен быть кратким (3-4 предложения) и мотивирующим."
        )
    
    def _create_workout_plan_prompt(self, user_data: Dict) -> str:
        """Создать промпт для плана тренировки"""
        goal = user_data.get('goal', 'общая физическая подготовка')
        experience = user_data.get('experience', 'средний')
        
        return (
            f"Уровень подготовки: {experience}\n"
            f"Цель: {goal}\n\n"
            f"Составь план одной тренировки (разминка, основные упражнения, заминка). "
            f"Дай конкретные упражнения, подходы и повторения."
        )
    
    def _create_analysis_prompt(self, user_data: Dict, history: List[Dict]) -> str:
        """Создать промпт для анализа прогресса"""
        workouts_count = len(history)
        total_volume = sum(h.get('total_volume', 0) for h in history)
        
        return (
            f"Проанализируй прогресс за последние {workouts_count} тренировок:\n"
            f"Общий объем: {total_volume} кг\n"
            f"Данные по дням: {history}\n\n"
            f"Дай 2-3 рекомендации для дальнейшего прогресса."
        )

# Глобальный экземпляр
openai_service = OpenAIService()