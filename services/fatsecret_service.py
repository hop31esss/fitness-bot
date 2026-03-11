import requests
from requests_oauthlib import OAuth2Session
from oauthlib.oauth2 import LegacyApplicationClient
import json
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)

class FatSecretService:
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = "https://oauth.fatsecret.com/connect/token"
        self.api_url = "https://platform.fatsecret.com/rest/server.api"
        self.token = None
        
    def _get_token(self):
        """Получение OAuth 2.0 токена"""
        if not self.token:
            oauth = OAuth2Session(client=LegacyApplicationClient(client_id=self.client_id))
            self.token = oauth.fetch_token(
                token_url=self.token_url,
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            logger.info("✅ Токен FatSecret получен")
        return self.token
    
    def _make_request(self, params: dict) -> Optional[dict]:
        """Базовый метод для запросов к API"""
        try:
            token = self._get_token()
            headers = {'Authorization': f'Bearer {token["access_token"]}'}
            
            response = requests.get(
                self.api_url,
                params=params,
                headers=headers
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Ошибка API: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Ошибка запроса: {e}")
            return None
    
    def search_foods(self, query: str, page: int = 0, max_results: int = 20) -> Optional[List[Dict]]:
        """Поиск продуктов по названию"""
        params = {
            'method': 'foods.search',
            'format': 'json',
            'search_expression': query,
            'page_number': page,
            'max_results': max_results
        }
        
        data = self._make_request(params)
        if data and 'foods' in data and 'food' in data['foods']:
            return data['foods']['food']
        return []
    
    def get_food_details(self, food_id: str) -> Optional[Dict]:
        """Получение детальной информации о продукте"""
        params = {
            'method': 'food.get',
            'format': 'json',
            'food_id': food_id
        }
        
        data = self._make_request(params)
        return data.get('food') if data else None
    
    def get_nutrition_data(self, food_data: Dict) -> Dict:
        """Извлекает БЖУ из данных продукта"""
        nutrition = {
            'calories': 0,
            'protein': 0,
            'fat': 0,
            'carbs': 0,
            'fiber': 0,
            'sugar': 0
        }
        
        if 'servings' in food_data and 'serving' in food_data['servings']:
            serving = food_data['servings']['serving']
            if isinstance(serving, list):
                serving = serving[0]
            
            nutrition['calories'] = float(serving.get('calories', 0))
            nutrition['protein'] = float(serving.get('protein', 0))
            nutrition['fat'] = float(serving.get('fat', 0))
            nutrition['carbs'] = float(serving.get('carbohydrate', 0))
            nutrition['fiber'] = float(serving.get('fiber', 0))
            nutrition['sugar'] = float(serving.get('sugar', 0))
            
        return nutrition