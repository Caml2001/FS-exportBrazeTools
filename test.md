# Exportador de Datos de Braze

Esta herramienta permite exportar datos de usuarios desde Braze utilizando la API oficial de Braze y bibliotecas de Node.js. Está diseñada para automatizar o ejecutar paso a paso el proceso de solicitud, descarga, extracción y procesamiento de datos de usuarios.

## 🔴 COMANDO RÁPIDO PARA PROCESO COMPLETO AUTOMÁTICO

Para ejecutar todo el proceso de forma automática (solicitud, descarga, extracción y procesamiento):

```bash
# Proceso completo automático (desde la solicitud hasta el procesamiento)
node braze-export-tool.js --all [ID_SEGMENTO] [TIEMPO_ESPERA_SEGUNDOS]

# Ejemplo (usando el segmento de todos los usuarios):
node braze-export-tool.js --all
```

Si ya tienes una URL de descarga y deseas continuar desde ese punto:

```bash
# Continuar desde una URL de descarga hasta el procesamiento
node braze-export-tool.js --continue URL_DESCARGA [MAX_USUARIOS]

# Ejemplo:
node braze-export-tool.js --continue https://bucket.s3.amazonaws.com/archivo.zip 10000
```

## Requisitos

- **Node.js**: Versión 14 o superior
- **Cuenta de Braze**: Con acceso a la API
- **Clave de API de Braze**: Con permisos para exportar usuarios
- **Dependencias**: Instaladas mediante `npm install`

## Instalación

1. **Clona el repositorio**:
   ```bash
   git clone <URL_DEL_REPOSITORIO>
   cd <NOMBRE_DEL_REPOSITORIO>
   ```

2. **Instala las dependencias**:
   ```bash
   npm install
   ```

3. **Configura el archivo `.env`**:
   Crea un archivo `.env` en la raíz del proyecto y añade las siguientes variables (ajusta los valores según tu configuración):

   ```
   BRAZE_API_KEY=tu_api_key_aquí
   BRAZE_API_URL=https://rest.iad-XX.braze.com  # Reemplaza XX con tu instancia de Braze
   EXPORT_DIRECTORY=./exports
   ALL_USERS_SEGMENT_ID=id_del_segmento_todos_los_usuarios

   # Credenciales AWS (opcional, para descargas desde S3)
   AWS_ACCESS_KEY_ID=tu_access_key_id
   AWS_SECRET_ACCESS_KEY=tu_secret_access_key
   AWS_REGION=us-east-1
   ```

## Guía detallada de comandos

### Todos los comandos disponibles

```bash
# Mostrar ayuda y opciones disponibles
node braze-export-tool.js --help

# 1. Solicitar una exportación a Braze
node braze-export-tool.js --export [ID_SEGMENTO]

# 2. Descargar un archivo de exportación desde una URL
node braze-export-tool.js --download URL_ARCHIVO

# 3. Extraer archivos de un ZIP descargado
node braze-export-tool.js --extract RUTA_ARCHIVO_ZIP

# 4. Procesar archivos extraídos
node braze-export-tool.js --process DIRECTORIO_EXTRAIDO [MAX_USUARIOS]

# 5. Ejecutar el proceso completo automáticamente
node braze-export-tool.js --all [ID_SEGMENTO] [TIEMPO_ESPERA_SEGUNDOS]

# 6. Continuar desde una URL de descarga hasta el procesamiento
node braze-export-tool.js --continue URL_DESCARGA [MAX_USUARIOS]
```

### Flujo de trabajo recomendado

#### Opción 1: Proceso completo automático

El método más rápido y sencillo:

```bash
# Todo en un solo paso:
node braze-export-tool.js --all
```

**Qué hace este comando**:
1. Solicita la exportación a Braze
2. Espera a que el archivo esté listo (por defecto, 300 segundos, ajustable con `[TIEMPO_ESPERA_SEGUNDOS]`)
3. Descarga el archivo ZIP
4. Extrae los contenidos
5. Procesa los datos y genera los resultados

