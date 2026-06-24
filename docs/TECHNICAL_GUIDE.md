# GeoPredict: запуск и техническая логика

Актуально для текущей кодовой базы в:

- `/Users/guguk/Documents/ml_here` — ML API;
- `/Users/guguk/Documents/geo_mark_front` — интерфейс;
- `/Users/guguk/Documents/express-auth-service` — авторизация.

## 1. Запуск всего проекта

### Требования

- установлен и запущен Docker Desktop;
- три папки находятся рядом в `/Users/guguk/Documents`;
- свободны порты `3000`, `8000`, `8001`, `5432`.

### Основная команда

```bash
cd /Users/guguk/Documents/ml_here
docker compose -f docker-compose.full.yml up -d --build
```

После запуска:

| Сервис | Адрес |
|---|---|
| Интерфейс | http://localhost:3000 |
| ML API | http://localhost:8000 |
| Swagger ML | http://localhost:8000/docs |
| Health ML | http://localhost:8000/health |
| Auth API | http://localhost:8001 |
| Swagger Auth | http://localhost:8001/api-docs |
| PostgreSQL Auth | `localhost:5432` |

При первом запуске нужно зарегистрировать пользователя через интерфейс.

### Проверка контейнеров

```bash
docker compose -f docker-compose.full.yml ps
```

У сервисов `geopredict-api`, `auth-db`, `auth-app`, `geo-mark-front` должен быть
статус `Up`, у `auth-db` — `healthy`.

### Просмотр логов

```bash
docker compose -f docker-compose.full.yml logs -f
```

Логи одного сервиса:

```bash
docker compose -f docker-compose.full.yml logs -f geopredict-api
docker compose -f docker-compose.full.yml logs -f geo-mark-front
docker compose -f docker-compose.full.yml logs -f auth-app
```

### Остановка

```bash
docker compose -f docker-compose.full.yml down
```

Остановка с удалением PostgreSQL и OSM-кэша:

```bash
docker compose -f docker-compose.full.yml down -v
```

Команда с `-v` удаляет зарегистрированных пользователей и локальный OSM-кэш.

### Перезапуск после изменения кода

```bash
docker compose -f docker-compose.full.yml up -d --build
```

Если нужно пересобрать только frontend:

```bash
docker compose -f docker-compose.full.yml up -d --build geo-mark-front
```

### Автоматические тесты

ML:

```bash
cd /Users/guguk/Documents/ml_here
python3 -m unittest discover -s tests
```

Frontend:

```bash
cd /Users/guguk/Documents/geo_mark_front
npm test -- --watchAll=false
```

## 2. Что именно оценивает система

Система не прогнозирует выручку, прибыль или гарантированное открытие бизнеса.
Она ранжирует H3-участки внутри выбранной пользователем территории по
геомаркетинговым proxy-признакам из OpenStreetMap.

Главный результат:

```text
suitability = selection_score
```

Это число от `0` до `1`. В интерфейсе оно показывается в процентах.

Важно:

- `model_score` — сырой прогноз регрессионной модели;
- `selection_score` — скорректированный итог для карты;
- `suitability` и `success_probability` сейчас равны `selection_score`;
- слово `probability` не означает статистически откалиброванную вероятность.

## 3. Полный путь расчёта

1. Пользователь передаёт GeoJSON `Polygon`.
2. Полигон разбивается на H3-ячейки.
3. Для всей территории запрашиваются POI из OSM/Overpass.
4. Для центра каждой ячейки считаются POI в радиусе бизнес-профиля.
5. Считаются нормализованные признаки.
6. `GradientBoostingRegressorLite` выдаёт `model_score`.
7. Поверх ML-score считаются уверенность и штрафы.
8. Получается `selection_score`.
9. Ячейки сортируются относительно друг друга.
10. По score, уверенности и месту в рейтинге присваивается рекомендация.

## 4. H3-сетка

Допустимые разрешения:

| H3 | Примерный радиус | Примерная площадь ячейки | Назначение |
|---:|---:|---:|---|
| 7 | 1220 м | 5.16 км² | крупная территория |
| 8 | 460 м | 0.737 км² | район |
| 9 | 175 м | 0.105 км² | квартал, значение по умолчанию |
| 10 | 66 м | 0.015 км² | детальный локальный анализ |

Синхронный лимит — `1000` ячеек. При превышении API возвращает HTTP `413` и
может предложить более грубое разрешение.

