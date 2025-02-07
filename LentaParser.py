import json
import pprint
import time
from requests import HTTPError
from LentaAPI import LentaAPI
import random

class LentaParser:
    """Класс для автоматического парсинга товаров в наличии из приложения Лента в МСК и Питере, где более 100 товаров"""
    
    TARGET_CITIES = {"Москва", "Санкт-Петербург"}

    def __init__(self, api: LentaAPI):
        self.api: LentaAPI = api
        self.city_stores = {"Москва": [], "Санкт-Петербург": []}
    
    def _get_target_stores(self):
        """Фильтрует магазины только в Москве и Санкт-Петербурге"""
        stores = self.api.get_stores()
        for store in stores["items"]:
            for city in self.TARGET_CITIES:
                if city in store["addressFull"] and store['marketType'] == "HM": # Проверка на город и Гипермаркет(больше товаров)
                    self.city_stores[city].append(store["id"])
                    break
        
        if not self.city_stores:
            raise ValueError("Нет доступных магазинов в Москве и Санкт-Петербурге")

    def _get_brand_of_product(self, product_id, max_retries=7, backoff_factor=2):
        """Получает бренд товара по его ID с повторными попытками при ошибках"""
        attempt = 0
        while attempt < max_retries: # Дефолтное значение будет доходить до целой минуты
            try:
                data = self.api.get_catalog_item(product_id)
                for attribute in data.get('attributes', []):
                    if attribute['alias'] == 'brand' or attribute['name'] == 'Бренд' or attribute['slug'] == 'brand':
                        return attribute['value']
                
                return "Без бренда"
            except HTTPError as e:
                print(f"❌ Ошибка HTTP: {e}")
                if e.response.status_code == 429:
                    print(f"⚠️ Превышен лимит запросов, делаем паузу на {backoff_factor ** attempt} секунд")
                attempt += 1
                time.sleep(backoff_factor ** attempt)

    def run(self):
        """Основная логика парсинга"""
        self._get_target_stores()

        # Получаем категории первого уровня в МСК
        moscow_stores = self.city_stores.get("Москва", [])
        moscow_store = random.choice(moscow_stores)
        print(f"\n📍 Москва, магазин ID: {moscow_store}")
        self.api.set_delivery(moscow_store)
        self.api.set_store(moscow_store)
        moscow_categories_level_1 = {
            x['slug']: x['id']
            for x in self.api.get_categories()
            if x['level'] == 1
        }
        
        # Получаем категории первого уровня в Питере
        piter_stores = self.city_stores.get("Санкт-Петербург", [])
        piter_store = random.choice(piter_stores)
        print(f"\n📍 Питер, магазин ID: {piter_store}")
        self.api.set_delivery(piter_store)
        self.api.set_store(piter_store)
        piter_categories_level_1 = {
            x['slug']: x['id']
            for x in self.api.get_categories()
            if x['level'] == 1
        }

        # Поиск общих категорий (навсякий случай)
        common_categories = set(moscow_categories_level_1.keys()) & set(piter_categories_level_1.keys())
        for category_slug in common_categories:
            print(f"\n🔍 Поиск общих товаров в категории {category_slug}")

            # Получаем товары из категории в мск
            self.api.set_delivery(moscow_store)
            self.api.set_store(moscow_store)
            moscow_items = self.api.get_catalog_items(moscow_categories_level_1[category_slug])
            print("Делаем задержку на 5 секунд")
            time.sleep(5)

            # Получаем товары из категории в питере
            self.api.set_delivery(piter_store)
            self.api.set_store(piter_store)
            piter_items = self.api.get_catalog_items(piter_categories_level_1[category_slug])
            
            # Сравниваем товары
            if piter_items['total'] < 100 or moscow_items['total'] < 100:
                print("❌ Нехватка товаров для сравнения в категории {category_slug}")
                continue

            # Находим общие товары по id
            moscow_ids = {item["id"]: item for item in moscow_items['items'] if item["count"] > 0 and not item["features"]["isBlockedForSale"]}
            piter_ids = {item["id"]: item for item in piter_items['items'] if item["count"] > 0 and not item["features"]["isBlockedForSale"]}
            common_products = [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "regular_price": item["prices"]["costRegular"] / 100,
                    "promo_price": item["prices"]["cost"] / 100
                }
                for item_id, item in moscow_ids.items()
                if item_id in piter_ids
            ]
            
            # Проверяем результаты
            if len(common_products) < 100:
                print("❌ Нехватка общих товаров в категории {category_slug}")
                continue

            print(f"✅ Найдено {len(common_products)} общих товаров в категории {category_slug}")
            
            # Добавялем бренды к товарам
            for common_products_item in common_products:
                common_products_item["brand"] = self._get_brand_of_product(common_products_item["id"])
                print(f"🛒 {common_products_item['name']} ({common_products_item['id']}) добавлен в список" )

            return common_products
        
        print("❌ Не найдено общих категорий, где больше 100 общих товаров в наличии в Москве и Питере")
        return []

    def save_results(self, data):
        """Сохраняет результаты в JSON"""
        with open("lenta_products_piter_moscow.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("✅ Данные сохранены в lenta_products_piter_moscow.json")

if __name__ == "__main__":
    api = LentaAPI()
    parser = LentaParser(api)
    
    results = parser.run()  # Запускаем парсер
    parser.save_results(results)  # Сохраняем в JSON
