# GitHub Secrets Configuration

Para que el workflow de deployment funcione correctamente, necesitas configurar los siguientes secrets en tu repositorio de GitHub.

## Cómo Configurar Secrets

1. Ve a tu repositorio en GitHub: https://github.com/rhernandezbas/ubiquiti__lmm
2. Click en **Settings** (Configuración)
3. En el menú lateral, click en **Secrets and variables** → **Actions**
4. Click en **New repository secret**
5. Agrega cada uno de los siguientes secrets:

## Secrets Requeridos

### 🖥️ VPS Configuration

| Secret Name | Description | Example |
|------------|-------------|---------|
| `VPS_HOST` | IP o dominio del VPS | `190.7.234.37` |
| `VPS_USERNAME` | Usuario SSH del VPS | `root` |
| `VPS_PASSWORD` | Contraseña SSH del VPS | `tu_password_seguro` |

### 🌐 UISP Configuration

| Secret Name | Description | Example |
|------------|-------------|---------|
| `UISP_BASE_URL` | URL base de UISP | `https://190.7.234.36` |
| `UISP_TOKEN` | Token de autenticación UISP | `tu_token_uisp` |

### 🔐 SSH Configuration

| Secret Name | Description | Example |
|------------|-------------|---------|
| `UBIQUITI_SSH_USERNAME` | Usuario SSH de dispositivos Ubiquiti | `ubnt` |
| `UBIQUITI_SSH_PASSWORD` | Contraseña SSH de dispositivos Ubiquiti | `ubnt` |

### 🤖 OpenAI Configuration

| Secret Name | Description | Example |
|------------|-------------|---------|
| `OPENAI_API_KEY` | API Key de OpenAI | `sk-...` |

## Verificación

Una vez configurados todos los secrets, el workflow se ejecutará automáticamente cuando:

1. **Push a main**: Cada vez que hagas push a la rama `main`
2. **Manual**: Desde la pestaña "Actions" → "Deploy Ubiquiti LLM API to VPS" → "Run workflow"

## Deployment Flow

El workflow realizará las siguientes acciones:

1. ✅ Verificar e instalar Docker en el VPS
2. ✅ Clonar o actualizar el repositorio en `/opt/ubiquiti-llm`
3. ✅ Crear archivo `.env` con los secrets configurados
4. ✅ Construir la imagen Docker
5. ✅ Levantar el contenedor
6. ✅ Verificar que el servicio esté funcionando

## URLs del Servicio

Una vez desplegado, el servicio estará disponible en:

- **API**: `http://VPS_HOST:8000`
- **Documentación**: `http://VPS_HOST:8000/docs`
- **Health Check**: `http://VPS_HOST:8000/health`
- **Endpoint Principal**: `http://VPS_HOST:8000/api/v1/analyze-device-complete`

## Troubleshooting

Si el deployment falla:

1. Verifica que todos los secrets estén configurados correctamente
2. Revisa los logs del workflow en la pestaña "Actions"
3. Conéctate al VPS y verifica los logs:
   ```bash
   cd /opt/ubiquiti-llm
   docker compose logs -f
   ```

## Notas de Seguridad

- ⚠️ **NUNCA** commits los valores de los secrets en el código
- ⚠️ Los secrets se inyectan automáticamente en el archivo `.env` durante el deployment
- ⚠️ El archivo `.env` está en `.gitignore` y no se sube al repositorio
