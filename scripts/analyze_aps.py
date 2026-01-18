#!/usr/bin/env python3
"""
Script para analizar APs: GPS faltante y saturación de clientes
"""
import json
import requests
import pandas as pd
from typing import Dict, List
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

UISP_API_URL = "https://190.7.234.36/nms/api/v2.1"
UISP_TOKEN = "cb53a0bc-48e8-480c-aa47-19e1042e4897"

CLIENT_THRESHOLD_WARNING = 20
CLIENT_THRESHOLD_CRITICAL = 30


def get_uisp_devices() -> List[Dict]:
    """Obtiene todos los dispositivos desde UISP"""
    headers = {
        'X-Auth-Token': UISP_TOKEN,
        'Accept': 'application/json'
    }
    response = requests.get(
        f"{UISP_API_URL}/devices",
        headers=headers,
        verify=False
    )
    response.raise_for_status()
    return response.json()


def get_uisp_sites() -> Dict[str, str]:
    """Obtiene mapeo de site ID a nombre"""
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
    sites = response.json()
    return {site['id']: site['identification']['name'] for site in sites}


def analyze_devices(devices: List[Dict], sites_map: Dict[str, str]) -> tuple:
    """Analiza dispositivos para encontrar APs sin GPS y saturados"""
    aps_without_gps = []
    saturated_aps = []
    
    for device in devices:
        identification = device.get('identification', {})
        overview = device.get('overview', {})
        location = device.get('location', {})
        
        device_type = identification.get('type', '')
        device_role = identification.get('role', '')
        device_name = identification.get('name', 'Sin nombre')
        device_model = identification.get('model', 'Sin modelo')
        
        # Obtener site info
        site_info = identification.get('site')
        if site_info:
            site_id = site_info.get('id')
        else:
            site_id = None
        site_name = sites_map.get(site_id, 'Sin sitio asignado') if site_id else 'Sin sitio asignado'
        
        # Filtrar solo APs (Access Points) - usar role='ap'
        if device_role != 'ap':
            continue
        
        # Verificar GPS
        if location:
            latitude = location.get('latitude')
            longitude = location.get('longitude')
            has_gps = latitude is not None and longitude is not None
        else:
            latitude = None
            longitude = None
            has_gps = False
        
        # Obtener cantidad de clientes
        client_count = overview.get('stationsCount', 0) or 0
        
        # AP sin GPS
        if not has_gps:
            aps_without_gps.append({
                'Nodo': site_name,
                'Dispositivo': device_name,
                'Modelo': device_model,
                'Tipo': device_type,
                'IP': identification.get('ipAddress', 'N/A'),
                'MAC': identification.get('mac', 'N/A'),
                'Estado': identification.get('status', 'unknown'),
                'Clientes': client_count
            })
        
        # AP saturado
        if client_count >= CLIENT_THRESHOLD_WARNING:
            severity = 'CRÍTICO' if client_count >= CLIENT_THRESHOLD_CRITICAL else 'ADVERTENCIA'
            saturated_aps.append({
                'Nodo': site_name,
                'Dispositivo': device_name,
                'Modelo': device_model,
                'Tipo': device_type,
                'IP': identification.get('ipAddress', 'N/A'),
                'Clientes Conectados': client_count,
                'Severidad': severity,
                'Estado': identification.get('status', 'unknown'),
                'GPS': f"{latitude},{longitude}" if has_gps else 'Sin GPS'
            })
    
    return aps_without_gps, saturated_aps


