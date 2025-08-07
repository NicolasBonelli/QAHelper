# QAHelper API

Esta es la documentación de la API reorganizada siguiendo las mejores prácticas de FastAPI.

## Estructura de Carpetas

```
backend/
├── api/
│   ├── __init__.py
│   ├── config.py          # Configuraciones centralizadas
│   ├── s3_routes.py       # Rutas para operaciones S3
│   ├── chat_routes.py     # Rutas para el chat del agente
│   ├── files_routes.py    # Rutas para gestión de archivos PDF
│   └── README.md          # Esta documentación
├── main.py                # Aplicación principal FastAPI
└── ...
```

## Endpoints Disponibles

### S3 Operations (`/s3`)

- `POST /s3/upload` - Sube texto a S3
- `POST /s3/process` - Procesa archivos en S3
- `GET /s3/health` - Verifica conectividad con S3

### Chat Agent (`/chat`)

- `POST /chat/send` - Envía mensaje al agente
- `POST /chat/session/new` - Crea nueva sesión
- `GET /chat/session/{session_id}` - Obtiene información de sesión
- `DELETE /chat/session/{session_id}` - Elimina sesión
- `GET /chat/health` - Verifica estado del chat

### File Management (`/files`)

- `POST /files/upload` - Sube archivo PDF
- `GET /files/list` - Lista archivos PDF
- `GET /files/download/{file_id}` - Descarga archivo PDF
- `DELETE /files/delete/{file_id}` - Elimina archivo PDF
- `GET /files/info/{file_id}` - Obtiene información del archivo
- `GET /files/health` - Verifica estado del almacenamiento

### General

- `GET /` - Endpoint raíz
- `GET /health` - Verificación general de salud
- `GET /docs` - Documentación Swagger
- `GET /redoc` - Documentación ReDoc

## Configuración

Las configuraciones están centralizadas en `api/config.py`:

- Configuraciones de la API (título, descripción, versión)
- Configuraciones de CORS
- Configuraciones de archivos (directorio de almacenamiento)
- Configuraciones de S3 (credenciales, bucket)
- Configuraciones de Gemini
- Configuraciones del servidor (host, port, debug)

## Uso

### Ejecutar el servidor

```bash
cd backend
python main.py
```

O con uvicorn directamente:

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### Documentación automática

Una vez ejecutado el servidor, puedes acceder a:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Mejoras Implementadas

1. **Organización modular**: Separación clara de responsabilidades por recursos
2. **Configuración centralizada**: Todas las configuraciones en un solo lugar
3. **Documentación automática**: FastAPI genera documentación automática
4. **Manejo de errores**: Excepciones HTTP apropiadas
5. **Validación de datos**: Uso de Pydantic para validación
6. **CORS configurado**: Para integración con frontend
7. **Health checks**: Endpoints para monitoreo
8. **Almacenamiento local**: Para archivos PDF sin depender de S3

## Próximos Pasos

1. Implementar autenticación y autorización
2. Agregar logging estructurado
3. Implementar rate limiting
4. Agregar tests unitarios
5. Configurar CI/CD
6. Implementar cache (Redis)
7. Agregar métricas y monitoreo 