Если Python-библиотека `h3` недоступна, backend использует fallback-гексагональную
сетку. В ответе это видно по `metadata.grid_backend`.

## 5. Какие объекты OSM используются

Overpass запрашивает:

- `shop`;
- `amenity`;
- `office`;
- `craft`, `tourism`, `leisure`, `healthcare`, `sport`, `public_transport`;
- жилые, офисные и коммерческие здания;
- `landuse=residential`;
- автобусные остановки;
- станции, метро, трамвайные остановки и железнодорожные остановки.

Учитываются только POI, преобразованные в точки. Для way/relation используется
координата `center`, которую возвращает Overpass.

## 6. Радиус анализа бизнеса

Текущий фиксированный каталог содержит 10 профилей:

| Тип | Семейство модели | Радиус | Soft limit конкурентов | Масштаб конкуренции |
|---|---|---:|---:|---:|
| ПВЗ | `pickup_point` | 500 м | 3 | 4.0 |
| Кофейня | `food_service` | 350 м | 4 | 5.0 |
| Пивной магазин / бар | `food_service` | 450 м | 3 | 5.0 |
| Аптека | `convenience_retail` | 500 м | 4 | 5.5 |
| Продуктовый магазин | `convenience_retail` | 450 м | 5 | 7.0 |
| Фастфуд | `food_service` | 400 м | 4 | 6.0 |
| Ресторан / кафе | `food_service` | 500 м | 4 | 6.0 |
| Красота / барбершоп / маникюр | `personal_service` | 450 м | 4 | 5.5 |
| Клиника / стоматология | `destination_service` | 700 м | 3 | 4.0 |
| Автосервис | `destination_service` | 800 м | 3 | 4.0 |

В репозитории лежит 5 `.pkl`, потому что несколько бизнесов используют одно
модельное семейство, а не отдельную модель на каждый пункт списка.

## 7. Сырые POI-счётчики

Для каждой ячейки считаются:

| Поле | Значение |
|---|---|
| `competitors` | конкуренты выбранного бизнеса |
| `shops` | магазины |
| `cafes` | кафе |
| `restaurants` | рестораны, фастфуд, бары и пабы |
| `public_transport` | остановки, станции и входы в метро |
| `offices` | офисы, коммерческие здания, coworking |
| `residential` | жилые здания и жилой landuse |
| `education` | школы, вузы, колледжи, детские сады |
| `nearby_poi_total` | все найденные POI в радиусе |

Конкурент определяется по:

- точному совпадению OSM-тега профиля;
- значению тега из списка профиля;
- ключевым словам в `name`, `brand`, `operator`, `branch`, `description`.

## 8. Нормализация признаков

Большинство счётчиков преобразуются функцией насыщения:

```text
saturating_count(count, scale) = 1 - exp(-count / scale)
```

Она ограничена диапазоном `[0; 1]`. Поэтому десятый одинаковый объект влияет
меньше первого: модель не должна бесконечно повышать score только из-за
огромного количества POI.

Основные признаки:

```text
residential_score = saturating_count(residential, 8)
transport_score = saturating_count(public_transport, 3)
retail_anchor_score = saturating_count(shops + cafes + restaurants, 12)
office_score = saturating_count(offices, 7)
education_score = saturating_count(education, 4)
density_score = saturating_count(nearby_poi_total, 25)
```

### Трафик-потенциал

Реального автомобильного или пешеходного трафика сейчас нет.
`traffic_potential` — proxy-оценка окружения:

```text
0.28 * transport_score
+ 0.20 * retail_anchor_score
+ 0.18 * residential_score
+ 0.14 * office_score
+ 0.10 * education_score
+ 0.10 * density_score
```

### Конкуренция

```text
norm_competition =
    saturating_count(competitors, profile.competition_scale)

competition_penalty =
    saturating_count(max(0, competitors - soft_limit), 2)

market_validation =
    clamp(competitors / validation_competitor_count)
```

То есть небольшое число конкурентов может подтверждать наличие спроса через
`market_validation`. После `soft_limit` начинает быстро расти отрицательный
`competition_penalty`.

## 9. Proxy-таргет обучения

Текущий target не является фактической успешностью бизнеса.

```text
target_success = clamp(0.18 + сумма(feature * business_weight))
```

### Веса ПВЗ

