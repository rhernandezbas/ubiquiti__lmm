# UISP Diagnostic Service

Servicio de diagnóstico inteligente para dispositivos Ubiquiti UISP utilizando LLM (Large Language Models).

## 🏗️ Arquitectura

Este proyecto utiliza **Arquitectura Hexagonal** (Ports and Adapters) para mantener el código limpio, testeable y desacoplado:

```
app/
├── domain/              # Capa de dominio (lógica de negocio)
│   ├── entities/        # Entidades del dominio
│   ├── repositories/    # Interfaces de repositorios
│   └── services/        # Servicios de dominio
│
├── infrastructure/      # Capa de infraestructura (implementaciones)
│   ├── api/            # Clientes de APIs externas (UISP)
│   ├── llm/            # Integración con LLM (OpenAI)
│   └── repositories/   # Implementaciones de repositorios
│
├── application/         # Capa de aplicación (casos de uso)
│   └── services/       # Servicios de aplicación
│
├── interfaces/          # Capa de interfaces (API REST)
│   └── api/
│       └── v1/
│           └── endpoints/
│
├── config/             # Configuración
│   ├── settings.py
│   └── logging_config.py
│
└── utils/              # Utilidades
    ├── patterns.py     # Patrones de diagnóstico
    └── dependencies.py # Inyección de dependencias
```

## 🚀 Características

- ✅ **Diagnóstico Inteligente**: Utiliza GPT-4 para analizar dispositivos UISP
- ✅ **Patrones Predefinidos**: Sistema de patrones para detección rápida de problemas comunes
- ✅ **API REST**: Endpoints bien documentados con FastAPI
- ✅ **Logging Avanzado**: Sistema de logs con rotación y niveles configurables
- ✅ **Arquitectura Limpia**: Separación de responsabilidades y fácil testing
- ✅ **Async/Await**: Operaciones asíncronas para mejor rendimiento

## 📋 Requisitos

- Python 3.9+
- Cuenta de UISP con API token
- API Key de OpenAI

## 🔧 Instalación

1. **Clonar el repositorio**
```bash
cd /Users/rhernandezba/PycharmProjects/ubiquiti_llm
```

2. **Crear entorno virtual**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno**
```bash
cp .env.example .env
# Editar .env con tus credenciales
```

## ⚙️ Configuración

Edita el archivo `.env` con tus credenciales:

```env
DEBUG=True
ENVIRONMENT=development
LOG_LEVEL=INFO

UISP_BASE_URL=https://your-uisp-instance.com
UISP_TOKEN=your_uisp_api_token

OPENAI_API_KEY=your_openai_api_key
LLM_MODEL=gpt-4
```

## 🏃 Ejecución

```bash
python main.py
```

El servidor estará disponible en: `http://localhost:8000`

## 📚 API Endpoints

### Health Check
```
GET /health
```

### Dispositivos

**Listar todos los dispositivos**
```
GET /api/v1/devices
```

**Obtener un dispositivo específico**
```
GET /api/v1/devices/{device_id}
```

### Diagnósticos

**Ejecutar diagnóstico en un dispositivo**
```
POST /api/v1/diagnostics/{device_id}?use_patterns=true
```

**Obtener historial de diagnósticos**
```
GET /api/v1/diagnostics/{device_id}/history?limit=10
```

## 📊 Ejemplo de Uso

### Diagnosticar un dispositivo

```bash
curl -X POST "http://localhost:8000/api/v1/diagnostics/device-123?use_patterns=true"
```

Respuesta:
```json
{
  "device_id": "device-123",
  "timestamp": "2026-01-12T22:30:00Z",
  "status": "completed",
  "issues": [
    "High CPU Usage detected",
    "Multiple recent disconnections"
  ],
  "recommendations": [
    "Investigate processes consuming CPU",
    "Check power supply stability"
  ],
  "confidence": 0.92,
  "patterns_matched": [
    "High CPU Usage",
    "Frequent Disconnections"
  ]
}
```

## 🧪 Testing

```bash
pytest tests/
```

## 📝 Patrones de Diagnóstico

El sistema incluye patrones predefinidos para detectar:

- 🔴 **Alto uso de CPU** (>80%)
- 🔴 **Alto uso de memoria** (>85%)
- 🟡 **Errores en interfaces de red**
- 🔴 **Alta pérdida de paquetes** (>5%)
- 🔴 **Desconexiones frecuentes**
- 🟡 **Señal débil** (<-70 dBm)
- 🟢 **Firmware desactualizado**
- 🔴 **Temperatura elevada** (>70°C)

## 🔍 Logging

Los logs se guardan en:
- `logs/app.log` - Logs generales
- `logs/error.log` - Solo errores

## 🛠️ Desarrollo

### Agregar nuevos patrones

Edita `app/utils/patterns.py`:

```python
{
    "name": "Nuevo Patrón",
    "description": "Descripción del problema",
    "severity": "high",
    "check": lambda stats: stats.get("metric", 0) > threshold,
    "recommendation": "Acción recomendada"
}
```

### Agregar nuevos endpoints

1. Crear archivo en `app/interfaces/api/v1/endpoints/`
2. Registrar en `app/interfaces/api/v1/api.py`

## 📄 Licencia

MIT

## 👥 Contribuciones

Las contribuciones son bienvenidas. Por favor:
1. Fork el proyecto
2. Crea una rama para tu feature
3. Commit tus cambios
4. Push a la rama
5. Abre un Pull Request

## 📞 Soporte

Para problemas o preguntas, abre un issue en el repositorio.
