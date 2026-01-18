#!/usr/bin/env python3
"""
Script maestro para configurar seguimiento NOC completo
"""
import sys
import subprocess
from datetime import datetime


def print_header(text: str):
    """Imprime un header formateado"""
    print("\n" + "="*70)
    print(f"  {text}")
    print("="*70 + "\n")


def run_script(script_name: str, description: str) -> bool:
    """Ejecuta un script y retorna si fue exitoso"""
    print_header(description)
    print(f"⏳ Ejecutando: {script_name}")
    print(f"🕐 Inicio: {datetime.now().strftime('%H:%M:%S')}\n")
    
    try:
        result = subprocess.run(
            [sys.executable, script_name],
            capture_output=False,
            text=True,
            check=True
        )
        print(f"\n✅ Completado exitosamente")
        print(f"🕐 Fin: {datetime.now().strftime('%H:%M:%S')}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ Error al ejecutar el script")
        print(f"Código de salida: {e.returncode}")
        return False
    except Exception as e:
        print(f"\n❌ Error inesperado: {str(e)}")
        return False


def main():
    """Función principal"""
    print_header("🚀 CONFIGURACIÓN COMPLETA NOC - UISP + SPLYNX")
    print(f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 Usuario: Sistema Automatizado")
    print(f"🎯 Objetivo: Crear tareas y analizar infraestructura\n")
    
    scripts = [
        {
            'name': 'scripts/analyze_aps.py',
            'description': '📊 PASO 1: Análisis de APs (GPS y Saturación)',
            'required': True
        },
        {
            'name': 'scripts/create_noc_tasks.py',
            'description': '📝 PASO 2: Creación de Tareas en Splynx',
            'required': True
        }
    ]
    
    results = []
    
    for script in scripts:
        success = run_script(script['name'], script['description'])
        results.append({
            'script': script['name'],
            'success': success,
            'required': script['required']
        })
        
        if not success and script['required']:
            print(f"\n⚠️  Script requerido falló. ¿Continuar de todos modos? (s/n): ", end='')
            response = input().lower()
            if response != 's':
                print("\n🛑 Proceso interrumpido por el usuario")
                break
    
    # Resumen final
    print_header("📊 RESUMEN DE EJECUCIÓN")
    
    success_count = sum(1 for r in results if r['success'])
    total_count = len(results)
    
    print(f"Total de scripts ejecutados: {total_count}")
    print(f"✅ Exitosos: {success_count}")
    print(f"❌ Fallidos: {total_count - success_count}\n")
    
    print("Detalle:")
    for r in results:
        status = "✅" if r['success'] else "❌"
        print(f"  {status} {r['script']}")
    
    print("\n" + "="*70)
    print("📁 ARCHIVOS GENERADOS:")
    print("="*70)
    print("  📊 /tmp/analisis_aps_uisp.xlsx - Reporte Excel de APs")
    print("  📄 /tmp/analisis_aps_uisp.json - Datos JSON de análisis")
    print("  📄 /tmp/splynx_tasks_results.json - Resultados de creación de tareas")
    print("  📋 scripts/puntos_mejora_noc.md - Documento de mejoras")
    print("="*70)
    
    print("\n" + "="*70)
    print("📋 PRÓXIMOS PASOS:")
    print("="*70)
    print("  1. Revisar el Excel con APs sin GPS y saturados")
    print("  2. Verificar tareas creadas en Splynx (Proyecto NOC #26)")
    print("  3. Completar información faltante en cada tarea")
    print("  4. Revisar documento de puntos de mejora")
    print("  5. Priorizar acciones según criticidad")
    print("="*70)
    
    if success_count == total_count:
        print("\n🎉 ¡Proceso completado exitosamente!")
        return 0
    else:
        print("\n⚠️  Proceso completado con algunos errores")
        return 1


if __name__ == "__main__":
    sys.exit(main())