#### Opción 2: Proceso por etapas

Para mayor control, ejecuta el proceso paso a paso:

1. **Solicitar exportación**:
   ```bash
   node braze-export-tool.js --export [ID_SEGMENTO]
   ```
   - Devuelve una URL de descarga que debes guardar.
   - Si omites `[ID_SEGMENTO]`, usa el segmento configurado en `ALL_USERS_SEGMENT_ID`.

2. **Continuar desde la URL**:
   ```bash
   node braze-export-tool.js --continue URL_DESCARGA
   ```
   - Descarga el archivo, lo extrae y procesa los datos automáticamente.

### Comandos individuales (para casos específicos)

- **Descargar un archivo**:
  ```bash
  node braze-export-tool.js --download URL_ARCHIVO
  ```

- **Extraer un ZIP**:
  ```bash
  node braze-export-tool.js --extract ./exports/archivo.zip
  ```

- **Procesar archivos extraídos**:
  ```bash
  node braze-export-tool.js --process ./exports/extract_dir
  ```
  - Limita los usuarios procesados añadiendo `[MAX_USUARIOS]`:
    ```bash
    node braze-export-tool.js --process ./exports/extract_dir 10000
    ```

## Estructura del proyecto

- **`braze-export-tool.js`**: Script principal que ejecuta todas las operaciones
- **`.env`**: Archivo de configuración con credenciales y variables
- **`exports/`**: Directorio para los archivos generados
  - **`archive/`**: Almacena ZIPs descargados y resultados antiguos
  - **`extract_FECHA/`**: Directorios temporales con archivos extraídos (ej. `extract_2023-10-15_14-30-00`)
  - **`usuarios_procesados_FECHA.json`**: Resultados procesados (ej. `usuarios_procesados_2023-10-15_14-30-00.json`)

## Casos de uso comunes

### Exportar todos los usuarios

```bash
node braze-export-tool.js --all
```

### Exportar un segmento específico

```bash
node braze-export-tool.js --all ID_SEGMENTO
```

### Procesar un archivo ZIP ya descargado

```bash
# 1. Extraer el archivo ZIP
node braze-export-tool.js --extract ./exports/archive/export.zip

# 2. Procesar los datos extraídos
node braze-export-tool.js --process ./exports/extract_2023-10-15_14-30-00
```

## Notas importantes

- **Tiempo de espera**: Las exportaciones de Braze pueden tardar minutos en generarse, especialmente con grandes volúmenes de datos.
- **Límite por segmento**: Solo una exportación activa por segmento a la vez.
- **Expiración de URLs**: Las URLs de descarga de Braze expiran tras pocas horas.
- **Datos grandes**: La herramienta divide automáticamente los resultados en archivos de máximo 1,000,000 usuarios por archivo.

## Solución de problemas

### Error "Invalid Braze API URL"
- Verifica `BRAZE_API_URL` en `.env`. Ejemplo correcto:
  ```
  BRAZE_API_URL=https://rest.iad-07.braze.com
  ```

### Error "Acceso Denegado" al descargar desde S3
- Revisa las credenciales AWS en `.env`.
- Si la URL expiró, descarga manualmente el ZIP y usa `--extract`.

### Error "El directorio no existe" al procesar
- Confirma la ruta del directorio de extracción:
  ```bash
  ls -la exports/  # En Linux/Mac
  dir exports\     # En Windows
  ```

### Error de memoria con muchos usuarios
- Limita los usuarios procesados:
  ```bash
  node braze-export-tool.js --process ./exports/extract_dir 500000
  ```

## Recursos adicionales

- [Documentación de la API de Braze](https://www.braze.com/docs/api/basics/)
- [Biblioteca braze-api en npm](https://www.npmjs.com/package/braze-api)