| Признак | Вес |
|---|---:|
| жилая плотность | +0.24 |
| транспорт | +0.19 |
| торговые якоря | +0.16 |
| общая плотность POI | +0.12 |
| офисы | +0.10 |
| подтверждение рынка конкурентами | +0.10 |
| образование | +0.05 |
| перенасыщение конкурентами | -0.20 |
| нормализованная конкуренция | -0.05 |

### Веса модельных семейств

| Семейство | Главные положительные факторы | Штраф перенасыщения |
|---|---|---:|
| `food_service` | трафик 0.24, торговые якоря 0.21, плотность 0.16 | -0.18 |
| `convenience_retail` | жильё 0.22, торговые якоря 0.18, транспорт 0.16 | -0.17 |
| `personal_service` | транспорт 0.20, жильё 0.18, торговые якоря 0.15 | -0.16 |
| `destination_service` | транспорт 0.22, жильё 0.16, офисы 0.12 | -0.14 |

Полные веса находятся в `geopredict_ml/business.py`.

## 10. Алгоритм модели

Используется собственный регрессионный алгоритм:

```text
GradientBoostingRegressorLite
```

Параметры по умолчанию:

| Параметр | Значение |
|---|---:|
| количество деревьев-пней | 48 |
| learning rate | 0.12 |
| максимум порогов признака | 12 |
| начальный прогноз | среднее target |

Каждый базовый алгоритм — decision stump: один признак, один порог, значение
слева и справа. На каждой итерации stump приближает остаточную ошибку.

Модель — регрессия, не классификация и не Random Forest.

Она не обучается после каждого пользовательского анализа. Запросы пользователей
не записываются в обучающий датасет и не меняют `.pkl`.

## 11. Итоговый score для карты

### Уверенность данных

```text
data_confidence =
    0.36 * density_score
  + 0.18 * traffic_potential
  + 0.15 * residential_score
  + 0.12 * transport_score
  + 0.11 * retail_anchor_score
  + 0.08 * saturating_count(nearby_poi_total, 12)
```

### Базовая оценка

```text
base_score =
    0.34 * model_score
  + 0.18 * traffic_potential
  + 0.16 * residential_score
  + 0.13 * retail_anchor_score
  + 0.10 * density_score
  + 0.06 * transport_score
  + 0.03 * office_score
```

### Штрафы

```text
saturation_penalty =
    0.16 * competition_penalty
  + 0.08 * max(0, norm_competition - 0.55)

uncertainty_penalty =
    0.20 * (1 - data_confidence)

weak_signal_penalty =
    0.06, если traffic + residential + retail < 0.55
    0.00 в остальных случаях
```

### Финальная формула

```text
selection_score = clamp(
    base_score
    - saturation_penalty
    - uncertainty_penalty
    - weak_signal_penalty
)
```

Именно `selection_score` определяет цвет, процент пригодности и место участка.

## 12. Как определяется место

Ячейки сортируются по:

1. `selection_score` — выше лучше;
2. `data_confidence` — выше лучше;
3. `traffic_potential` — выше лучше;
4. `residential_score` — выше лучше;
5. `competition_penalty` — ниже лучше;
6. `h3_id` — технический стабильный tie-breaker.

`rank=1` означает лучшую ячейку только внутри текущей выбранной территории.
Ранг нельзя напрямую сравнивать между двумя анализами разного размера.

`top_percentile` сейчас считается как:

```text
rank / total_candidates
```

## 13. Пороги рекомендаций

```text
high_priority_limit = max(3, ceil(total_cells * 0.02))
promising_limit = max(10, ceil(total_cells * 0.18))
```

| Рекомендация | Условия |
|---|---|
| Приоритетно | score ≥ 0.70, confidence ≥ 0.30, место входит в верхние 2%, минимум топ-3 |
| Перспективно | score ≥ 0.54, confidence ≥ 0.22, место входит в верхние 18%, минимум топ-10 |
| Ручная проверка | score ≥ 0.34 и confidence ≥ 0.12 |
| Низкий приоритет | всё остальное |
| Недостаточно данных | список POI пуст |

Высокий процент сам по себе не гарантирует зелёную категорию: учитывается также
относительный ранг и уверенность данных.

## 14. Пользовательский бизнес

При `business_type="custom_osm"` обязательно поле `business_query`.

Система:

1. нормализует строку;
2. выделяет слова длиной от трёх символов;
3. применяет словарь подсказок для популярных категорий;
4. ищет совпадения в OSM-тегах, названии, бренде и описании;
5. использует радиус 500 м;
6. использует веса и модель семейства `convenience_retail`.

