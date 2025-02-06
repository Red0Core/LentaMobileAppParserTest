# LentaMobileAppParserTest

Этот проект представляет собой парсер, предназначенный для извлечения данных из API мобильного приложения Лента. Он фокусируется на выявлении ЛЮБОЙ ПЕРВОЙ КАТЕГОРИИ с более чем 100 товарами, доступными в магазинах Москвы и Санкт-Петербурга. Извлекаемые данные включают:

- ID товара
- Название товара
- Регулярная цена
- Промо-цена
- Бренд

Результаты экспортируются в формате JSON.

## Особенности

- **Фильтрация категорий**: Находит ЛЮБУЮ ПЕРВУЮ категорию с более чем 100 товарами, доступными в Москве и Санкт-Петербурге.
- **Извлечение данных**: Получает основные детали о товарах, такие как ID, название, цены и бренд.
- **Экспорт в JSON**: Сохраняет извлеченные данные в JSON-файл для дальнейшего анализа.

## Требования

- Python 3.7 или выше
- Библиотека `requests`

## Установка

1. **Клонирование репозитория**:

   ```bash
   git clone https://github.com/Red0Core/LentaMobileAppParserTest.git
   cd LentaMobileAppParserTest

2. **Установка зависимостей**:
    ```bash
    python -m venv venv
    source venv/bin/activate  # Для Windows используйте venv\Scripts\activate
    pip install -r requirements.txt

3. **Запуск парсера**:
    ```bash
    python LentaParser.py

## Примечания
- Убедитесь, что ваш IP-адрес не заблокирован API Ленты. Если вы столкнулись с проблемами, рассмотрите возможность использования прокси или VPN.
- Скрипт включает базовую обработку ошибок, но можно внести дополнительные улучшения для повышения устойчивости.

## Результаты
Извлеченные данные сохраняются в файле lenta_products_piter_moscow.json в следующем формате:
```JSON
[
    {
        "id": 12345,
        "name": "Название товара",
        "brand": "Название бренда",
        "regular_price": 100.0,
        "promo_price": 80.0
    },
    ...
]
