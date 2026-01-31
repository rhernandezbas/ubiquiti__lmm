#!/usr/bin/env python3
"""
Script de migración manual para crear las tablas de la base de datos.
Ejecuta este script si necesitas crear las tablas manualmente.
"""

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Importar después de cargar .env
from app_fast_api.utils.database import init_db, engine
from sqlalchemy import inspect, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def check_existing_tables():
    """Verifica qué tablas ya existen en la base de datos."""
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    return existing_tables


def main():
    """Ejecuta la migración de base de datos."""
    print("=" * 60)
    print("  MIGRACIÓN DE BASE DE DATOS - Sistema de Alerting")
    print("=" * 60)
    print()

    # Verificar DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ ERROR: DATABASE_URL no está configurada")
        print("   Asegúrate de tener un archivo .env con:")
        print("   DATABASE_URL=mysql+pymysql://user:pass@host:port/database")
        return

    print(f"📊 Base de datos: {database_url}")
    print()

    # Verificar tablas existentes
    print("🔍 Verificando tablas existentes...")
    try:
        existing_tables = check_existing_tables()
        print(f"   Tablas encontradas: {len(existing_tables)}")
        for table in existing_tables:
            print(f"   ✓ {table}")
        print()
    except Exception as e:
        print(f"⚠️  No se pudo conectar a la base de datos: {str(e)}")
        print()

    # Preguntar confirmación
    response = input("¿Deseas continuar con la migración? [s/N]: ")
    if response.lower() not in ['s', 'si', 'yes', 'y']:
        print("❌ Migración cancelada")
        return

    print()
    print("🚀 Ejecutando migración...")
    print()

    try:
        # Ejecutar init_db() que creará las tablas
        init_db()

        print()
        print("=" * 60)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print()

        # Verificar tablas después de la migración
        print("📋 Tablas después de la migración:")
        existing_tables = check_existing_tables()
        for table in sorted(existing_tables):
            print(f"   ✓ {table}")

        print()
        print("🎉 Las nuevas tablas están listas para usar:")
        print("   - site_monitoring: Almacena información de sites de UNMS")
        print("   - alert_events: Gestiona eventos de alertas")
        print()
        print("📖 Para más información, consulta: ALERTING_SYSTEM.md")

    except Exception as e:
        print()
        print("=" * 60)
        print("❌ ERROR EN LA MIGRACIÓN")
        print("=" * 60)
        print(f"Error: {str(e)}")
        print()
        print("Posibles soluciones:")
        print("1. Verifica que DATABASE_URL sea correcta")
        print("2. Verifica que la base de datos esté corriendo")
        print("3. Verifica que tengas permisos para crear tablas")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
