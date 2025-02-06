import json
import time
from requests import HTTPError
from LentaAPI import LentaAPI

class LentaParser:
    """Класс для автоматического парсинга товаров в наличии из приложения Лента в МСК и Питере, где более 100 товаров"""
    
    TARGET_CITIES = {"Москва", "Санкт-Петербург"}

    def __init__(self, api: LentaAPI):
        self.api: LentaAPI = api
        self.city_stores = {}
    
    def _get_target_stores(self):
        """Фильтрует магазины только в Москве и Санкт-Петербурге"""
        stores = self.api.get_stores()
        for store in stores["items"]:
            for city in self.TARGET_CITIES:
                if city in store["addressFull"]:
                    self.city_stores[city] = store["id"]
                    break
        
        if not self.city_stores:
            raise ValueError("Нет доступных магазинов в Москве и Санкт-Петербурге")

    def _get_suitable_category(self):
        """Находит первую категорию, где более 100 товаров"""
        categories = self.api.get_categories()

        for category in categories:
            print(f"Проверяю категорию: {category['name']}...")
            items = self.api.get_catalog_items(category["id"])
            if items and items["total"] >= 100:
                print(f"✅ Найдено {items['total']} товаров в категории {category['name']}!")
                return category["id"], category["name"]
            
        return None, None

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

    def _parse_products(self, category_id):
        """Получает товары из категории и фильтрует только в наличии"""
        print(f"Парсинг товаров из категории {category_id}...")
        data = self.api.get_catalog_items(category_id)
        products = []

        for item in data["items"]:
            if item["features"]["isBlockedForSale"] and item["count"] > 0:
                continue  # Пропускаем недоступные товары

            products.append({
                "id": item["id"],
                "name": item["name"],
                "brand": self._get_brand_of_product(item["id"]),
                "regular_price": item["prices"]["costRegular"] / 100,
                "promo_price": item["prices"]["cost"] / 100
            })
            print(f"🛒 {item['name']} ({item['id']}) добавлен в список")

        print(f"✅ Найдено {len(products)} товаров в наличии!")
        return products

    def run(self):
        """Основная логика парсинга"""
        self._get_target_stores()

        all_results = {}
        for city, store_id in self.city_stores.items():
            if city in all_results:
                print(f"⚠️ Город {city} уже обработан, пропускаем...")
                continue

            print(f"\n📍 Выбран город: {city}, магазин ID: {store_id}")
            self.api.set_delivery(store_id)
            self.api.set_store(store_id)
            time.sleep(2) # Делаем паузу, чтобы не забанили

            category_id, category_name = self._get_suitable_category()
            if category_id is None:
                print(f"❌ Не найдено подходящей категории с более чем 100 товарами в городе: {city}, магазин ID: {store_id}")
                continue

            products = self._parse_products(category_id)

            all_results[city] = products

            time.sleep(2) # Делаем паузу, чтобы не забанили

        return all_results
    
    def save_results(self, data):
        """Сохраняет результаты в JSON"""
        with open("lenta_products.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        print("✅ Данные сохранены в lenta_products.json")

if __name__ == "__main__":
    api = LentaAPI()
    parser = LentaParser(api)
    
    results = parser.run()  # Запускаем парсер
    parser.save_results(results)  # Сохраняем в JSON
