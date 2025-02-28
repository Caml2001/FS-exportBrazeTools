#!/usr/bin/env node
require('dotenv').config();
const { Braze } = require('braze-api');
const fs = require('fs');
const path = require('path');
const axios = require('axios');
const AdmZip = require('adm-zip');
const readline = require('readline');
const moment = require('moment');
const AWS = require('aws-sdk');

// Configuración desde variables de entorno o argumentos
const config = {
  // Credenciales de Braze
  brazeApiKey: process.env.BRAZE_API_KEY,
  brazeApiUrl: process.env.BRAZE_API_URL,
  // Configuración de exportación
  allUsersSegmentId: process.env.ALL_USERS_SEGMENT_ID,
  exportDir: process.env.EXPORT_DIRECTORY || './exports',
  // Límites y configuración
  maxUsers: 1000000,
  // AWS
  awsRegion: process.env.AWS_REGION || 'us-east-1',
  awsAccessKeyId: process.env.AWS_ACCESS_KEY_ID,
  awsSecretAccessKey: process.env.AWS_SECRET_ACCESS_KEY
};

// Inicializar Braze SDK (verificando que ambos valores están definidos)
let braze;
try {
  if (!config.brazeApiKey || !config.brazeApiUrl) {
    console.warn('ADVERTENCIA: No se han proporcionado credenciales de Braze válidas en el archivo .env');
    console.warn('Algunas funcionalidades que requieren acceso a la API de Braze no estarán disponibles');
  } else {
    // Imprimir valores para depuración
    console.log('Valores de inicialización:');
    console.log('- API Key:', config.brazeApiKey);
    console.log('- API URL:', config.brazeApiUrl);
    console.log('- Tipo de dato de API URL:', typeof config.brazeApiUrl);
    
    // Inicializar correctamente pasando los argumentos por separado
    braze = new Braze(config.brazeApiUrl, config.brazeApiKey);
    console.log('SDK de Braze inicializado correctamente');
  }
} catch (error) {
  console.error('Error al inicializar el SDK de Braze:', error.message);
  console.error('Algunas funcionalidades que requieren acceso a la API de Braze no estarán disponibles');
}

// Crear directorio de exportación si no existe
if (!fs.existsSync(config.exportDir)) {
  fs.mkdirSync(config.exportDir, { recursive: true });
}

// Generar un ID único para esta ejecución
const runId = moment().format('YYYY-MM-DD_HH-mm-ss');

/**
 * Paso 1: Solicitar la exportación a Braze
 * @param {string} segmentId - ID del segmento a exportar
 * @returns {Promise<object>} - Respuesta de la API con datos de la exportación
 */
async function solicitarExportacion(segmentId = config.allUsersSegmentId) {
  console.log('===== PASO 1: SOLICITAR EXPORTACIÓN =====');
  console.log(`Solicitando exportación del segmento: ${segmentId}`);
  
  try {
    if (!braze) {
      throw new Error('El SDK de Braze no está inicializado. Verifica tus credenciales en el archivo .env');
    }
    
    if (!segmentId) {
      throw new Error('No se ha proporcionado un ID de segmento válido');
    }
    
    // Iniciar la exportación usando el endpoint de exportación por segmento
    const exportResponse = await braze.users.export.segment({
      segment_id: segmentId,
      fields_to_export: [
        "external_id", "first_name", "last_name", "email", "phone",
        "country", "gender", "home_city", "language", "time_zone",
        "dob", "custom_attributes", "custom_events", "purchases"
      ]
    });
    
    // Verificar si la exportación se inició correctamente
    if (!exportResponse.message || exportResponse.message !== 'success') {
      throw new Error(`Error al iniciar exportación: ${JSON.stringify(exportResponse)}`);
    }
    
    console.log('Exportación iniciada con éxito.');
    console.log('\n===== INFORMACIÓN SOBRE LA EXPORTACIÓN =====');
    
    // Guardar información de la exportación en un archivo de registro
    const exportInfo = {
      fecha_solicitud: moment().format('YYYY-MM-DD HH:mm:ss'),
      segmento_id: segmentId,
      url: exportResponse.url || null,
      object_prefix: exportResponse.object_prefix || null,
      estado: 'solicitado'
    };
    
    const exportInfoFile = path.join(config.exportDir, `export_info_${runId}.json`);
    fs.writeFileSync(exportInfoFile, JSON.stringify(exportInfo, null, 2));
    console.log(`Información de la exportación guardada en: ${exportInfoFile}`);
    
    if (exportResponse.url) {
      console.log(`URL de descarga: ${exportResponse.url}`);
      console.log('NOTA: Esta URL estará disponible solo por unas horas.');
    } else if (exportResponse.object_prefix) {
      console.log(`Prefijo del objeto: ${exportResponse.object_prefix}`);
      console.log('Los archivos se guardarán en el bucket de S3 configurado en tu cuenta de Braze.');
    }
    
    return { 
      success: true, 
      exportInfo,
      exportInfoFile,
      exportResponse 
    };
  } catch (error) {
    console.error('Error al solicitar la exportación:', error.message);
    
    // Manejar el error específico de exportación en progreso
    if (error.status === 429 && error.message && error.message.includes('already in progress')) {
      console.log('\n===== INFORMACIÓN IMPORTANTE =====');
      console.log('Ya hay una exportación en progreso para este segmento.');
      console.log('Según la documentación de Braze, solo se puede ejecutar una exportación por segmento a la vez.');
      console.log('\n===== DÓNDE VER LA EXPORTACIÓN EN CURSO =====');
      console.log('1. Panel de control de Braze:');
      console.log('   - Inicia sesión en tu cuenta de Braze');
      console.log('   - Ve a la sección "Usuarios" o "Exportaciones"');
    }
    
    return { success: false, error: error.message };
  }
}

