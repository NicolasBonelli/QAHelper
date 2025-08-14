# Pipeline CI/CD para QAHelper

## 🚀 Descripción General

Este pipeline de CI/CD está diseñado para automatizar el proceso de desarrollo, testing y deployment de QAHelper. Utiliza GitHub Actions para implementar un flujo de trabajo robusto que incluye testing, linting, security scanning, building y deployment.

## 📋 Estructura del Pipeline

### Jobs Principales

1. **test-and-lint** - Tests y linting
2. **security-scan** - Análisis de seguridad
3. **build-docker** - Construcción de imagen Docker
4. **deploy-staging** - Deployment a staging
5. **deploy-production** - Deployment a producción
6. **performance-test** - Tests de performance

## 🧪 Testing

### Tipos de Tests

#### 1. Tests del Supervisor (`tests/test_supervisor_architecture.py`)
- **Propósito**: Verificar la arquitectura supervisor
- **Cobertura**: Flujo completo del supervisor, agentes, decisiones
- **Ejecución**: `pytest tests/test_supervisor_architecture.py`

### Ejecución Local de Tests

```bash
# Ejecutar todos los tests
./run_tests.sh

# Solo tests unitarios
./run_tests.sh -u

# Tests de integración con cobertura
./run_tests.sh -i -c

# Tests del supervisor en modo verbose
./run_tests.sh -s -v

# Tests de performance
./run_tests.sh -p

# Modo rápido (sin tests lentos)
./run_tests.sh -f
```

### Configuración de Tests

#### pytest.ini
```ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    -v
    --tb=short
    --strict-markers
    --disable-warnings
    --cov=backend
    --cov-report=html:htmlcov
    --cov-report=xml:coverage.xml
    --cov-report=term-missing
    --cov-fail-under=70
```

#### Marcadores de Tests
- `@pytest.mark.slow` - Tests que toman tiempo
- `@pytest.mark.integration` - Tests de integración
- `@pytest.mark.performance` - Tests de performance
- `@pytest.mark.security` - Tests de seguridad
- `@pytest.mark.asyncio` - Tests asíncronos

## 🔒 Security Scanning

### Bandit
- **Propósito**: Análisis estático de seguridad
- **Configuración**: Excluye tests y directorios de desarrollo
- **Reporte**: JSON para análisis posterior

### Safety
- **Propósito**: Verificar vulnerabilidades en dependencias
- **Configuración**: Verifica requirements.txt
- **Reporte**: JSON con vulnerabilidades encontradas

## 🐳 Docker

### Multi-stage Build

#### Stage 1: Builder
```dockerfile
FROM python:3.11-slim as builder
# Instala dependencias de compilación
# Instala dependencias de Python
```

#### Stage 2: Production
```dockerfile
FROM python:3.11-slim as production
# Usuario no-root para seguridad
# Copia dependencias del builder
# Configuración de producción
```

### Optimizaciones
- **Multi-stage build** para reducir tamaño de imagen
- **Usuario no-root** para seguridad
- **Health checks** para monitoreo
- **Cache de capas** para builds más rápidos

## 🚀 Deployment

### Environments

#### Staging
- **Trigger**: Push a branch `develop`
- **Propósito**: Testing de nuevas features
- **URL**: `https://staging.qahelper.com`

#### Production
- **Trigger**: Push a branch `main`
- **Propósito**: Versión estable para usuarios
- **URL**: `https://qahelper.com`

### Docker Compose

```yaml
version: '3.8'
services:
  qahelper:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_DB=qahelper
  
  redis:
    image: redis:7-alpine
```

## 📊 Monitoreo y Métricas

### Health Checks
- **Endpoint**: `/health`
- **Intervalo**: 30 segundos
- **Timeout**: 10 segundos
- **Retries**: 3

### Métricas de Performance
- **Tiempo de respuesta**: < 30 segundos
- **Uso de memoria**: < 200MB
- **Tasa de éxito**: > 80%
- **Requests concurrentes**: < 10

## 🔧 Configuración

### Variables de Entorno Requeridas

```bash
# API Keys
GEMINI_API_KEY=your_gemini_api_key
MODEL=gemini-pro

# AWS
AWS_ACCESS_KEY_ID=your_aws_key
AWS_SECRET_ACCESS_KEY=your_aws_secret
BUCKET_NAME=your_s3_bucket

# Database
DATABASE_URL=postgresql://user:pass@host:port/db
POSTGRES_DB=qahelper
POSTGRES_USER=qahelper
POSTGRES_PASSWORD=your_password

# MCP Server
MCP_RAG_SERVER_URL=http://localhost:8001
```

### Secrets de GitHub

Configurar en Settings > Secrets and variables > Actions:

- `GEMINI_API_KEY`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `BUCKET_NAME`
- `DATABASE_URL`
- `POSTGRES_PASSWORD`

## 📈 Cobertura de Código

### Objetivos
- **Cobertura mínima**: 70%
- **Reportes**: HTML, XML, Terminal
- **Exclusiones**: Tests, archivos de configuración

### Generación de Reportes
```bash
# Con cobertura
pytest --cov=backend --cov-report=html:htmlcov

# Ver reporte
open htmlcov/index.html
```

## 🛠️ Herramientas de Desarrollo

### Linting
- **Black**: Formateo de código
- **Flake8**: Análisis de estilo
- **MyPy**: Type checking

### Comandos Útiles
```bash
# Formatear código
black .

# Verificar estilo
flake8 .

# Type checking
mypy backend/

# Security scan
bandit -r backend/
safety check
```

## 🔄 Flujo de Trabajo

### 1. Desarrollo
```bash
# Crear feature branch
git checkout -b feature/nueva-funcionalidad

# Hacer cambios
# ...

# Ejecutar tests localmente
./run_tests.sh -u -i

# Commit y push
git commit -m "feat: nueva funcionalidad"
git push origin feature/nueva-funcionalidad
```

### 2. Pull Request
- Se ejecuta pipeline automáticamente
- Tests deben pasar
- Cobertura debe ser > 70%
- Security scan debe pasar

### 3. Merge a Develop
- Deploy automático a staging
- Tests de integración
- Performance tests

### 4. Merge a Main
- Deploy automático a producción
- Health checks
- Notificaciones

## 🚨 Troubleshooting

### Tests Fallando
1. Verificar dependencias: `pip install -r requirements.txt`
2. Limpiar cache: `./run_tests.sh --clean`
3. Ejecutar tests específicos: `./run_tests.sh -u -v`

### Build Fallando
1. Verificar Dockerfile
2. Verificar .dockerignore
3. Verificar variables de entorno

### Deployment Fallando
1. Verificar secrets de GitHub
2. Verificar conectividad de red
3. Verificar logs de contenedor

## 📚 Recursos Adicionales

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [pytest Documentation](https://docs.pytest.org/)
- [FastAPI Deployment](https://fastapi.tiangolo.com/deployment/)

## 🤝 Contribución

Para contribuir al pipeline:

1. Crear issue describiendo el problema/mejora
2. Crear branch para la feature
3. Implementar cambios
4. Ejecutar tests localmente
5. Crear Pull Request
6. Esperar review y merge

---

**Nota**: Este pipeline está diseñado para ser robusto y escalable. Cualquier cambio debe ser probado exhaustivamente antes de ser mergeado a main.
