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

Ответ содержит:

- `features[]` — GeoJSON-ячейки с ML-оценкой `suitability`, вероятностью `success_probability`, рангом `rank`, кодом рекомендации `recommendation`, объяснениями и счетчиками POI.
- `metadata.top_candidates` — до 10 лучших ячеек по оценке модели для быстрого вывода списка приоритетных зон.
- `metadata.recommendation_counts` — количество ячеек в группах `high_priority`, `promising`, `manual_review`, `low_priority`.

Пример свойств одной ячейки:

```json
{
  "h3_id": "891f1d489ffffff",
  "rank": 1,
  "suitability": 0.742,
  "success_probability": 0.742,
  "recommendation": "promising",
  "recommendation_label": "Перспективная зона",
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
