# Exportador de Datos de Braze

Esta herramienta permite exportar datos de usuarios desde Braze utilizando la API oficial.

## 🔴 COMANDO RÁPIDO PARA PROCESO COMPLETO AUTOMÁTICO

Para ejecutar todo el proceso de forma automática (solicitud, descarga, extracción y procesamiento):

```bash
# Proceso completo automático (desde la solicitud hasta el procesamiento)
node braze-export-tool.js --all [ID_SEGMENTO] [TIEMPO_ESPERA_SEGUNDOS]

# Por ejemplo (usando el segmento de todos los usuarios):
node braze-export-tool.js --all
```

Si ya tienes una URL de descarga y quieres continuar desde ahí:

```bash
# Continuar desde una URL de descarga hasta el procesamiento
node braze-export-tool.js --continue URL_DESCARGA [MAX_USUARIOS]

# Por ejemplo:
node braze-export-tool.js --continue https://bucket.s3.amazonaws.com/archivo.zip 10000
```

## Requisitos

- Node.js (versión 14 o superior)
- Una cuenta de Braze con acceso a la API
- Clave de API de Braze con permisos de exportación de usuarios

## Instalación

1. Clona este repositorio
2. Instala las dependencias:

```bash
npm install
```

3. Configura el archivo `.env` con tus credenciales:

```
BRAZE_API_KEY=tu_api_key_aquí
BRAZE_API_URL=https://rest.iad-XX.braze.com  # Reemplaza XX con tu instancia
EXPORT_DIRECTORY=./exports
ALL_USERS_SEGMENT_ID=id_del_segmento_todos_los_usuarios

# AWS Credentials (opcional, para acceder a S3)
AWS_ACCESS_KEY_ID=tu_access_key_id
AWS_SECRET_ACCESS_KEY=tu_secret_access_key
AWS_REGION=us-east-1
```

## Guía detallada de comandos

### Todos los comandos disponibles

```bash
# Ver ayuda y opciones disponibles
node braze-export-tool.js --help

# 1. Solicitar una exportación a Braze
node braze-export-tool.js --export [ID_SEGMENTO]

# 2. Descargar un archivo de exportación usando la URL
node braze-export-tool.js --download URL_ARCHIVO

# 3. Extraer archivos de un ZIP descargado
node braze-export-tool.js --extract RUTA_ARCHIVO_ZIP

# 4. Procesar archivos extraídos
node braze-export-tool.js --process DIRECTORIO_EXTRAIDO [MAX_USUARIOS]

# 5. Proceso completo automático (desde solicitud hasta procesamiento)
node braze-export-tool.js --all [ID_SEGMENTO] [TIEMPO_ESPERA_SEGUNDOS]

# 6. Continuar desde una URL de descarga hasta el procesamiento
node braze-export-tool.js --continue URL_DESCARGA [MAX_USUARIOS]
```

### Flujo de trabajo recomendado

Puedes elegir entre dos flujos de trabajo principales:

#### Opción 1: Proceso completo automático

Este es el método más sencillo y recomendado:

```bash
# Todo el proceso en un solo comando:
node braze-export-tool.js --all
```

Este comando:
1. Solicita la exportación a Braze
2. Espera a que esté lista (por defecto 300 segundos)
3. Descarga el archivo automáticamente
4. Extrae los archivos
5. Procesa los datos

#### Opción 2: Proceso por etapas

Si prefieres ejecutar el proceso paso a paso:

1. **Solicitar exportación**:
   ```bash
   node braze-export-tool.js --export
   ```
   ⚠️ Esto te dará una URL de descarga que debes guardar.

2. **Continuar desde la URL**:
   ```bash
   node braze-export-tool.js --continue URL_DE_DESCARGA
   ```
   Este comando completará el resto del proceso desde la descarga hasta el procesamiento.

### Comandos individuales (para casos especiales)

Si necesitas ejecutar solo pasos específicos:

- **Descargar un archivo**: Útil si ya tienes una URL de exportación
  ```bash
  node braze-export-tool.js --download URL_ARCHIVO
  ```

- **Extraer un ZIP**: Si ya has descargado manualmente un archivo
  ```bash
  node braze-export-tool.js --extract ./exports/export_file.zip
  ```

- **Procesar archivos**: Si ya has extraído los archivos
  ```bash
  node braze-export-tool.js --process ./exports/extract_dir
  ```
  Puedes limitar el número de usuarios añadiendo un número al final:
  ```bash
  node braze-export-tool.js --process ./exports/extract_dir 10000
  ```

## Estructura del proyecto

- `braze-export-tool.js`: **Herramienta unificada** para todo el proceso de exportación
- `.env`: Archivo de configuración con credenciales
- `exports/`: Directorio donde se guardan los archivos exportados
  - `archive/`: Subdirectorio donde se almacenan los archivos ZIP y resultados antiguos
  - `extract_FECHA/`: Directorios temporales con los archivos extraídos
  - `usuarios_procesados_FECHA.json`: Archivos de resultados procesados

## Casos de uso comunes

### Exportar todos los usuarios

```bash
node braze-export-tool.js --all
```

### Exportar usuarios de un segmento específico

```bash
node braze-export-tool.js --all ID_SEGMENTO
```

### Procesar un archivo ZIP ya descargado

```bash
# 1. Extraer archivos
node braze-export-tool.js --extract ./exports/archive/export_download.zip

# 2. Procesar los datos (suponiendo que se extrajeron a extract_2025-02-28_17-03-52)
node braze-export-tool.js --process ./exports/extract_2025-02-28_17-03-52
```

## Notas importantes

- Las exportaciones de Braze pueden tardar varios minutos en completarse.
- Solo se puede tener una exportación activa por segmento al mismo tiempo.
- Las URLs de descarga proporcionadas por Braze suelen expirar después de unas horas.
- Para conjuntos de datos muy grandes, la herramienta divide los resultados en múltiples archivos (máximo 1,000,000 usuarios por archivo).

## Solución de problemas

### Error "Invalid Braze API URL"
- Verifica que el valor de `BRAZE_API_URL` en tu archivo `.env` sea una cadena de texto correcta.
- Ejemplo correcto: `BRAZE_API_URL=https://rest.iad-07.braze.com`

### Error "Acceso Denegado" al descargar de S3
- Verifica tus credenciales AWS en el archivo `.env`
- Es posible que la URL haya expirado (suelen durar pocas horas)
- Intenta usar un archivo ZIP ya descargado con el comando `--extract`

### Error "El directorio no existe" al procesar
- Asegúrate de usar la ruta correcta del directorio de extracción
- Puedes listar los directorios disponibles en la carpeta `exports/`
- Ejemplo: `ls -la exports/`

### Error de memoria al procesar muchos usuarios
- La herramienta ahora divide automáticamente los resultados en múltiples archivos
- Puedes limitar el número de usuarios a procesar añadiendo un número al final:
  ```bash
1. Verifica que tu API key tenga los permisos necesarios
2. Comprueba que la URL de la API sea correcta para tu instancia de Braze
3. Revisa los logs para identificar errores específicos
4. Para problemas de acceso a S3, verifica tus credenciales AWS

## Recursos adicionales

- [Documentación de la API de Braze](https://www.braze.com/docs/api/basics/)
- [Biblioteca braze-api](https://www.npmjs.com/package/braze-api) 