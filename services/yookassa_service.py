import logging
from yookassa import Configuration, Payment
from yookassa.domain.notification import WebhookNotification
import uuid
from typing import Optional, Dict

from config import YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY

logger = logging.getLogger(__name__)

# Настройка ЮKassa
Configuration.account_id = YOOKASSA_SHOP_ID
Configuration.secret_key = YOOKASSA_SECRET_KEY

class YooKassaService:
    """Сервис для работы с ЮKassa API"""
    
    @staticmethod
    async def create_payment(amount: float, description: str, user_id: int, return_url: str = None) -> Optional[Dict]:
        """
        Создание платежа в ЮKassa
        
        Args:
            amount: сумма платежа
            description: описание платежа
            user_id: ID пользователя для метаданных
            return_url: URL для возврата после оплаты
            
        Returns:
            словарь с данными платежа или None при ошибке
        """
        try:
            # Генерируем уникальный IDempotence key
            idempotence_key = str(uuid.uuid4())
            
            # Создаем платеж
            payment = Payment.create({
                "amount": {
                    "value": f"{amount:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url or "https://t.me/StrengthAIBot"
                },
                "capture": True,
                "description": description,
                "metadata": {
                    "user_id": str(user_id)
                }
            }, idempotence_key)
            
            logger.info(f"✅ Платеж создан: {payment.id}")
            return {
                "id": payment.id,
                "amount": payment.amount.value,
                "confirmation_url": payment.confirmation.confirmation_url,
                "status": payment.status
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания платежа: {e}")
            return None
    
    @staticmethod
    async def get_payment_status(payment_id: str) -> Optional[str]:
        """Получение статуса платежа"""
        try:
            payment = Payment.find_one(payment_id)
            return payment.status
        except Exception as e:
            logger.error(f"❌ Ошибка получения статуса: {e}")
            return None
    
    @staticmethod
    async def capture_payment(payment_id: str, amount: float) -> bool:
        """Подтверждение платежа (если capture=False)"""
        try:
            idempotence_key = str(uuid.uuid4())
            payment = Payment.capture(
                payment_id,
                {
                    "amount": {
                        "value": f"{amount:.2f}",
                        "currency": "RUB"
                    }
                },
                idempotence_key
            )
            return payment.status == "succeeded"
        except Exception as e:
            logger.error(f"❌ Ошибка подтверждения: {e}")
            return False
    
    @staticmethod
    async def cancel_payment(payment_id: str) -> bool:
        """Отмена платежа"""
        try:
            idempotence_key = str(uuid.uuid4())
            payment = Payment.cancel(payment_id, idempotence_key)
            return payment.status == "canceled"
        except Exception as e:
            logger.error(f"❌ Ошибка отмены: {e}")
            return False