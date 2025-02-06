import json
import time
from timeit import repeat
from requests import HTTPError
from LentaAPI import LentaAPI

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

        products = []
        moscow_stores = self.city_stores.get("Москва", [])
        piter_stores = self.city_stores.get("Санкт-Петербург", [])

        for moscow_store in moscow_stores:
            print(f"\n📍 Москва, магазин ID: {moscow_store}")
            self.api.set_delivery(moscow_store)
            self.api.set_store(moscow_store)
            time.sleep(2)

            moscow_items = []
            categories = self.api.get_categories()
            category_moscow_id = None
            for category in categories:
                print(f"Проверяю категорию: {category['name']}...")
                items = self.api.get_catalog_items(category["id"])
                if items and items["total"] >= 100:
                    print(f"✅ Найдено {items['total']} товаров в категории {category['name']}!")
                    category_moscow_id = category["id"]
                    moscow_items = items

                    # Теперь ищем в питере нужную нам категорию с товарами
                    for piter_store in piter_stores:
                        print(f"\n📍 Питер, магазин ID: {piter_store}")
                        self.api.set_delivery(piter_store)
                        self.api.set_store(piter_store)
                        time.sleep(2)

                        repeat_items = []
                        piter_items = self.api.get_catalog_items(category_moscow_id)
                        if piter_items and piter_items['total'] > 100:
                            print(f"✅ Найдено {piter_items['total']} товаров в категории {category['name']} в Питере!")
                            
                            # Теперь ищем совпадения
                            for moscow_item in moscow_items['items']:
                                for piter_item in piter_items['items']:
                                    if moscow_item['id'] == piter_item['id'] \
                                        and moscow_item['count'] > 0 \
                                        and piter_item['count'] > 0:

                                        repeat_items.append(moscow_item)

                        if len(repeat_items) >= 100:
                            print(f"✅ Найдено {len(repeat_items)} товаров в наличии в обоих городах!")

                            # Добавляем товары в выходной список
                            for item in repeat_items:
                                products.append({
                                    "id": item["id"],
                                    "name": item["name"],
                                    "brand": self._get_brand_of_product(item["id"]),
                                    "regular_price": item["prices"]["costRegular"] / 100,
                                    "promo_price": item["prices"]["cost"] / 100
                                })
                            print(f"✅ Добавлено {len(repeat_items)} товаров в список!")
                            return products
                        else:
                            print(f"❌ Не найдено товаров в обоих городах больше 100, а именно {len(repeat_items)}")
                            
            if category_moscow_id is None:
                print(f"❌ Не найдено подходящей категории с более чем 100 товарами в Москве, магазин ID: {moscow_store}")
                continue

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
