"""
Diccionario de frecuencias disponibles por modelo de dispositivo Ubiquiti.
Estas frecuencias están en MHz y representan todos los canales que cada modelo puede escanear/usar.
"""

from typing import Dict, List

# Frecuencias por modelo de dispositivo
DEVICE_FREQUENCIES: Dict[str, List[int]] = {
    # LiteBeam AC - Banda completa 5 GHz (4.9 - 6.1 GHz)
    "LiteBeam AC": list(range(4920, 6105, 5)),  # 4920 a 6100 MHz en pasos de 5 MHz
    "LBE-5AC-Gen2": list(range(4920, 6105, 5)),
    "LBE-5AC-16-120": list(range(4920, 6105, 5)),
    "LBE-5AC-23": list(range(4920, 6105, 5)),
    
    # NanoBeam AC - Banda completa 5 GHz (4.9 - 6.1 GHz)
    "NanoBeam AC": list(range(4920, 6105, 5)),  # 4920 a 6100 MHz en pasos de 5 MHz
    "NBE-5AC-Gen2": list(range(4920, 6105, 5)),
    "NBE-5AC-16": list(range(4920, 6105, 5)),
    "NBE-5AC-19": list(range(4920, 6105, 5)),
    
    # PowerBeam AC - Banda 5 GHz completa
    "PowerBeam AC": list(range(5150, 5876, 5)),
    "PBE-5AC-Gen2": list(range(5150, 5876, 5)),
    "PBE-5AC-300": list(range(5150, 5876, 5)),
    "PBE-5AC-400": list(range(5150, 5876, 5)),
    "PBE-5AC-500": list(range(5150, 5876, 5)),
    "PBE-5AC-620": list(range(5150, 5876, 5)),
    
    # airMAX AC - Banda 5 GHz
    "Rocket 5AC": list(range(5150, 5876, 5)),
    "R5AC-Lite": list(range(5150, 5876, 5)),
    "R5AC-PTP": list(range(5150, 5876, 5)),
    "R5AC-PTMP": list(range(5150, 5876, 5)),
    
    # NanoStation AC - Dual band
    "NanoStation AC": {
        "2.4GHz": list(range(2412, 2485, 5)),  # 2.412 - 2.484 GHz
        "5GHz": list(range(5150, 5876, 5))
    },
    "NS-5AC": list(range(5150, 5876, 5)),
    "NS-5ACL": list(range(5150, 5876, 5)),
    
    # LiteAP AC - Banda 5 GHz
    "LiteAP AC": list(range(5150, 5876, 5)),
    "LAP-120": list(range(5150, 5876, 5)),
    "LAP-GPS": list(range(5150, 5876, 5)),
    
    # airFiber - Bandas específicas según modelo
    "airFiber 5": list(range(5150, 5876, 5)),
    "airFiber 5X": list(range(5150, 5876, 5)),
    "airFiber 5XHD": list(range(5150, 5876, 5)),
    "AF-5": list(range(5150, 5876, 5)),
    "AF-5X": list(range(5150, 5876, 5)),
    "AF-5XHD": list(range(5150, 5876, 5)),
    
    # airFiber 60/24 - Bandas milimétricas (solo referencia, no wireless típico)
    "airFiber 60": [60000],  # 60 GHz (simplificado)
    "airFiber 24": [24000],  # 24 GHz (simplificado)
    
    # Modelos legacy airMAX M (2.4 GHz y 5 GHz)
    "NanoStation M2": list(range(2412, 2485, 5)),
    "NanoStation M5": list(range(5150, 5876, 20)),  # Canales más espaciados en M5
    "Rocket M2": list(range(2412, 2485, 5)),
    "Rocket M5": list(range(5150, 5876, 20)),
    "PowerBeam M5": list(range(5150, 5876, 20)),
    "NanoBridge M5": list(range(5150, 5876, 20)),
    
    # Default genérico para dispositivos 5 GHz no identificados
    "default_5ghz": list(range(5150, 5876, 5)),
    "default_2.4ghz": list(range(2412, 2485, 5)),
}

# Bandas de frecuencia por región (regulatorio)
REGULATORY_BANDS: Dict[str, Dict[str, List[int]]] = {
    "FCC": {  # Estados Unidos
        "2.4GHz": list(range(2412, 2485, 5)),
        "5GHz_UNII1": list(range(5150, 5251, 5)),  # 5.15 - 5.25 GHz
        "5GHz_UNII2": list(range(5250, 5351, 5)),  # 5.25 - 5.35 GHz
        "5GHz_UNII2e": list(range(5470, 5726, 5)),  # 5.47 - 5.725 GHz
        "5GHz_UNII3": list(range(5725, 5851, 5)),  # 5.725 - 5.85 GHz
    },
    "ETSI": {  # Europa
        "2.4GHz": list(range(2412, 2485, 5)),
        "5GHz": list(range(5150, 5876, 5)),
    },
    "LATAM": {  # Latinoamérica (similar a FCC)
        "2.4GHz": list(range(2412, 2485, 5)),
        "5GHz": list(range(5150, 5876, 5)),
    }
}

def get_frequencies_for_model(model: str, default_band: str = "5GHz") -> List[int]:
    """
    Obtiene las frecuencias disponibles para un modelo específico.
    
    Args:
        model: Nombre del modelo del dispositivo
        default_band: Banda por defecto si el modelo no se encuentra ("5GHz" o "2.4GHz")
    
    Returns:
        Lista de frecuencias en MHz
    """
    # Buscar coincidencia exacta
    if model in DEVICE_FREQUENCIES:
        freq = DEVICE_FREQUENCIES[model]
        # Si es un dict (dual band), retornar la banda especificada
        if isinstance(freq, dict):
            return freq.get(default_band, freq.get("5GHz", []))
        return freq
    
    # Buscar coincidencia parcial (por si el modelo tiene sufijos/versiones)
    for key, freq in DEVICE_FREQUENCIES.items():
        if key.lower() in model.lower() or model.lower() in key.lower():
            if isinstance(freq, dict):
                return freq.get(default_band, freq.get("5GHz", []))
            return freq
    
    # Default según banda
    if "2.4" in model or "M2" in model:
        return DEVICE_FREQUENCIES["default_2.4ghz"]
    else:
        return DEVICE_FREQUENCIES["default_5ghz"]

def get_frequency_range_string(frequencies: List[int]) -> str:
    """
    Convierte una lista de frecuencias a un string de rangos legible.
    
    Args:
        frequencies: Lista de frecuencias en MHz
    
    Returns:
        String con rangos (ej: "5150-5250,5470-5850")
    """
    if not frequencies:
        return ""
    
    frequencies = sorted(frequencies)
    ranges = []
    start = frequencies[0]
    prev = frequencies[0]
    
    for freq in frequencies[1:]:
        if freq - prev > 10:  # Gap mayor a 10 MHz = nuevo rango
            ranges.append(f"{start}-{prev}")
            start = freq
        prev = freq
    
    ranges.append(f"{start}-{prev}")
    return ",".join(ranges)

def get_all_5ghz_frequencies() -> List[int]:
    """Retorna todas las frecuencias de 5 GHz posibles (4.9 - 6.1 GHz)"""
    return list(range(4920, 6105, 5))

def get_standard_5ghz_frequencies() -> List[int]:
    """Retorna frecuencias estándar de 5 GHz (5.15 - 5.875 GHz)"""
    return list(range(5150, 5876, 5))

def get_all_2_4ghz_frequencies() -> List[int]:
    """Retorna todas las frecuencias de 2.4 GHz (2.412 - 2.484 GHz)"""
    return list(range(2412, 2485, 5))