Это приближение. Для неизвестного бизнеса нет отдельной обученной модели и
профессионально настроенных весов.

## 15. Источники и состояние данных

| `data_status` | Значение |
|---|---|
| `live` | свежий ответ Overpass |
| `cached` | OSM-кэш или просроченный fallback-кэш |
| `mock` | явно запрошенный sample-набор |
| `insufficient` | POI отсутствуют |

Кэш живёт 24 часа. Если live Overpass недоступен, backend пробует второй
endpoint, затем просроченный кэш. Если ничего нет, API возвращает HTTP `503`
с кодом `osm_unavailable`.

Mock включается только явно через `data_mode="mock"`, работает только для ПВЗ
и только в области bundled demo-полигона Москвы.

## 16. Метрики качества модели

Поддерживаются:

- `MAE`;
- `MSE`;
- `RMSE`;
- median absolute error;
- max error;
- bias;
- `MAPE`;
- `R²`;
- baseline по среднему target.

Команда:

```bash
cd /Users/guguk/Documents/ml_here
python3 -m scripts.evaluate_model \
  --dataset data/processed/pvz_features.csv \
  --model models/geopredict_pickup_point_v1.pkl
```

Holdout:

```bash
python3 -m scripts.evaluate_model \
  --dataset data/processed/pvz_features.csv \
  --fit-holdout \
  --test-size 0.25 \
  --seed 42
```

### Текущий sample-результат

Артефакт на 12 строках:

| Метрика | Значение |
|---|---:|
| MAE | 0.0732 |
| RMSE | 0.0874 |
| MAPE | 19.65% |
| R² | -0.952 |

Baseline по среднему:

| Метрика | Значение |
|---|---:|
| MAE | 0.0470 |
| RMSE | 0.0626 |
| R² | 0.0 |

Baseline на этом наборе лучше модели. Причины:

- всего 12 строк;
- target синтетический;
- dataset не представляет разные города, даты и рыночные условия;
- артефакт обучался на reference-сетке, а не на истории реальных открытий.

Эти метрики проверяют техническую воспроизводимость proxy-формулы, но не
доказывают бизнес-эффективность.

## 17. Что модель пока не учитывает

- фактическую выручку и прибыль;
- аренду и стоимость помещения;
- реальный пешеходный и автомобильный трафик;
- демографию и доход населения;
- этажность и количество квартир;
- парковки и точные маршруты пешей доступности;
- рейтинг, отзывы и время работы конкурентов;
- историю открытий и закрытий;
- сезонность;
- юридические ограничения;
- площадь и состояние помещения;
- каннибализацию собственной сети;
- качество и полноту OSM-разметки.

## 18. Критические ограничения интерпретации

1. `suitability=90%` не означает 90% вероятности успеха.
2. Ранг относителен выбранному полигону.
3. Мало OSM-объектов означает низкую уверенность, а не обязательно плохой район.
4. Конкуренты одновременно подтверждают спрос и создают штраф после soft limit.
5. H3 влияет на детализацию, число кандидатов и относительный рейтинг.
6. Кэш может содержать данные возрастом до 24 часов, stale fallback — старше.
7. Пользовательский тип бизнеса использует общий fallback-профиль.
8. Модель не становится лучше от обычных запросов.
9. PostgreSQL используется auth-сервисом; ML API своей базы данных не имеет.
10. Для реальной валидации необходим исторический target: открылась ли точка,
    работала ли через N месяцев, выручка, заказы или другой измеримый результат.

## 19. Главные файлы реализации

| Логика | Файл |
|---|---|
| Полный pipeline | `geopredict_ml/pipeline.py` |
| POI и признаки | `geopredict_ml/features.py` |
| Бизнес-профили и веса | `geopredict_ml/business.py` |
| Proxy-target | `geopredict_ml/target.py` |
| Gradient Boosting | `geopredict_ml/model.py` |
| Registry моделей | `geopredict_ml/model_registry.py` |
| H3 и лимиты | `geopredict_ml/grid.py` |
| OSM/Overpass и кэш | `geopredict_ml/osm.py` |
| Объяснения | `geopredict_ml/explain.py` |
| Метрики | `geopredict_ml/metrics.py` |
| Оценка модели | `geopredict_ml/evaluation.py` |
| FastAPI | `api/analyze.py` |
| Docker-стек | `docker-compose.full.yml` |