/**
 * Paso 2: Descargar archivo de exportación
 * @param {string} url - URL del archivo en S3
 * @returns {Promise<object>} - Información sobre la descarga
 */
async function descargarArchivo(url) {
  console.log('\n===== PASO 2: DESCARGAR ARCHIVO DE EXPORTACIÓN =====');
  console.log(`Intentando descargar archivo desde: ${url}`);
  
  const downloadPath = path.join(config.exportDir, `export_file_${runId}.zip`);
  console.log(`El archivo se guardará en: ${downloadPath}`);
  
  try {
    // Método 1: Intentar descarga directa con axios
    console.log('\n--- Método 1: Descarga directa ---');
    try {
      const response = await axios({
        method: 'GET',
        url,
        responseType: 'arraybuffer',
        timeout: 60000 // 1 minuto de timeout
      });
      
      fs.writeFileSync(downloadPath, response.data);
      console.log(`Descarga exitosa. Archivo guardado en: ${downloadPath}`);
      return { success: true, method: 'direct', filePath: downloadPath };
    } catch (directError) {
      console.log(`Error en descarga directa: ${directError.message}`);
      
      if (directError.response) {
        console.log(`Código de estado: ${directError.response.status}`);
      }
      
      console.log('Intentando con AWS SDK...');
    }
    
    // Método 2: Usar AWS SDK
    console.log('\n--- Método 2: AWS SDK ---');
    
    // Extraer información del bucket y key de la URL
    const s3UrlObj = new URL(url);
    const bucketName = s3UrlObj.hostname.split('.')[0];
    const objectKey = s3UrlObj.pathname.substring(1); // Quitar el slash inicial
    
    console.log(`Bucket: ${bucketName}`);
    console.log(`Key: ${objectKey}`);
    
    // Configurar AWS SDK
    const s3 = new AWS.S3({
      region: config.awsRegion,
      accessKeyId: config.awsAccessKeyId,
      secretAccessKey: config.awsSecretAccessKey
    });
    
    // Descargar usando AWS SDK
    const data = await s3.getObject({
      Bucket: bucketName,
      Key: objectKey
    }).promise();
    
    fs.writeFileSync(downloadPath, data.Body);
    console.log(`Descarga exitosa con AWS SDK. Archivo guardado en: ${downloadPath}`);
    
    return { success: true, method: 'aws', filePath: downloadPath };
  } catch (error) {
    console.error('Error al descargar archivo:', error.message);
    
    if (error.code === 'AccessDenied') {
      console.log('\n===== ERROR DE ACCESO DENEGADO =====');
      console.log('No se pudo acceder al archivo en S3. Posibles razones:');
      console.log('1. La URL ha expirado (suelen durar pocas horas)');
      console.log('2. No tienes permisos para acceder al bucket');
      console.log('3. Las credenciales de AWS no son correctas');
    }
    
    return { success: false, error: error.message };
  }
}

/**
 * Paso 3: Extraer archivos del ZIP
 * @param {string} zipPath - Ruta al archivo ZIP
 * @returns {Promise<object>} - Información sobre la extracción
 */
