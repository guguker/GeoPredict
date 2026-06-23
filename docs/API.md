# GeoPredict API

Swagger UI доступен по адресу:

```text
http://localhost:8000/docs
```

OpenAPI JSON:

```text
http://localhost:8000/openapi.json
```

## Эндпоинты

### `GET /health`

Проверка доступности сервиса.

### `POST /analyze`

Анализирует пользовательский `Polygon`, строит H3-сетку и возвращает GeoJSON `FeatureCollection`.

Минимальный запрос:

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

Для локального теста без Overpass можно добавить:

```json
{
  "use_live_osm": false
}
```

`business_type` можно передавать как основной код или алиас. Например: `pickup_point`, `pvz`, `ozon`, `coffee_shop`, `кофейня`, `beer_store`, `пивнуха`, `dental_clinic`, `стоматология`.

Если `business_type` не найден в фиксированном каталоге, `/analyze` по умолчанию создает `custom_osm` профиль и ищет похожие объекты в OSM по пользовательской строке, названиям, брендам и тегам. Для строгого режима каталога передайте:

```json
{
  "allow_custom_business": false
}
```

В строгом режиме неподдержанный тип бизнеса вернет `422`:

```json
{
  "detail": {
    "code": "unsupported_business_type",
    "message": "Unsupported business_type: '...'",
    "supported_business_types": ["pickup_point", "coffee_shop", "beer_store"],
    "suggestions": ["coffee_shop"]
  }
}
```

### `GET /business-types`

Возвращает фиксированный каталог из 20 поддерживаемых типов бизнеса для UI-списка. Опционально принимает `query`: тогда `business_types` содержит найденные подсказки из фиксированного каталога, а `custom_candidate` описывает свободный пользовательский запрос для OSM-поиска:

```text
GET /business-types?query=кофе
```

```json
{
  "total": 1,
  "business_types": [
    {
      "business_type": "pickup_point",
      "title": "Пункт выдачи заказов",
      "category": "marketplace_logistics",
      "aliases": ["pickup_point", "pvz", "пвз", "ozon"],
      "examples": ["Ozon", "Wildberries", "Яндекс Маркет", "СДЭК", "Boxberry"],
      "radius_m": 500
    }
  ],
  "custom_candidate": {
    "business_type": "custom_osm",
    "title": "Пользовательский бизнес: кофе",
    "category": "custom_osm_search",
    "source_query": "кофе",
    "is_custom": true
  }
}
```

Ответ `POST /analyze` содержит:

- `features[]` — GeoJSON-ячейки с v2-оценкой `suitability`, сырым `model_score`, строгим `selection_score`, уверенностью данных `data_confidence`, рангом `rank`, кодом рекомендации `recommendation`, объяснениями и счетчиками POI.
- `features[].properties.explanation_factors` — структурированные факторы плюс/минус для интерфейса объяснений.
- `metadata.business_search` — как был выбран профиль: фиксированный каталог или `custom_osm`, какие OSM-ключи/слова используются.
- `metadata.top_candidates` — до 10 лучших ячеек по оценке модели для быстрого вывода списка приоритетных зон.
- `metadata.recommendation_counts` — количество ячеек в группах `high_priority`, `promising`, `manual_review`, `low_priority`.
- `metadata.data_status` — `live`, `degraded` или `empty`. При ошибках Overpass, включая `429 Too Many Requests`, API возвращает `degraded` вместо HTTP 502.

### `POST /analyze-jobs`

Запускает тот же анализ в job-режиме и сразу возвращает `job_id` со статусом `queued`/`running`. Это нужно для больших полигонов и live OSM-запросов.

### `GET /analyze-jobs/{job_id}`

Возвращает состояние job: `queued`, `running`, `done` или `failed`. Когда job завершена, поле `result` содержит тот же GeoJSON `FeatureCollection`, что и `POST /analyze`.

Для API-кэша Overpass можно задать переменную окружения:

```bash
GEOPREDICT_OSM_CACHE_DIR=data/cache/osm
```

Пример свойств одной ячейки:

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
  ],
  "explanation_factors": [
    {
      "feature": "residential_score",
      "label": "Жилая база",
      "value": 0.72,
      "weight": 0.24,
      "impact": 0.173,
      "direction": "positive",
      "message": "Поддерживает оценку"
    }
  ]
}
```
