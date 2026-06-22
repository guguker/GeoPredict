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
