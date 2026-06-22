# GeoPredict ML

Первая ML-версия для оценки перспективности открытия ПВЗ по пользовательскому полигону.

## Что делает пайплайн

1. Принимает запрос с `geometry`, `business_type` и `h3_resolution`.
2. Делит территорию на H3-ячейки. Если библиотека `h3` не установлена, использует совместимую fallback-сетку для локальной разработки.
3. Берет POI из OpenStreetMap/Overpass или из локального GeoJSON.
4. Считает признаки для ПВЗ: конкуренты, транспорт, жилое окружение, офисы, торговые якоря, плотность POI.
5. Обучает или загружает `GradientBoostingRegressorLite`.
6. Возвращает GeoJSON `FeatureCollection` для карты.

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

## Датасет для команды

```bash
python -m scripts.build_dataset \
  --request data/sample/request_pvz.json \
  --pois data/sample/osm_pois_pvz_sample.geojson \
  --output data/processed/pvz_features.csv
```

CSV будет содержать одну строку на H3-ячейку: признаки, counts по POI и `target_success`.

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
