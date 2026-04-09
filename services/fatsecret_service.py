import httpx
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class FatSecretService:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = None
        self.token_url = "https://oauth.fatsecret.com/connect/token"
        self.api_url = "https://platform.fatsecret.com/rest/server.api"
    
    async def _get_token(self):
        """Получение OAuth2 токена напрямую через async HTTP клиент."""
        if self.token:
            return self.token
        
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'basic'
            }
            
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(self.token_url, data=data)
            
            if response.status_code == 200:
                self.token = response.json()
                logger.info("✅ Токен FatSecret получен")
                return self.token
            else:
                logger.error(f"❌ Ошибка получения токена: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"❌ Ошибка: {e}")
            return None
    
    async def search_foods(self, query: str, page: int = 0, max_results: int = 20) -> Optional[List[Dict]]:
        """Поиск продуктов"""
        token = await self._get_token()
        if not token:
            return []
        
        params = {
            'method': 'foods.search',
            'format': 'json',
            'search_expression': query,
            'page_number': page,
            'max_results': max_results
        }
        
        headers = {'Authorization': f"Bearer {token['access_token']}"}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.api_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                if 'foods' in data and 'food' in data['foods']:
                    return data['foods']['food']
                return []
            else:
                logger.error(f"Ошибка API: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Ошибка запроса: {e}")
            return []
    
    async def get_food_details(self, food_id: str) -> Optional[Dict]:
        """Получение деталей продукта"""
        token = await self._get_token()
        if not token:
            return None
        
        params = {
            'method': 'food.get',
            'format': 'json',
            'food_id': food_id
        }
        
        headers = {'Authorization': f"Bearer {token['access_token']}"}
        
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(self.api_url, params=params, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('food')
            else:
                logger.error(f"Ошибка API: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка запроса: {e}")
            return None