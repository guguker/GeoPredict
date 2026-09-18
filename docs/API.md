# GeoPredict API

API принимает GeoJSON `Polygon` и возвращает ранжированные ячейки в `FeatureCollection`. Оценка строится на синтетическом proxy-target; поля score не являются прогнозом выручки или вероятностью успеха бизнеса.

После запуска `python -m uvicorn api.analyze:app --host 127.0.0.1 --port 8000` доступны [Swagger UI](http://127.0.0.1:8000/docs) и [OpenAPI JSON](http://127.0.0.1:8000/openapi.json).

## Эндпоинты

| Метод | Путь | Назначение |
|---|---|---|
| GET | `/health` | Доступность приложения |
| GET | `/business-types` | 10 фиксированных бизнес-профилей |
| GET | `/business-types?query=кофе` | Подсказки из каталога и `custom_candidate` |
| POST | `/analyze` | Анализ территории |

## Запрос анализа

```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[37.6173, 55.7558], [37.6273, 55.7558], [37.6273, 55.7658], [37.6173, 55.7658], [37.6173, 55.7558]]]
  },
  "business_type": "pickup_point",
  "h3_resolution": 9,
  "data_mode": "live",
  "allow_custom_business": true
}
```

Координаты идут в порядке `[longitude, latitude]`. Разрешение H3 — от 7 до 10; синхронный анализ ограничен 1 000 ячейками.

`business_type` принимает код или алиас, например `pickup_point`, `pvz`, `ozon`, `coffee_shop`, `кофейня`, `pharmacy`, `стоматология`. С неизвестным типом при `allow_custom_business=true` создаётся общий профиль `custom_osm`; он ищет подходящие OSM-объекты по строке запроса и не имеет собственной обученной модели. Для явного `business_type="custom_osm"` передайте `business_query` длиной 2–120 символов.

При `allow_custom_business=false` неизвестный профиль возвращает `422 unsupported_business_type` со списком допустимых значений и подсказками.

### Источники данных

- `data_mode="live"` (по умолчанию): Overpass, свежий файловый кэш или резервный stale-кэш с предупреждением.
- `data_mode="mock"`: включённый sample для ПВЗ в области московского демо-полигона. Используйте [готовый запрос](../data/sample/request_pvz_mock.json).
- `use_live_osm` — устаревшее поле. `use_live_osm=false` не включает демо и отклоняется; используйте `data_mode`.

Если Overpass и кэш недоступны, API возвращает `503` с `detail.code="osm_unavailable"` и `retryable=true`. Live-запрос не подменяется демонстрационными POI.

## Ответ

- `features[]`: геометрия ячеек; `rank`, `suitability`, `model_score`, `selection_score`, `data_confidence`, рекомендации, `poi_counts`, объяснения.
- `metadata.top_candidates`: до 10 лучших кандидатов.
- `metadata.recommendation_counts`: распределение по категориям рекомендаций.
- `metadata.recommendations_available`: доступны ли рекомендации при имеющихся POI.
- `metadata.data_status`: `live`, `cached`, `mock` или `insufficient`.
- `metadata.data_sources`, `data_warnings`, `data_fetched_at`: источник и состояние данных.
- `metadata.target_type`: `proxy_location_success`.
- `metadata.grid_backend`: фактически использованная сетка — `h3` или fallback.
- `metadata.model_source`: зарегистрированный артефакт, явно указанный артефакт или reference-модель в памяти.

`model_score` — сырой выход бустинга. `selection_score` и `suitability` — итог после эвристических поправок. Поле `success_probability` является алиасом `selection_score`: название сохранено для совместимости, **статистической калибровки вероятностей нет**. `data_confidence` также является эвристикой.

Форма свойств одной ячейки (значения иллюстративны, не являются метриками качества):

```json
{
  "h3_id": "891f1d489ffffff",
  "rank": 1,
  "suitability": 0.742,
  "success_probability": 0.742,
  "model_score": 0.812,
  "selection_score": 0.742,
  "data_confidence": 0.781,
  "recommendation": "high_priority",
  "recommendation_label": "Приоритетно рассмотреть",
  "competition": 3,
  "poi_counts": {"competitors": 3, "public_transport": 4, "residential": 15},
  "explanation": ["Конкуренция есть, но зона не выглядит перенасыщенной"]
}
```

При отсутствии POI `recommendations_available=false`, top-кандидаты пусты, а ячейки получают `insufficient_data`.

## Ошибки

| HTTP | Код / причина |
|---|---|
| 400 | Некорректная геометрия или несовместимые параметры анализа |
| 413 | `analysis_area_too_large`: превышен лимит ячеек; ответ содержит suggested resolution |
| 422 | Ошибка схемы запроса, `unsupported_business_type` или `mock_unavailable` |
| 503 | `osm_unavailable`: нет доступных OSM-данных и кэша |
| 502 | Другая ошибка зависимости при анализе |

## Настройка

`GEOPREDICT_CORS_ORIGINS` задаёт разрешённые origins через запятую. По умолчанию разрешены localhost/127.0.0.1 на портах 3000 и 5173. `GEOPREDICT_OSM_CACHE_DIR` задаёт каталог кэша (по умолчанию `/tmp/geopredict-osm-cache`).

Формулы признаков, веса и политика ранжирования: [техническое руководство](TECHNICAL_GUIDE.md).
