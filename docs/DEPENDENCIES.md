# GeoPredict Dependencies

Документ фиксирует прямые библиотеки, рантаймы и внешние сервисы, которые сейчас используются в общем проекте:

- `/Users/guguk/Documents/ml_here` — ML backend.
- `/Users/guguk/Documents/express-auth-service` — auth API.
- `/Users/guguk/Documents/geo_mark_front` — frontend.

## ML Backend

Папка: `/Users/guguk/Documents/ml_here`

### Python Packages

Из `requirements.txt`:

```text
numpy >=1.24
pandas >=2.0
pydantic >=2.0
h3 >=4.0
fastapi >=0.110
uvicorn >=0.27
```

### Python Standard Library

```text
argparse
csv
dataclasses
hashlib
itertools
json
math
os
pathlib
pickle
random
re
statistics
tempfile
typing
unicodedata
unittest
urllib.parse
urllib.request
```

### ML / Geo

```text
GradientBoostingRegressorLite
pickle .pkl model artifacts
GeoJSON
H3 grid
OSM POI data
Overpass API
proxy target_success
MAE / RMSE / R2 evaluation metrics
```

### Backend Infrastructure

```text
FastAPI
Swagger / OpenAPI
Uvicorn
Docker
Docker Compose
Python 3.11 slim
```

## Auth Service

Папка: `/Users/guguk/Documents/express-auth-service`

### Node Packages

Из `package.json`:

```text
bcrypt ^6.0.0
cookie-parser ^1.4.7
cors ^2.8.6
dotenv ^17.3.1
express ^5.2.1
express-validator ^7.3.1
js-yaml ^4.1.1
jsonwebtoken ^9.0.3
pg ^8.19.0
sequelize ^6.37.8
swagger-ui-express ^5.0.1
uuid ^13.0.0
```

### Dev Packages

```text
nodemon ^3.1.14
```

### Node Standard Library

```text
fs
```

### Auth Infrastructure

```text
Node 20 alpine
Express
PostgreSQL 15 alpine
Sequelize ORM
JWT access tokens
JWT refresh tokens
HTTP cookies
CORS
Swagger UI
```

## Frontend

Папка: `/Users/guguk/Documents/geo_mark_front`

### Runtime Packages

Из `package.json`:

```text
@testing-library/dom ^10.4.1
@testing-library/jest-dom ^6.9.1
@testing-library/react ^16.3.2
@testing-library/user-event ^13.5.0
axios ^1.18.1
copy-webpack-plugin ^14.0.0
html2pdf.js ^0.14.0
jspdf ^4.2.1
leaflet ^1.9.4
leaflet-draw ^1.0.4
react ^19.2.7
react-dom ^19.2.7
react-leaflet ^5.0.0
react-leaflet-draw ^0.21.0
react-router-dom ^7.18.0
react-scripts 5.0.1
sass ^1.101.0
web-vitals ^2.1.4
webpack ^5.107.2
```

### Dev Packages

```text
@babel/core ^7.24.0
@babel/preset-env ^7.24.0
@babel/preset-react ^7.23.3
@types/leaflet ^1.9.21
babel-loader ^9.1.3
css-loader ^6.10.0
css-minimizer-webpack-plugin ^6.0.0
html-webpack-plugin ^5.6.0
mini-css-extract-plugin ^2.8.0
sass ^1.101.0
sass-loader ^14.1.0
style-loader ^3.3.4
terser-webpack-plugin ^5.3.10
webpack ^5.107.2
webpack-cli ^7.0.3
webpack-dev-server ^5.0.0
```

### Frontend Infrastructure

```text
Node 18 alpine
Webpack
Webpack Dev Server
React
React Router
Axios API client
Leaflet map
Leaflet Draw
SCSS modules
PDF export
```

## Full Local Stack

Файл запуска: `/Users/guguk/Documents/ml_here/docker-compose.full.yml`

```text
geopredict-api    FastAPI ML backend, port 8000
auth-db           PostgreSQL, port 5432
auth-app          Express auth API, port 8001
geo-mark-front    React frontend, port 3000
```

### Main URLs

```text
Frontend:    http://localhost:3000
ML Swagger:  http://localhost:8000/docs
Auth Swagger: http://localhost:8001/api-docs/
```

### Main Environment Variables

```text
API_BASE_URL=http://localhost:8000
AUTH_API_URL=http://localhost:8001/api
GEOPREDICT_CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

## Notes

Этот файл перечисляет прямые зависимости и основные системные компоненты проекта. Транзитивные npm-зависимости находятся в `package-lock.json` соответствующих Node-проектов.