async function extraerArchivos(zipPath) {
  console.log('\n===== PASO 3: EXTRAER ARCHIVOS =====');
  console.log(`Extrayendo archivos de: ${zipPath}`);
  
  try {
    const extractDir = path.join(config.exportDir, `extract_${runId}`);
    
    // Crear directorio si no existe
    if (!fs.existsSync(extractDir)) {
      fs.mkdirSync(extractDir, { recursive: true });
    }
    
    // Extraer archivos
    const zip = new AdmZip(zipPath);
    zip.extractAllTo(extractDir, true);
    
    // Listar archivos extraídos
    const files = fs.readdirSync(extractDir);
    console.log(`Se extrajeron ${files.length} archivos en: ${extractDir}`);
    
    return { success: true, extractDir, files, totalFiles: files.length };
  } catch (error) {
    console.error('Error al extraer archivos:', error.message);
    return { success: false, error: error.message };
  }
}

/**
 * Paso 4: Procesar los archivos extraídos
 * @param {string} extractDir - Directorio con los archivos extraídos
 * @param {number} maxUsers - Número máximo de usuarios a procesar
 * @returns {Promise<object>} - Información sobre el procesamiento
 */
async function procesarArchivos(extractDir, maxUsers = config.maxUsers) {
  console.log('\n===== PASO 4: PROCESAR ARCHIVOS =====');
  console.log(`Procesando archivos en: ${extractDir}`);
  
  try {
    // Verificar que el directorio existe
    if (!fs.existsSync(extractDir)) {
      throw new Error(`El directorio ${extractDir} no existe`);
    }
    
    // Archivo de salida
    const baseOutputFile = path.join(config.exportDir, `usuarios_procesados_${runId}`);
    const infoOutputFile = `${baseOutputFile}_info.json`;
    console.log(`La información se guardará en: ${infoOutputFile}`);
    
    // Obtener lista de archivos
    const files = fs.readdirSync(extractDir).filter(file => file.endsWith('.txt'));
    console.log(`Se encontraron ${files.length} archivos para procesar`);
    
    // Inicializar contador de usuarios
    let totalUsuarios = 0;
    let archivosProcesados = 0;
    let partCounter = 1;
    let usuariosEnParte = 0;
    const USUARIOS_POR_ARCHIVO = 1000000; // Máximo de usuarios por archivo para evitar problemas de memoria
    
    // Información de los archivos generados
    const archivosGenerados = [];
    
    // Actual archivo de salida para usuarios
    let currentOutputFile = `${baseOutputFile}_part${partCounter}.json`;
    console.log(`Escribiendo usuarios en: ${currentOutputFile}`);
    
    // Iniciar archivo JSON con apertura de array y formato adecuado
    fs.writeFileSync(currentOutputFile, '[\n', 'utf8');
    
    // Procesar cada archivo
    for (const file of files) {
      archivosProcesados++;
      const filePath = path.join(extractDir, file);
      console.log(`Procesando archivo: ${file} (${archivosProcesados}/${files.length})`);
      
      // Crear interfaz de lectura de líneas
      const fileStream = fs.createReadStream(filePath);
      const rl = readline.createInterface({
        input: fileStream,
        crlfDelay: Infinity
      });
      
      // Procesar línea por línea
      for await (const line of rl) {
        if (line.trim()) {
          try {
            // Parsear la línea como JSON
            const userData = JSON.parse(line);
            
            // Escribir el usuario al archivo con formato más legible
            // Usar JSON.stringify con indentación de 2 espacios para mejor legibilidad
            const userStr = JSON.stringify(userData, null, 2);
            
            // Agregar coma si no es el primer usuario en el archivo
            const prefix = usuariosEnParte > 0 ? ',\n' : '';
            fs.appendFileSync(currentOutputFile, `${prefix}${userStr}`, 'utf8');
            
            // Incrementar contadores
            totalUsuarios++;
            usuariosEnParte++;
            
            // Mostrar progreso
            if (totalUsuarios % 10000 === 0) {
              console.log(`Procesados ${totalUsuarios} usuarios...`);
            }
            
            // Si alcanzamos el límite de usuarios por archivo, cerrar este y abrir uno nuevo
            if (usuariosEnParte >= USUARIOS_POR_ARCHIVO) {
              // Cerrar array JSON
              fs.appendFileSync(currentOutputFile, '\n]', 'utf8');
              
              // Registrar archivo completado
              archivosGenerados.push({
                archivo: currentOutputFile,
                usuarios: usuariosEnParte
              });
              
              // Incrementar contador de partes y reiniciar contador de usuarios por parte
              partCounter++;
              usuariosEnParte = 0;
              
              // Crear nuevo archivo
              currentOutputFile = `${baseOutputFile}_part${partCounter}.json`;
              console.log(`Continuando con nuevo archivo: ${currentOutputFile}`);
              fs.writeFileSync(currentOutputFile, '[\n', 'utf8');
            }
            
            // Limitar el número total de usuarios
            if (totalUsuarios >= maxUsers) {
              console.log(`Se alcanzó el límite de ${maxUsers} usuarios. Deteniendo procesamiento.`);
              break;
            }
          } catch (e) {
            console.warn(`Error al parsear línea en ${file}: ${e.message}`);
          }
        }
      }
      
      // Cerrar el stream
      fileStream.close();
      
      // Si alcanzamos el límite, salir del bucle
      if (totalUsuarios >= maxUsers) {
        break;
      }
    }
    
    // Cerrar el último archivo JSON si tiene usuarios
    if (usuariosEnParte > 0) {
      fs.appendFileSync(currentOutputFile, '\n]', 'utf8');
      
      // Registrar último archivo
      archivosGenerados.push({
        archivo: currentOutputFile,
        usuarios: usuariosEnParte
      });
    }
    
    console.log(`Procesamiento completado. Total de usuarios: ${totalUsuarios}`);
    
    // Crear archivo de información
    const resultado = {
      info: {
        fecha_procesamiento: moment().format('YYYY-MM-DD HH:mm:ss'),
        total_usuarios: totalUsuarios,
        archivos_procesados: files.length,
        archivos_generados: archivosGenerados,
        run_id: runId
      }
    };
    
    // Guardar información en archivo JSON
    fs.writeFileSync(infoOutputFile, JSON.stringify(resultado, null, 2));
    console.log(`Información guardada en: ${infoOutputFile}`);
    
    // Generar estadísticas básicas
    console.log('\n===== RESUMEN =====');
    console.log(`Total de archivos de datos generados: ${archivosGenerados.length}`);
    console.log(`Total de usuarios procesados: ${totalUsuarios}`);
    
    return {
      success: true,
      totalUsuarios,
      archivos_procesados: files.length,
      archivos_generados: archivosGenerados,
      infoOutputFile
    };
  } catch (error) {
    console.error('Error durante el procesamiento:', error);
    return {
      success: false,
      error: error.message
    };
  }
}

