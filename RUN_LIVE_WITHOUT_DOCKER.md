# GeoPredict: запуск без Docker, только live-данные

Это инструкция для запуска API локально без Docker. Mock/sample-данные не используются.

## Что нужно установить

- Python 3.11 или новее
- Интернет-доступ: API получает POI из OpenStreetMap через Overpass

## Запуск на Windows

```bat
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn api.analyze:app --host 127.0.0.1 --port 8000
```

## Запуск на macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m uvicorn api.analyze:app --host 127.0.0.1 --port 8000
```

## Проверка

Открыть в браузере:

```text
http://127.0.0.1:8000/docs
```

Проверка здоровья API:

```text
http://127.0.0.1:8000/health
```

## Пример live-запроса

В Swagger открыть `POST /analyze`, нажать `Try it out` и отправить:

```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[37.6173, 55.7558], [37.6273, 55.7558], [37.6273, 55.7658], [37.6173, 55.7658], [37.6173, 55.7558]]]
  },
  "business_type": "pickup_point",
  "h3_resolution": 9,
  "data_mode": "live"
}
```

Если Overpass временно ограничит запросы или будет недоступен, это проблема внешнего сервиса OSM. Нужно повторить позже или выбрать меньший полигон.
