#!/usr/bin/env python3
"""
Script para crear tareas de seguimiento de nodos en Splynx
"""
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UISP_API_URL = "https://190.7.234.36/nms/api/v2.1"
UISP_TOKEN = "cb53a0bc-48e8-480c-aa47-19e1042e4897"

SPLYNX_API_URL = "https://splynx.ipnext.com.ar/api/2.0"
SPLYNX_KEY = "a69232229bf7a86e1a4acab4ac4700a2"
SPLYNX_SECRET = "725a72d2368530ee73c079a54d43c6e3"

PROJECT_ID = 26  # Proyecto NOC


def get_uisp_sites() -> List[Dict]:
    """Obtiene todos los sites desde UISP"""
    headers = {
        'X-Auth-Token': UISP_TOKEN,
        'Accept': 'application/json'
    }
    response = requests.get(
        f"{UISP_API_URL}/sites",
        headers=headers,
        verify=False
    )
    response.raise_for_status()
    return response.json()


def extract_node_info(site: Dict) -> Dict:
    """Extrae información relevante del nodo desde UISP"""
    identification = site.get('identification', {})
    description = site.get('description', {})
    contact = description.get('contact', {})
    location = description.get('location', {})
    note = description.get('note', '')
    
    # Analizar notas para extraer información
    note_lower = note.lower() if note else ''
    has_battery = 'bateria' in note_lower or 'baterias' in note_lower
    needs_coordination = 'coordinar' in note_lower or 'comunicarse' in note_lower
    
    # Determinar tipo de acceso
    if 'ingreso libre' in note_lower:
        access_type = "Ingreso libre"
    elif 'documentación' in note_lower or 'permisos' in note_lower:
        access_type = "Permisos especiales requeridos"
    elif needs_coordination:
        access_type = "Contactar nodo antes de ingresar"
    else:
        access_type = "Por definir"
    
    # Información del nodo padre (vecino)
    parent = identification.get('parent')
    parent_info = f"{parent['name']}" if parent else "Sin nodo padre"
    
    return {
        'id': identification.get('id'),
        'name': identification.get('name'),
        'status': identification.get('status'),
        'contact_name': contact.get('name', 'Sin contacto'),
        'contact_phone': contact.get('phone', 'Sin teléfono'),
        'contact_email': contact.get('email', 'Sin email'),
        'access_type': access_type,
        'has_battery': has_battery,
        'battery_duration': 'Por definir' if has_battery else 'N/A',
        'cooperative': 'Por definir',
        'parent_node': parent_info,
        'recovery_ap': 'Por definir',
        'guard_criteria': 'Por definir',
        'guard_schedule': 'Por definir',
        'device_count': description.get('deviceCount', 0),
        'location': location,
        'notes': note,
        'gps': f"{location.get('latitude', '')},{location.get('longitude', '')}" if location else ""
    }