/**
 * Proceso completo: desde solicitar la exportación hasta procesar los archivos
 * @param {string} segmentId - ID del segmento a exportar
 * @param {number} waitTime - Tiempo de espera en segundos antes de descargar
 * @returns {Promise<object>} - Resultado del proceso completo
 */
async function procesoCompleto(segmentId = config.allUsersSegmentId, waitTime = 300) {
  console.log('======================================================');
  console.log('INICIANDO PROCESO COMPLETO DE EXPORTACIÓN Y PROCESAMIENTO');
  console.log('======================================================');
  console.log(`ID del segmento: ${segmentId}`);
  console.log(`Tiempo de espera: ${waitTime} segundos`);
  console.log(`ID de ejecución: ${runId}`);
  console.log('------------------------------------------------------');
  
  try {
    // Paso 1: Solicitar exportación
    const solicitudResult = await solicitarExportacion(segmentId);
    if (!solicitudResult.success) {
      throw new Error(`Error al solicitar la exportación: ${solicitudResult.error}`);
    }
    
    // Obtener URL de la exportación
    const exportUrl = solicitudResult.exportResponse.url;
    
    if (!exportUrl) {
      console.log('No se proporcionó una URL directa para la descarga.');
      console.log('La exportación se guardará en el bucket de S3 con el prefijo:');
      console.log(solicitudResult.exportResponse.object_prefix);
      console.log('\nDebes proporcionar manualmente la URL para continuar.');
      
      return {
        success: true,
        message: 'Solicitud de exportación completada pero se requiere la URL de descarga para continuar',
        exportInfo: solicitudResult.exportInfo,
        nextSteps: [
          'Obtener la URL del bucket de S3 cuando la exportación esté lista',
          `Ejecutar: node ${process.argv[1]} --download URL_DE_DESCARGA`
        ]
      };
    }
    
    // Esperar a que la exportación esté lista
    console.log(`\nEsperando ${waitTime} segundos para que la exportación esté lista...`);
    await new Promise(resolve => setTimeout(resolve, waitTime * 1000));
    
    // Paso 2: Descargar archivo
    console.log('\nContinuando con la descarga del archivo...');
    const descargaResult = await descargarArchivo(exportUrl);
    if (!descargaResult.success) {
      throw new Error(`Error al descargar el archivo: ${descargaResult.error}`);
    }
    
    // Paso 3: Extraer archivos
    const extractResult = await extraerArchivos(descargaResult.filePath);
    if (!extractResult.success) {
      throw new Error(`Error al extraer los archivos: ${extractResult.error}`);
    }
    
    // Paso 4: Procesar archivos
    const procesamientoResult = await procesarArchivos(extractResult.extractDir);
    if (!procesamientoResult.success) {
      throw new Error(`Error al procesar los archivos: ${procesamientoResult.error}`);
    }
    
    console.log('\n======================================================');
    console.log('PROCESO COMPLETO FINALIZADO CON ÉXITO');
    console.log('======================================================');
    console.log(`Total de usuarios procesados: ${procesamientoResult.totalUsuarios}`);
    console.log(`Información guardada en: ${procesamientoResult.infoOutputFile}`);
    if (procesamientoResult.archivos_generados && procesamientoResult.archivos_generados.length > 0) {
      console.log(`Se generaron ${procesamientoResult.archivos_generados.length} archivos con los datos de los usuarios`);
      procesamientoResult.archivos_generados.forEach((archivo, index) => {
        console.log(`  ${index + 1}. ${archivo.archivo} (${archivo.usuarios} usuarios)`);
      });
    }
    
    return {
      success: true,
      runId,
      solicitudResult,
      descargaResult,
      extractResult,
      procesamientoResult
    };
  } catch (error) {
    console.error('\n======================================================');
    console.error('ERROR EN EL PROCESO COMPLETO');
    console.error('======================================================');
    console.error(`Detalle del error: ${error.message}`);
    
    return {
      success: false,
      error: error.message,
      runId
    };
  }
}

