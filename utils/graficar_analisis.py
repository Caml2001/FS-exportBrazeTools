#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Graficador de análisis temporal de números telefónicos.
Este script genera gráficas a partir del archivo CSV generado por analisis_telefonos_streaming.py.
"""

import os
import csv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import seaborn as sns

# Configuración
DIRECTORIO_RESULTADOS = '../resultados'
DIRECTORIO_GRAFICAS = '../graficas'
ARCHIVO_CSV = 'analisis_temporal_2025-02-28_19-51-16.csv'

# Crear directorio de gráficas si no existe
if not os.path.exists(DIRECTORIO_GRAFICAS):
    os.makedirs(DIRECTORIO_GRAFICAS)

def cargar_datos_csv():
    """
    Carga los datos desde el archivo CSV de análisis temporal.
    
    Returns:
        pandas.DataFrame: DataFrame con los datos cargados
    """
    ruta_archivo = os.path.join(DIRECTORIO_RESULTADOS, ARCHIVO_CSV)
    print(f"Cargando datos desde: {ruta_archivo}")
    
    try:
        # Cargar datos con pandas
        df = pd.read_csv(ruta_archivo)
        
        # Convertir 'Periodo' a formato de fecha para mejor visualización
        df['Fecha'] = df['Periodo'].apply(lambda x: datetime.strptime(x, '%Y-%m'))
        
        # Ordenar por fecha
        df = df.sort_values('Fecha')
        
        print(f"Se cargaron {len(df)} registros")
        return df
    
    except Exception as e:
        print(f"Error al cargar el archivo CSV: {str(e)}")
        return None

def generar_grafica_porcentajes(df):
    """
    Genera una gráfica de líneas que muestra la evolución del porcentaje 
    de números con y sin prefijo a lo largo del tiempo.
    
    Args:
        df (pandas.DataFrame): DataFrame con los datos
    """
    print("Generando gráfica de porcentajes...")
    
    # Configurar el estilo
    plt.figure(figsize=(15, 8))
    sns.set_style("whitegrid")
    
    # Graficar porcentajes
    plt.plot(df['Fecha'], df['% Sin Prefijo'], 'r-', linewidth=2, label='Sin prefijo')
    plt.plot(df['Fecha'], df['% Con Prefijo'], 'b-', linewidth=2, label='Con prefijo')
    
    # Añadir línea de 50%
    plt.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
    
    # Configurar ejes y títulos
    plt.title('Evolución porcentual de números con y sin prefijo país', fontsize=16)
    plt.xlabel('Fecha', fontsize=12)
    plt.ylabel('Porcentaje (%)', fontsize=12)
    plt.ylim(0, 105)  # Limite del eje Y
    
    # Formato de fecha en eje X
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)
    
    # Añadir cuadrícula y leyenda
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Guardar gráfica
    ruta_grafica = os.path.join(DIRECTORIO_GRAFICAS, 'evolucion_porcentajes.png')
    plt.tight_layout()
    plt.savefig(ruta_grafica, dpi=300)
    print(f"Gráfica guardada en: {ruta_grafica}")
    plt.close()

def generar_grafica_volumen(df):
    """
    Genera una gráfica de barras apiladas que muestra el volumen 
    de usuarios con y sin prefijo a lo largo del tiempo.
    
    Args:
        df (pandas.DataFrame): DataFrame con los datos
    """
    print("Generando gráfica de volumen...")
    
    # Configurar el estilo
    plt.figure(figsize=(15, 8))
    sns.set_style("whitegrid")
    
    # Crear barras apiladas
    plt.bar(df['Fecha'], df['Sin Prefijo'], color='red', label='Sin prefijo')
    plt.bar(df['Fecha'], df['Con Prefijo'], bottom=df['Sin Prefijo'], color='blue', label='Con prefijo')
    
    # Configurar ejes y títulos
    plt.title('Volumen de registros con y sin prefijo país', fontsize=16)
    plt.xlabel('Fecha', fontsize=12)
    plt.ylabel('Número de usuarios', fontsize=12)
    
    # Formato de fecha en eje X
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=3))
    plt.xticks(rotation=45)
    
    # Añadir cuadrícula y leyenda
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Guardar gráfica
    ruta_grafica = os.path.join(DIRECTORIO_GRAFICAS, 'volumen_usuarios.png')
    plt.tight_layout()
    plt.savefig(ruta_grafica, dpi=300)
    print(f"Gráfica guardada en: {ruta_grafica}")
    plt.close()

def generar_grafica_tendencia(df):
    """
    Genera una gráfica de tendencia combinando líneas y áreas.
    
    Args:
        df (pandas.DataFrame): DataFrame con los datos
    """
    print("Generando gráfica de tendencia...")
    
    # Filtrar datos a partir de 2023 para mejor visualización
    df_reciente = df[df['Fecha'] >= datetime(2023, 1, 1)]
    
    # Resetear índices para evitar problemas con iloc
    df_reciente = df_reciente.reset_index(drop=True)
    
    # Configurar el estilo
    plt.figure(figsize=(15, 8))
    sns.set_style("whitegrid")
    
    # Crear áreas sombreadas
    plt.fill_between(df_reciente['Fecha'], df_reciente['% Sin Prefijo'], 
                     color='red', alpha=0.3, label='_nolegend_')
    plt.fill_between(df_reciente['Fecha'], df_reciente['% Con Prefijo'], 
                     color='blue', alpha=0.3, label='_nolegend_')
    
    # Añadir líneas de tendencia
    plt.plot(df_reciente['Fecha'], df_reciente['% Sin Prefijo'], 'r-', linewidth=2, label='Sin prefijo')
    plt.plot(df_reciente['Fecha'], df_reciente['% Con Prefijo'], 'b-', linewidth=2, label='Con prefijo')
    
    # Marcar el punto de inversión (cuando cruzan el 50%)
    punto_cruce = df_reciente[df_reciente['% Sin Prefijo'] > 50].iloc[0] if any(df_reciente['% Sin Prefijo'] > 50) else None
    if punto_cruce is not None:
        plt.axvline(x=punto_cruce['Fecha'], color='green', linestyle='--', linewidth=2)
        plt.text(punto_cruce['Fecha'], 105, f"Punto de inversión\n{punto_cruce['Periodo']}", 
                 ha='center', va='top', color='green', fontweight='bold')
    
    # Configurar ejes y títulos
    plt.title('Tendencia reciente: Cambio en la distribución de números telefónicos', fontsize=16)
    plt.xlabel('Fecha', fontsize=12)
    plt.ylabel('Porcentaje (%)', fontsize=12)
    plt.ylim(0, 105)  # Limite del eje Y
    
    # Formato de fecha en eje X
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))
    plt.xticks(rotation=45)
    
    # Añadir cuadrícula y leyenda
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=12)
    
    # Añadir anotaciones para puntos clave de manera segura
    for i in range(len(df_reciente)):
        row = df_reciente.iloc[i]
        if row['% Sin Prefijo'] > 90:
            # Solo comparar con fila anterior si no es la primera
            if i == 0 or (i > 0 and df_reciente.iloc[i-1]['% Sin Prefijo'] < 90):
                plt.annotate(f"{row['Periodo']}: {row['% Sin Prefijo']}%", 
                            xy=(row['Fecha'], row['% Sin Prefijo']),
                            xytext=(10, 20),
                            textcoords='offset points',
                            arrowprops=dict(arrowstyle='->', color='black'))
    
    # Guardar gráfica
    ruta_grafica = os.path.join(DIRECTORIO_GRAFICAS, 'tendencia_reciente.png')
    plt.tight_layout()
    plt.savefig(ruta_grafica, dpi=300)
    print(f"Gráfica guardada en: {ruta_grafica}")
    plt.close()

def main():
    """Función principal del script."""
    print("Iniciando generación de gráficas...")
    
    # Cargar datos
    df = cargar_datos_csv()
    if df is None:
        print("No se pudieron cargar los datos. Abortando.")
        return
    
    # Generar gráficas
    generar_grafica_porcentajes(df)
    generar_grafica_volumen(df)
    generar_grafica_tendencia(df)
    
    print("\nTodas las gráficas han sido generadas.")

if __name__ == "__main__":
    main() 