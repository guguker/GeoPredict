# GeoPredict ML

Полная инструкция по запуску, формулам, признакам, порогам и ограничениям:
[`docs/TECHNICAL_GUIDE.md`](docs/TECHNICAL_GUIDE.md).

Первая ML-версия для оценки перспективности открытия ПВЗ по пользовательскому полигону.

## Что делает пайплайн

1. Принимает запрос с `geometry`, `business_type` и `h3_resolution`.
2. Делит территорию на H3-ячейки. Если библиотека `h3` не установлена, использует совместимую fallback-сетку для локальной разработки.
3. Берет POI из OpenStreetMap/Overpass или из локального GeoJSON.
4. Считает признаки для ПВЗ: конкуренты, транспорт, жилое окружение, офисы, торговые якоря, плотность POI.
5. Обучает или загружает `GradientBoostingRegressorLite`.
6. Возвращает GeoJSON `FeatureCollection` для карты с ранжированием ячеек и списком лучших кандидатов.

## Почему ПВЗ сделан отдельно

ПВЗ оценивается не как обычный магазин. Для Ozon, Wildberries, Яндекс Маркета, СДЭК, Boxberry, PickPoint и похожих брендов важны:

- жилая плотность;
- пешая и транспортная доступность;
- торговые и сервисные точки притяжения;
- офисный дневной поток;
- наличие конкурентов как сигнал подтвержденного спроса;
- штраф за перенасыщение конкурентами.

## Формат запроса

```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[37.6173, 55.7558], [37.6273, 55.7558], [37.6273, 55.7658], [37.6173, 55.7658], [37.6173, 55.7558]]]
  },
  "business_type": "pickup_point",
  "h3_resolution": 9
}
```

`business_type` принимает один из 10 фиксированных профилей или его алиас на русском/английском. ПВЗ остается общей группой: `pickup_point`, а внутри профиля учитываются Ozon, Wildberries, Яндекс Маркет, СДЭК, Boxberry и похожие операторы.

Поддерживаемые основные значения:

- `pickup_point` — Пункт выдачи заказов
- `coffee_shop` — Кофейня
- `beer_store` — Пивной магазин / бар
- `pharmacy` — Аптека
- `grocery_store` — Продуктовый магазин
- `bakery` — Пекарня
- `fast_food` — Фастфуд / шаурма
- `restaurant` — Ресторан / кафе
- `beauty_salon` — Красота / барбершоп / маникюр
- `medical_clinic` — Клиника / стоматология
- `car_service` — Автосервис

Для фронта есть справочник:

```text
GET /business-types
GET /business-types?query=кофе
```

Если пользователь введет свободный текст, фронт может сначала запросить `GET /business-types?query=...` и показать подсказки. По умолчанию `/analyze` тоже принимает неподдержанный `business_type`: API создаёт временный `custom_osm` профиль и ищет похожие точки в OSM по `name`, `brand`, `shop`, `amenity` и другим тегам. В ответе тогда будет `metadata.is_custom_business = true`, `business_type = "custom_osm"` и `business_query` с исходной строкой.

Если нужен строго только фиксированный каталог, передайте:

```json
{
  "allow_custom_business": false
}
```

Тогда неподдержанный тип вернет `422` с кодом `unsupported_business_type`, списком допустимых `supported_business_types` и массивом `suggestions`.

## Быстрый локальный прогон без сети

```bash
python -m scripts.train_model \
  --business-type pickup_point \
  --output models/geopredict_pvz_v1.pkl

python -m scripts.analyze_polygon \
  --request data/sample/request_pvz.json \
  --pois data/sample/osm_pois_pvz_sample.geojson \
  --model models/geopredict_pvz_v1.pkl
```

## Модельные артефакты

Десять бизнес-профилей объединены в пять модельных семейств, поэтому в
`models/` лежит пять основных `.pkl`. API выбирает артефакт семейства по
каноническому `business_type`; если файла нет, временно обучает
reference-модель в памяти.

Перегенерировать весь registry:

```bash
python -m scripts.train_all_models --models-dir models
```

Список артефактов и бизнес-типов хранится в `models/manifest.json`. Для обратной совместимости ПВЗ-модель остается в `models/geopredict_pvz_v1.pkl`.

## Структура проекта

```text
api/              FastAPI-приложение и Swagger/OpenAPI контракт
geopredict_ml/    ML-пайплайн, признаки, бизнес-профили, сетка, OSM и модель
scripts/          CLI-команды для сбора OSM, обучения, анализа и сборки датасета
data/sample/      Пример запроса и локальные sample POI для запуска без сети
data/processed/   Примеры рассчитанных признаков и GeoJSON-результата
models/           Сохраненные артефакты моделей и manifest
tests/            Контрактные, feature- и model-тесты
docs/             Дополнительная API-документация
```

## Тесты

```bash
python -m unittest discover tests
```

## Датасет для команды

```bash
python -m scripts.build_dataset \
  --request data/sample/request_pvz.json \
  --pois data/sample/osm_pois_pvz_sample.geojson \
  --output data/processed/pvz_features.csv
```

CSV будет содержать одну строку на H3-ячейку: признаки, counts по POI и `target_success`.

## Оценка модели