def create_task_description(node_info: Dict) -> str:
    """Crea la descripción de la tarea con la información del nodo"""
    desc = f"""<h3>Template de Seguimiento - {node_info['name']}</h3>

<h4>📋 INFORMACIÓN DE CONTACTO</h4>
<ul>
<li><strong>Contacto:</strong> Por definir</li>
<li><strong>Teléfono:</strong> Por definir</li>
<li><strong>Email:</strong> Por definir</li>
</ul>

<h4>🚪 ACCESO AL NODO</h4>
<ul>
<li><strong>Tipo de acceso:</strong> Por definir (Ingreso libre / Contactar nodo / Permisos especiales)</li>
</ul>

<h4>🔋 ENERGÍA</h4>
<ul>
<li><strong>Tiene baterías:</strong> Por definir (Sí/No)</li>
<li><strong>Duración estimada:</strong> Por definir</li>
</ul>

<h4>🏢 COOPERATIVA</h4>
<ul>
<li><strong>Nombre:</strong> Por definir</li>
<li><strong>Teléfono:</strong> Por definir</li>
</ul>

<h4>🔗 CONECTIVIDAD</h4>
<ul>
<li><strong>Nodo vecino para recuperación:</strong> Por definir</li>
<li><strong>AP que se puede utilizar:</strong> Por definir</li>
</ul>

<h4>👮 CRITERIOS GUARDIA</h4>
<ul>
<li><strong>Se manda guardia solo si:</strong> Por definir</li>
<li><strong>Horarios permitidos:</strong> Por definir</li>
</ul>

<hr>

<h4>📊 INFO ACTUAL (UISP)</h4>
<ul>
<li><strong>Dispositivos:</strong> {node_info['device_count']}</li>
<li><strong>Status:</strong> {node_info['status']}</li>
<li><strong>GPS:</strong> {node_info['gps']}</li>
</ul>

<h4>📝 Ver notas completas en UISP</h4>

<hr>

<h4>✅ TAREAS PENDIENTES</h4>
<ul>
<li>Completar información de contacto</li>
<li>Definir tipo de acceso</li>
<li>Verificar y documentar baterías</li>
<li>Identificar cooperativa (si aplica)</li>
<li>Definir nodo vecino y AP de respaldo</li>
<li>Establecer criterios y horarios de guardia</li>
<li>Verificar GPS de todos los APs del nodo</li>
<li>Identificar APs saturados (+20-30 clientes)</li>
<li>Corregir mapa de interconexión en UISP</li>
<li>Documentar equipos auxiliares (EPS, Switch, Monitor, Rectificador)</li>
</ul>
"""
    return desc


def create_splynx_task(node_info: Dict) -> Dict:
    """Crea una tarea en Splynx para el nodo"""
    headers = {
        'Content-Type': 'application/json',
    }
    
    task_data = {
        "title": node_info['name'],
        "description": create_task_description(node_info),
        "address": f"GPS: {node_info['gps']}" if node_info['gps'] else "Sin ubicación",
        "gps": node_info['gps'] if node_info['gps'] else None,
        "partner_id": 1,
        "project_id": PROJECT_ID,
        "priority": "priority_medium",
        "workflow_status_id": 4,
        "is_archived": 0,
        "is_scheduled": False,
        "reporter_id": 1
    }
    
    # Basic Auth: API Key como username, Secret como password
    auth = (SPLYNX_KEY, SPLYNX_SECRET)
    
    response = requests.post(
        f"{SPLYNX_API_URL}/admin/scheduling/tasks",
        headers=headers,
        json=task_data,
        auth=auth
    )
    
    return {
        'node_name': node_info['name'],
        'status_code': response.status_code,
        'success': response.status_code in [200, 201],
        'response': response.json() if response.status_code in [200, 201] else response.text
    }


def main():
    """Función principal"""
    print("🚀 Iniciando creación de tareas NOC en Splynx...")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Obtener sites desde UISP
    print("📡 Obteniendo sites desde UISP...")
    sites = get_uisp_sites()
    print(f"✅ {len(sites)} sites obtenidos\n")
    
    # Procesar cada site
    results = []
    success_count = 0
    error_count = 0
    
    for idx, site in enumerate(sites, 1):
        node_info = extract_node_info(site)
        print(f"[{idx}/{len(sites)}] Procesando: {node_info['name']}")
        
        try:
            result = create_splynx_task(node_info)
            results.append(result)
            
            if result['success']:
                print(f"  ✅ Tarea creada exitosamente")
                success_count += 1
            else:
                print(f"  ❌ Error: {result['status_code']} - {result['response']}")
                error_count += 1
                
        except Exception as e:
            print(f"  ❌ Excepción: {str(e)}")
            error_count += 1
            results.append({
                'node_name': node_info['name'],
                'success': False,
                'error': str(e)
            })
    
    # Resumen
    print("\n" + "="*60)
    print("📊 RESUMEN DE EJECUCIÓN")
    print("="*60)
    print(f"Total de nodos procesados: {len(sites)}")
    print(f"✅ Tareas creadas exitosamente: {success_count}")
    print(f"❌ Errores: {error_count}")
    print("="*60)
    
    # Guardar resultados
    with open('/tmp/splynx_tasks_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    print("\n💾 Resultados guardados en: /tmp/splynx_tasks_results.json")


if __name__ == "__main__":
    main()