def generate_excel_report(aps_without_gps: List[Dict], saturated_aps: List[Dict], output_file: str):
    """Genera reporte Excel con múltiples hojas"""
    
    with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
        # Hoja 1: APs sin GPS
        if aps_without_gps:
            df_no_gps = pd.DataFrame(aps_without_gps)
            df_no_gps = df_no_gps.sort_values(['Nodo', 'Dispositivo'])
            df_no_gps.to_excel(writer, sheet_name='APs sin GPS', index=False)
        
        # Hoja 2: APs saturados
        if saturated_aps:
            df_saturated = pd.DataFrame(saturated_aps)
            df_saturated = df_saturated.sort_values(['Severidad', 'Clientes Conectados'], ascending=[True, False])
            df_saturated.to_excel(writer, sheet_name='APs Saturados', index=False)
        
        # Hoja 3: Resumen por nodo
        if aps_without_gps:
            df_no_gps = pd.DataFrame(aps_without_gps)
            summary_no_gps = df_no_gps.groupby('Nodo').size().reset_index(name='APs sin GPS')
        else:
            summary_no_gps = pd.DataFrame(columns=['Nodo', 'APs sin GPS'])
        
        if saturated_aps:
            df_saturated = pd.DataFrame(saturated_aps)
            summary_saturated = df_saturated.groupby('Nodo').size().reset_index(name='APs Saturados')
        else:
            summary_saturated = pd.DataFrame(columns=['Nodo', 'APs Saturados'])
        
        summary = pd.merge(summary_no_gps, summary_saturated, on='Nodo', how='outer').fillna(0)
        summary['APs sin GPS'] = summary['APs sin GPS'].astype(int)
        summary['APs Saturados'] = summary['APs Saturados'].astype(int)
        summary = summary.sort_values('Nodo')
        summary.to_excel(writer, sheet_name='Resumen por Nodo', index=False)
    
    print(f"✅ Reporte Excel generado: {output_file}")


def main():
    """Función principal"""
    print("🔍 Iniciando análisis de APs...\n")
    
    # Obtener datos
    print("📡 Obteniendo dispositivos desde UISP...")
    devices = get_uisp_devices()
    print(f"✅ {len(devices)} dispositivos obtenidos")
    
    print("📡 Obteniendo sites desde UISP...")
    sites_map = get_uisp_sites()
    print(f"✅ {len(sites_map)} sites obtenidos\n")
    
    # Analizar
    print("🔍 Analizando APs...")
    aps_without_gps, saturated_aps = analyze_devices(devices, sites_map)
    
    # Resultados
    print("\n" + "="*60)
    print("📊 RESULTADOS DEL ANÁLISIS")
    print("="*60)
    print(f"🚨 APs sin GPS: {len(aps_without_gps)}")
    print(f"⚠️  APs saturados (≥{CLIENT_THRESHOLD_WARNING} clientes): {len(saturated_aps)}")
    
    if saturated_aps:
        critical = sum(1 for ap in saturated_aps if ap['Severidad'] == 'CRÍTICO')
        warning = len(saturated_aps) - critical
        print(f"   - CRÍTICO (≥{CLIENT_THRESHOLD_CRITICAL} clientes): {critical}")
        print(f"   - ADVERTENCIA ({CLIENT_THRESHOLD_WARNING}-{CLIENT_THRESHOLD_CRITICAL-1} clientes): {warning}")
    
    print("="*60 + "\n")
    
    # Generar Excel en carpeta scripts
    import os
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_file = os.path.join(script_dir, 'analisis_aps_uisp.xlsx')
    json_file = os.path.join(script_dir, 'analisis_aps_uisp.json')
    
    generate_excel_report(aps_without_gps, saturated_aps, output_file)
    
    # Guardar JSON también
    results = {
        'aps_without_gps': aps_without_gps,
        'saturated_aps': saturated_aps,
        'summary': {
            'total_aps_without_gps': len(aps_without_gps),
            'total_saturated_aps': len(saturated_aps),
            'critical_aps': sum(1 for ap in saturated_aps if ap['Severidad'] == 'CRÍTICO'),
            'warning_aps': sum(1 for ap in saturated_aps if ap['Severidad'] == 'ADVERTENCIA')
        }
    }
    
    with open(json_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print("💾 Resultados guardados en:")
    print(f"   - Excel: {output_file}")
    print(f"   - JSON: {json_file}")
    
    # Mostrar top 10 APs más saturados
    if saturated_aps:
        print("\n" + "="*60)
        print("🔥 TOP 10 APs MÁS SATURADOS")
        print("="*60)
        sorted_aps = sorted(saturated_aps, key=lambda x: x['Clientes Conectados'], reverse=True)[:10]
        for idx, ap in enumerate(sorted_aps, 1):
            print(f"{idx}. {ap['Dispositivo']} ({ap['Nodo']}) - {ap['Clientes Conectados']} clientes - {ap['Severidad']}")
        print("="*60)


if __name__ == "__main__":
    main()
