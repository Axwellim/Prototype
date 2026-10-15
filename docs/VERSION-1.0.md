# Versión 1.0.0

Primera versión del sistema de gestión documental del GAD Parroquial Rural de Imantag.

- Aplicación Laravel con PostgreSQL, carga e historial de documentos y eliminación lógica.
- Procesamiento automático de PDF e imágenes mediante servicio Python local.
- Conservación del PDF y transcripción por página, con recuperación del texto digital cuando es utilizable.
- OCR en español con tratamiento de plantillas, firmas, asuntos, párrafos y listas.
- Referencias humanas independientes y evaluación CER/WER para revisar resultados.

La instalación y las dependencias se describen en [EJECUCION.md](EJECUCION.md). La precisión depende del documento; los ejemplos usados para ajustar heurísticas no sustituyen una evaluación independiente.

El repositorio excluye configuraciones locales, contraseñas, documentos cargados, transcripciones de diagnóstico, bases de datos, sesiones, cachés, dependencias instaladas y herramientas privadas. Los archivos `.env.example` contienen las variables necesarias sin credenciales.

Identificador de versión: `1.0.0`. Etiqueta Git prevista: `v1.0.0`. Este archivo no acredita por sí mismo una publicación en GitHub: la publicación requiere crear el commit y enviar la rama y etiqueta al repositorio remoto.
