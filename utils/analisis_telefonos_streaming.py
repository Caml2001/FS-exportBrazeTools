#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Análisis de números de teléfono en archivo de usuarios - Versión optimizada.
Este script identifica usuarios cuyos números de teléfono no incluyen el prefijo de país (lada 52 para México).
Procesa el archivo JSON línea por línea para un manejo eficiente de memoria con archivos grandes.
Incluye análisis temporal con datos de registros del archivo CSV.
"""

import json
import os
import re
import csv
from datetime import datetime
from collections import defaultdict, Counter

# Configuración
ARCHIVO_ENTRADA = '../exports/allUsers.json'
DIRECTORIO_RESULTADOS = '../resultados'
PREFIJO_MEXICO = '52'  # Prefijo de país para México
ARCHIVO_CSV = 'userData.csv'  # Archivo CSV con fechas de registro

# Crear directorio de resultados si no existe
if not os.path.exists(DIRECTORIO_RESULTADOS):
    os.makedirs(DIRECTORIO_RESULTADOS)

# Timestamp para archivos de resultados
timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

def es_numero_mexicano_sin_prefijo(numero):
    """
    Determina si un número de teléfono es mexicano y no tiene el prefijo 52.
    
    Nueva lógica:
    - Números con exactamente 10 dígitos se consideran SIN lada de país
    - Números con más de 10 dígitos se consideran CON lada de país
    
    Args:
        numero (str): Número de teléfono a verificar
        
    Returns:
        bool: True si el número parece ser mexicano sin prefijo, False en caso contrario
    """
    if not numero:
        return False
    
    # Eliminar caracteres no numéricos
    numero_limpio = re.sub(r'\D', '', numero)
    
    # Nueva lógica: números con exactamente 10 dígitos NO tienen lada
    # Números con más de 10 dígitos SÍ tienen lada
    return len(numero_limpio) == 10

def cargar_datos_csv():
    """
    Carga los datos del archivo CSV para obtener las fechas de registro de los usuarios.
    
    Returns:
        dict: Diccionario con números de teléfono como clave y fecha de registro como valor
    """
    print(f"Cargando datos del archivo CSV: {ARCHIVO_CSV}")
    registros = {}
    
    try:
        # Leer todo el contenido del archivo como texto
        with open(ARCHIVO_CSV, 'rb') as f:
            contenido = f.read()
        
        # Detectar codificación y eliminar BOM si existe
        if contenido.startswith(b'\xef\xbb\xbf'):  # UTF-8 BOM
            contenido = contenido[3:]
        
        # Convertir a cadena y dividir por líneas
        lineas = contenido.decode('utf-8', errors='ignore').split('\n')
        
        # Procesar encabezado
        if len(lineas) > 0:
            encabezado = lineas[0].strip().split(',')
            
            # Limpiar posibles caracteres BOM del encabezado
            encabezado[0] = encabezado[0].lstrip('\ufeff').strip()
            
            # Verificar si las columnas necesarias están presentes
            if 'hostRegister' in encabezado and 'phone' in encabezado:
                hostRegister_idx = encabezado.index('hostRegister')
                phone_idx = encabezado.index('phone')
                
                # Procesar líneas de datos
                for i in range(1, len(lineas)):
                    if lineas[i].strip():  # Ignorar líneas vacías
                        campos = lineas[i].strip().split(',')
                        if len(campos) >= max(hostRegister_idx, phone_idx) + 1:
                            fecha_registro = campos[hostRegister_idx]
                            numero_telefono = campos[phone_idx]
                            
                            # Limpiar número telefónico (quitar signo negativo y tomar solo los últimos 10 dígitos)
                            numero_limpio = re.sub(r'\D', '', numero_telefono)
                            
                            # Si el número tiene longitud adecuada, guardar los últimos 10 dígitos
                            if len(numero_limpio) >= 10:
                                ultimos_10_digitos = numero_limpio[-10:]  # Tomar últimos 10 dígitos
                                registros[ultimos_10_digitos] = fecha_registro
            else:
                print(f"Error: Las columnas 'hostRegister' o 'phone' no se encontraron en el CSV.")
                print(f"Columnas encontradas: {encabezado}")
        
        print(f"Se cargaron {len(registros)} registros del archivo CSV")
        return registros
    
    except Exception as e:
        print(f"Error al cargar el archivo CSV: {str(e)}")
        return {}

def analizar_archivo_json_streaming():
    """
    Analiza el archivo JSON línea por línea para encontrar usuarios con números de teléfono sin prefijo de país.
    Usa un enfoque de streaming para manejar archivos grandes sin cargarlos completamente en memoria.
    
    Returns:
        tuple: (usuarios_sin_prefijo, usuarios_con_prefijo, total_usuarios_con_telefono, resultados_analisis)
    """
    print(f"Analizando archivo (modo streaming): {ARCHIVO_ENTRADA}")
    
    # Cargar datos de fechas de registro desde CSV
    fechas_registro_csv = cargar_datos_csv()
    
    # Contadores y listas para el análisis
    usuarios_sin_prefijo = []
    usuarios_con_prefijo = []
    total_usuarios = 0
    total_usuarios_con_telefono = 0
    
    try:
        # Abrir archivo en modo lectura
        with open(ARCHIVO_ENTRADA, 'r', encoding='utf-8') as file:
            # Leer la primera línea que debe ser '['
            primera_linea = file.readline().strip()
            if primera_linea != '[':
                print("Error: El archivo no comienza con '['. No es un JSON válido.")
                return [], [], 0, {}
            
            # Variables para el manejo de JSON incompleto entre líneas
            objeto_actual = ''
            en_objeto = False
            llaves_abiertas = 0
            
            # Procesar el archivo línea por línea
            for linea in file:
                linea = linea.strip()
                
                # Ignorar línea vacía
                if not linea:
                    continue
                
                # Si no estamos en un objeto, verificar si comienza uno nuevo
                if not en_objeto:
                    if linea.startswith('{'):
                        en_objeto = True
                        objeto_actual = linea
                        llaves_abiertas = linea.count('{') - linea.count('}')
                        
                        # Si el objeto se cierra en la misma línea
                        if llaves_abiertas == 0 and linea.endswith('},') or linea.endswith('}'):
                            en_objeto = False
                            # Eliminar la coma final si existe
                            if linea.endswith('},'):
                                objeto_json = objeto_actual[:-1]  # Quitar la coma
                            else:
                                objeto_json = objeto_actual
                            
                            # Procesar el objeto completo
                            usuario_procesado = procesar_objeto(objeto_json, fechas_registro_csv)
                            if usuario_procesado:
                                total_usuarios_con_telefono += 1
                                if usuario_procesado.get('sin_prefijo', False):
                                    usuarios_sin_prefijo.append(usuario_procesado['info'])
                                else:
                                    usuarios_con_prefijo.append(usuario_procesado['info'])
                            
                            total_usuarios += 1
                            objeto_actual = ''
                else:
                    # Estamos en medio de un objeto, añadir la línea actual
                    objeto_actual += linea
                    llaves_abiertas += linea.count('{') - linea.count('}')
                    
                    # Verificar si el objeto se cierra
                    if llaves_abiertas == 0 and (linea.endswith('},') or linea.endswith('}')):
                        en_objeto = False
                        # Eliminar la coma final si existe
                        if linea.endswith('},'):
                            objeto_json = objeto_actual[:-1]  # Quitar la coma
                        else:
                            objeto_json = objeto_actual
                        
                        # Procesar el objeto completo
                        usuario_procesado = procesar_objeto(objeto_json, fechas_registro_csv)
                        if usuario_procesado:
                            total_usuarios_con_telefono += 1
                            if usuario_procesado.get('sin_prefijo', False):
                                usuarios_sin_prefijo.append(usuario_procesado['info'])
                            else:
                                usuarios_con_prefijo.append(usuario_procesado['info'])
                        
                        total_usuarios += 1
                        objeto_actual = ''
        
        # Analizar distribución temporal de registros
        analisis_temporal = analizar_distribucion_temporal(usuarios_sin_prefijo, usuarios_con_prefijo)
        
        # Crear resumen del análisis
        resultados_analisis = {
            'total_usuarios': total_usuarios,
            'total_con_telefono': total_usuarios_con_telefono,
            'total_sin_prefijo': len(usuarios_sin_prefijo),
            'total_con_prefijo': len(usuarios_con_prefijo),
            'porcentaje_sin_prefijo': round((len(usuarios_sin_prefijo) / total_usuarios_con_telefono * 100), 2) if total_usuarios_con_telefono > 0 else 0,
            'analisis_temporal': analisis_temporal
        }
        
        return usuarios_sin_prefijo, usuarios_con_prefijo, total_usuarios_con_telefono, resultados_analisis
    
    except Exception as e:
        print(f"Error al procesar el archivo: {str(e)}")
        return [], [], 0, {}

def procesar_objeto(objeto_json, fechas_registro_csv):
    """
    Procesa un objeto JSON y verifica si tiene un número de teléfono sin prefijo.
    
    Args:
        objeto_json (str): Cadena que representa un objeto JSON
        fechas_registro_csv (dict): Diccionario con fechas de registro desde el CSV
        
    Returns:
        dict: Información del usuario procesado o None si no tiene teléfono
    """
    try:
        usuario = json.loads(objeto_json)
        
        # Verificar si el usuario tiene número de teléfono
        if 'phone' in usuario and usuario['phone']:
            # Obtener número limpio
            numero_limpio = re.sub(r'\D', '', usuario['phone'])
            ultimos_10_digitos = numero_limpio[-10:] if len(numero_limpio) >= 10 else numero_limpio
            
            # Determinar si el número tiene prefijo
            tiene_sin_prefijo = es_numero_mexicano_sin_prefijo(usuario['phone'])
            
            # Recopilar información relevante del usuario
            info_usuario = {
                'phone': usuario['phone'],
                'phone_limpio': numero_limpio,
                'ultimos_10_digitos': ultimos_10_digitos,
                'phone_length': len(numero_limpio),  # Añadir longitud del número
                'email': usuario.get('email', 'No disponible'),
                'external_id': usuario.get('external_id', 'No disponible'),
                'country': usuario.get('country', 'No disponible'),
                'fecha_registro': 'No disponible'
            }
            
            # Añadir fecha de registro si está disponible en el CSV
            if ultimos_10_digitos in fechas_registro_csv:
                info_usuario['fecha_registro'] = fechas_registro_csv[ultimos_10_digitos]
                # Extraer solo el año y mes para análisis temporal
                try:
                    fecha_obj = datetime.strptime(fechas_registro_csv[ultimos_10_digitos], '%Y-%m-%d %H:%M:%S')
                    info_usuario['anio_registro'] = fecha_obj.year
                    info_usuario['mes_registro'] = fecha_obj.month
                    info_usuario['periodo'] = f"{fecha_obj.year}-{fecha_obj.month:02d}"
                except Exception:
                    # Si hay error en el formato de fecha, dejar los valores por defecto
                    pass
            
            # Añadir atributos personalizados si existen
            if 'custom_attributes' in usuario:
                if 'name' in usuario['custom_attributes']:
                    info_usuario['nombre'] = usuario['custom_attributes']['name']
                if 'paternal' in usuario['custom_attributes']:
                    info_usuario['apellido_paterno'] = usuario['custom_attributes']['paternal']
                if 'maternal' in usuario['custom_attributes']:
                    info_usuario['apellido_materno'] = usuario['custom_attributes']['maternal']
                if 'entity' in usuario['custom_attributes']:
                    info_usuario['entidad'] = usuario['custom_attributes']['entity']
                # También buscar si hay fecha de registro en los atributos personalizados
                if 'fechaRegistro' in usuario['custom_attributes'] and info_usuario['fecha_registro'] == 'No disponible':
                    info_usuario['fecha_registro'] = usuario['custom_attributes']['fechaRegistro']
            
            return {
                'sin_prefijo': tiene_sin_prefijo,
                'info': info_usuario
            }
        
        return None  # No tiene teléfono
    
    except json.JSONDecodeError:
        print(f"Error al decodificar JSON: {objeto_json[:100]}...")
        return None
    except Exception as e:
        print(f"Error al procesar objeto: {str(e)}")
        return None

def analizar_distribucion_temporal(usuarios_sin_prefijo, usuarios_con_prefijo):
    """
    Analiza la distribución temporal de usuarios con y sin prefijo de país.
    
    Args:
        usuarios_sin_prefijo (list): Lista de usuarios con teléfonos sin prefijo
        usuarios_con_prefijo (list): Lista de usuarios con teléfonos con prefijo
        
    Returns:
        dict: Análisis temporal con distribución por año/mes
    """
    # Agrupar usuarios por período (año-mes)
    periodos_sin_prefijo = defaultdict(int)
    periodos_con_prefijo = defaultdict(int)
    
    # Contabilizar usuarios por período
    for usuario in usuarios_sin_prefijo:
        if 'periodo' in usuario:
            periodos_sin_prefijo[usuario['periodo']] += 1
    
    for usuario in usuarios_con_prefijo:
        if 'periodo' in usuario:
            periodos_con_prefijo[usuario['periodo']] += 1
    
    # Obtener todos los períodos únicos y ordenarlos
    todos_periodos = sorted(set(list(periodos_sin_prefijo.keys()) + list(periodos_con_prefijo.keys())))
    
    # Crear análisis completo
    analisis_temporal = {
        'periodos': todos_periodos,
        'datos': []
    }
    
    # Para cada período, calcular la proporción de usuarios con/sin prefijo
    for periodo in todos_periodos:
        sin_prefijo = periodos_sin_prefijo[periodo]
        con_prefijo = periodos_con_prefijo[periodo]
        total = sin_prefijo + con_prefijo
        
        # Calcular porcentajes
        porcentaje_sin_prefijo = round((sin_prefijo / total * 100), 2) if total > 0 else 0
        porcentaje_con_prefijo = round((con_prefijo / total * 100), 2) if total > 0 else 0
        
        analisis_temporal['datos'].append({
            'periodo': periodo,
            'sin_prefijo': sin_prefijo,
            'con_prefijo': con_prefijo,
            'total': total,
            'porcentaje_sin_prefijo': porcentaje_sin_prefijo,
            'porcentaje_con_prefijo': porcentaje_con_prefijo
        })
    
    return analisis_temporal

def guardar_resultados(usuarios_sin_prefijo, usuarios_con_prefijo, resultados_analisis):
    """
    Guarda los resultados del análisis en archivos JSON.
    
    Args:
        usuarios_sin_prefijo (list): Lista de usuarios con teléfonos sin prefijo
        usuarios_con_prefijo (list): Lista de usuarios con teléfonos con prefijo
        resultados_analisis (dict): Resumen estadístico del análisis
    """
    # Guardar lista de usuarios sin prefijo
    archivo_sin_prefijo = os.path.join(DIRECTORIO_RESULTADOS, f'usuarios_sin_prefijo_{timestamp}.json')
    with open(archivo_sin_prefijo, 'w', encoding='utf-8') as f:
        json.dump(usuarios_sin_prefijo, f, ensure_ascii=False, indent=2)
    
    # Guardar lista de usuarios con prefijo
    archivo_con_prefijo = os.path.join(DIRECTORIO_RESULTADOS, f'usuarios_con_prefijo_{timestamp}.json')
    with open(archivo_con_prefijo, 'w', encoding='utf-8') as f:
        json.dump(usuarios_con_prefijo, f, ensure_ascii=False, indent=2)
    
    # Guardar resumen del análisis
    archivo_resumen = os.path.join(DIRECTORIO_RESULTADOS, f'resumen_analisis_{timestamp}.json')
    with open(archivo_resumen, 'w', encoding='utf-8') as f:
        json.dump(resultados_analisis, f, ensure_ascii=False, indent=2)
    
    # Crear archivo CSV con análisis temporal
    archivo_temporal_csv = os.path.join(DIRECTORIO_RESULTADOS, f'analisis_temporal_{timestamp}.csv')
    with open(archivo_temporal_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        # Escribir encabezados
        writer.writerow(['Periodo', 'Total Usuarios', 'Sin Prefijo', 'Con Prefijo', '% Sin Prefijo', '% Con Prefijo'])
        
        # Escribir datos
        for periodo in resultados_analisis['analisis_temporal']['datos']:
            writer.writerow([
                periodo['periodo'],
                periodo['total'],
                periodo['sin_prefijo'],
                periodo['con_prefijo'],
                periodo['porcentaje_sin_prefijo'],
                periodo['porcentaje_con_prefijo']
            ])
    
    print(f"Resultados guardados en:")
    print(f"- {archivo_sin_prefijo}")
    print(f"- {archivo_con_prefijo}")
    print(f"- {archivo_resumen}")
    print(f"- {archivo_temporal_csv}")

def main():
    """Función principal del script."""
    print("Iniciando análisis de números de teléfono con análisis temporal...")
    
    # Analizar el archivo JSON
    usuarios_sin_prefijo, usuarios_con_prefijo, total_con_telefono, resultados_analisis = analizar_archivo_json_streaming()
    
    # Mostrar resultados
    print("\nResultados del análisis:")
    print(f"Total de usuarios procesados: {resultados_analisis['total_usuarios']}")
    print(f"Usuarios con número de teléfono: {total_con_telefono}")
    print(f"Usuarios sin prefijo de país: {len(usuarios_sin_prefijo)} ({resultados_analisis['porcentaje_sin_prefijo']}%)")
    print(f"Usuarios con prefijo de país: {len(usuarios_con_prefijo)} ({100 - resultados_analisis['porcentaje_sin_prefijo']}%)")
    
    # Mostrar análisis temporal
    print("\nAnálisis temporal (por período):")
    print("Periodo\t\tTotal\tSin Prefijo\tCon Prefijo\t% Sin Prefijo\t% Con Prefijo")
    for periodo in resultados_analisis['analisis_temporal']['datos']:
        print(f"{periodo['periodo']}\t{periodo['total']}\t{periodo['sin_prefijo']}\t{periodo['con_prefijo']}\t{periodo['porcentaje_sin_prefijo']}%\t{periodo['porcentaje_con_prefijo']}%")
    
    # Guardar resultados en archivos
    guardar_resultados(usuarios_sin_prefijo, usuarios_con_prefijo, resultados_analisis)
    
    print("\nAnálisis completado.")

if __name__ == "__main__":
    main() 