/**
 * Ejecución principal basada en argumentos
 */
async function main() {
  const args = process.argv.slice(2);
  
  // Si no hay argumentos, mostrar ayuda
  if (args.length === 0) {
    console.log('======================================================');
    console.log('HERRAMIENTA DE EXPORTACIÓN DE USUARIOS DE BRAZE');
    console.log('======================================================');
    console.log('\nUso:');
    console.log('  node braze-export-tool.js [comando] [opciones]');
    console.log('\nComandos:');
    console.log('  --help                      Muestra esta ayuda');
    console.log('  --export [segmento_id]      Solicita una exportación de usuarios');
    console.log('  --download [url]            Descarga un archivo de exportación');
    console.log('  --extract [archivo_zip]     Extrae archivos de un ZIP');
    console.log('  --process [directorio]      Procesa los archivos extraídos');
    console.log('  --all [segmento_id]         Ejecuta todo el proceso completo');
    console.log('  --continue [url]            Continúa desde la URL de descarga hasta el procesamiento');
    console.log('\nEjemplos:');
    console.log('  node braze-export-tool.js --export');
    console.log('  node braze-export-tool.js --download https://bucket.s3.amazonaws.com/archivo.zip');
    console.log('  node braze-export-tool.js --extract ./exports/export_file.zip');
    console.log('  node braze-export-tool.js --process ./exports/extract_dir');
    console.log('  node braze-export-tool.js --all');
    console.log('  node braze-export-tool.js --continue https://bucket.s3.amazonaws.com/archivo.zip');
    return;
  }
  
  // Procesar comandos
  const comando = args[0];
  
  switch (comando) {
    case '--help':
      // Mostrar ayuda directamente, sin llamar a main() nuevamente
      console.log('======================================================');
      console.log('HERRAMIENTA DE EXPORTACIÓN DE USUARIOS DE BRAZE');
      console.log('======================================================');
      console.log('\nUso:');
      console.log('  node braze-export-tool.js [comando] [opciones]');
      console.log('\nComandos:');
      console.log('  --help                      Muestra esta ayuda');
      console.log('  --export [segmento_id]      Solicita una exportación de usuarios');
      console.log('  --download [url]            Descarga un archivo de exportación');
      console.log('  --extract [archivo_zip]     Extrae archivos de un ZIP');
      console.log('  --process [directorio]      Procesa los archivos extraídos');
      console.log('  --all [segmento_id]         Ejecuta todo el proceso completo');
      console.log('  --continue [url]            Continúa desde la URL de descarga hasta el procesamiento');
      console.log('\nEjemplos:');
      console.log('  node braze-export-tool.js --export');
      console.log('  node braze-export-tool.js --download https://bucket.s3.amazonaws.com/archivo.zip');
      console.log('  node braze-export-tool.js --extract ./exports/export_file.zip');
      console.log('  node braze-export-tool.js --process ./exports/extract_dir');
      console.log('  node braze-export-tool.js --all');
      console.log('  node braze-export-tool.js --continue https://bucket.s3.amazonaws.com/archivo.zip');
      break;
      
    case '--export':
      const segmentId = args[1] || config.allUsersSegmentId;
      await solicitarExportacion(segmentId);
      break;
      
    case '--download':
      if (!args[1]) {
        console.error('Error: Debes proporcionar una URL para descargar');
        console.log('Ejemplo: node braze-export-tool.js --download https://bucket.s3.amazonaws.com/archivo.zip');
        return;
      }
      await descargarArchivo(args[1]);
      break;
      
    case '--extract':
      if (!args[1]) {
        console.error('Error: Debes proporcionar la ruta al archivo ZIP');
        console.log('Ejemplo: node braze-export-tool.js --extract ./exports/export_file.zip');
        return;
      }
      await extraerArchivos(args[1]);
      break;
      
    case '--process':
      if (!args[1]) {
        console.error('Error: Debes proporcionar el directorio con los archivos extraídos');
        console.log('Ejemplo: node braze-export-tool.js --process ./exports/extract_dir');
        return;
      }
      const maxUsers = args[2] ? parseInt(args[2]) : config.maxUsers;
      await procesarArchivos(args[1], maxUsers);
      break;
      
    case '--all':
      const segmentoAll = args[1] || config.allUsersSegmentId;
      const waitTime = args[2] ? parseInt(args[2]) : 300; // 5 minutos por defecto
      await procesoCompleto(segmentoAll, waitTime);
      break;
      
    case '--continue':
      if (!args[1]) {
        console.error('Error: Debes proporcionar una URL para descargar');
        console.log('Ejemplo: node braze-export-tool.js --continue https://bucket.s3.amazonaws.com/archivo.zip');
        return;
      }
      
      // Ejecutar la secuencia de pasos desde la descarga hasta el procesamiento
      (async () => {
        try {
          console.log('======================================================');
          console.log('INICIANDO PROCESO DESDE DESCARGA HASTA PROCESAMIENTO');
          console.log('======================================================');
          console.log(`URL de descarga: ${args[1]}`);
          console.log(`ID de ejecución: ${runId}`);
          console.log('------------------------------------------------------');
          
          // Paso 1: Descargar archivo
          const descargaResult = await descargarArchivo(args[1]);
          if (!descargaResult.success) {
            throw new Error(`Error al descargar el archivo: ${descargaResult.error}`);
          }
          
          // Paso 2: Extraer archivos
          const extractResult = await extraerArchivos(descargaResult.filePath);
          if (!extractResult.success) {
            throw new Error(`Error al extraer los archivos: ${extractResult.error}`);
          }
          
          // Paso 3: Procesar archivos
          const maxUsers = args[2] ? parseInt(args[2]) : config.maxUsers;
          const procesamientoResult = await procesarArchivos(extractResult.extractDir, maxUsers);
          if (!procesamientoResult.success) {
            throw new Error(`Error al procesar los archivos: ${procesamientoResult.error}`);
          }
          
          console.log('\n======================================================');
          console.log('PROCESO COMPLETADO CON ÉXITO');
          console.log('======================================================');
          console.log(`Total de usuarios procesados: ${procesamientoResult.totalUsuarios}`);
          console.log(`Información guardada en: ${procesamientoResult.infoOutputFile}`);
          if (procesamientoResult.archivos_generados && procesamientoResult.archivos_generados.length > 0) {
            console.log(`Se generaron ${procesamientoResult.archivos_generados.length} archivos con los datos de los usuarios`);
            procesamientoResult.archivos_generados.forEach((archivo, index) => {
              console.log(`  ${index + 1}. ${archivo.archivo} (${archivo.usuarios} usuarios)`);
            });
          }
        } catch (error) {
          console.error('\n======================================================');
          console.error('ERROR EN EL PROCESO');
          console.error('======================================================');
          console.error(`Detalle del error: ${error.message}`);
        }
      })();
      break;
      
    default:
      console.error(`Comando desconocido: ${comando}`);
      console.log('Usa --help para ver la lista de comandos disponibles');
  }
}

// Ejecutar el script
if (require.main === module) {
  main().catch(error => {
    console.error('Error en la ejecución principal:', error);
    process.exit(1);
  });
} 