Для текущего MVP метрики считаются по колонке `target_success`. Это proxy-таргет, поэтому такие метрики показывают, насколько модель воспроизводит заданную геомаркетинговую формулу успешности. Когда появятся исторические данные по фактическим открытиям ПВЗ, можно добавить колонку вроде `actual_success` и передать ее через `--target-column`.

Оценить сохраненный артефакт модели на размеченном CSV:

```bash
python -m scripts.evaluate_model \
  --dataset data/processed/pvz_features.csv \
  --model models/geopredict_pvz_v1.pkl
```

Сделать holdout-проверку: обучить свежую модель на train-части CSV и посчитать метрики на test-части:

```bash
python -m scripts.evaluate_model \
  --dataset data/processed/pvz_features.csv \
  --fit-holdout \
  --test-size 0.25 \
  --seed 42
```

В отчете выводятся `mae`, `mse`, `rmse`, `median_absolute_error`, `max_error`, `bias`, `mape`, `r2`, а также baseline по среднему значению target.

## Сбор данных из OSM

```bash
python -m scripts.collect_osm \
  --request data/sample/request_pvz.json \
  --output data/raw/osm_pois.geojson
```

Затем:

```bash
python -m scripts.analyze_polygon \
  --request data/sample/request_pvz.json \
  --pois data/raw/osm_pois.geojson \
  --model models/geopredict_pvz_v1.pkl \
  --output data/processed/pvz_analysis.geojson
```

## API

Если установлен FastAPI:

```bash
uvicorn api.analyze:app --reload
```

`POST /analyze` принимает тот же JSON. По умолчанию API пробует получить POI из OSM/Overpass.

Для локальной разработки API разрешает CORS-запросы с `http://localhost:3000`, `http://127.0.0.1:3000`, `http://localhost:5173` и `http://127.0.0.1:5173`. Если фронт живет на другом адресе, передайте список через `GEOPREDICT_CORS_ORIGINS`, например `GEOPREDICT_CORS_ORIGINS=http://localhost:8080`.

В ответе каждая ячейка содержит `rank`, `suitability`, `success_probability`, `model_score`, `selection_score`, `data_confidence`, `recommendation`, `recommendation_label`, счетчики POI и объяснения. `model_score` — сырой ML-score, а `suitability`/`selection_score` — более строгая v2-оценка для карты и топа: она учитывает силу локальных сигналов, уверенность данных, насыщение зоны и относительный ранг внутри выбранного полигона.

Если Overpass временно отвечает ошибкой вроде `429 Too Many Requests`, API больше не падает `502`. Он возвращает GeoJSON с `metadata.data_status = "degraded"`, `data_sources = ["osm_unavailable"]` и предупреждением в `metadata.data_warnings`.

Короткий пример свойств одной ячейки:

```json
{
  "h3_id": "891f1d489ffffff",
  "rank": 1,
  "top_percentile": 0.01,
  "suitability": 0.742,
  "success_probability": 0.742,
  "model_score": 0.812,
  "selection_score": 0.742,
  "data_confidence": 0.781,
  "recommendation": "high_priority",
  "recommendation_label": "Приоритетно рассмотреть",
  "competition": 3,
  "traffic_potential": 0.691,
  "density_score": 0.638,
  "poi_counts": {
    "competitors": 3,
    "public_transport": 4,
    "residential": 15
  },
  "explanation": [
    "Перспективная локация",
    "Конкуренция есть, но зона не выглядит перенасыщенной"
  ]
}
```

Сводка лучших зон приходит в `metadata`:

```json
{
  "top_candidates": [
    {
      "h3_id": "891f1d489ffffff",
      "rank": 1,
      "suitability": 0.742,
      "model_score": 0.812,
      "data_confidence": 0.781,
      "recommendation": "high_priority",
      "center": {"lon": 37.6173, "lat": 55.7558}
    }
  ],
  "data_status": "live",
  "poi_count": 1284,
  "selection_policy": "strict_v2_rank_confidence_saturation",
  "recommendation_counts": {
    "high_priority": 4,
    "promising": 21,
    "manual_review": 14,
    "low_priority": 3
  }
}
```

Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI JSON:

```text
http://localhost:8000/openapi.json
```

## Docker

```bash
docker compose up --build
```

После запуска:

```text
API: http://localhost:8000
Swagger: http://localhost:8000/docs
Health: http://localhost:8000/health
```

## Важная формулировка для защиты

Модель не прогнозирует фактическую будущую выручку конкретного предпринимателя. Она рассчитывает вероятность успешности локации на основе внешних геомаркетинговых факторов: конкуренции, инфраструктуры, транспортной доступности, плотности POI и proxy-показателей спроса.

## Ограничения MVP

- Данные OSM могут быть неполными: отсутствие POI в выгрузке не всегда означает отсутствие объекта в реальности.
- Overpass API может быть медленным или временно недоступным, поэтому для демо и тестов предусмотрен локальный sample GeoJSON.
- `target_success` является proxy-таргетом, построенным из геомаркетинговых факторов, а не фактической исторической выручкой.
- Результат модели стоит использовать как предварительный скоринг территории; финальное решение об открытии ПВЗ требует проверки помещения, арендной ставки, входной группы, видимости и операционных условий.
