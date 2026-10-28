# Arquitectura - Fase 1
## Agencia Metropolitana de Transporte

La arquitectura se divide en tres mecanismos de ingesta según la naturaleza de cada fuente.

## 1. Streaming - Kafka

Se utilizará Kafka para simular fuentes que en un entorno real producirían
eventos de forma continua.

Fuentes:

- transmetro_validaciones.csv
- aerometro_boardings.csv

Los archivos se publicarán línea por línea hacia Kafka para representar
la llegada continua de validaciones y abordajes.

## 2. Batch

Se utilizará carga Batch para fuentes que se reciben completas o que
cambian con poca frecuencia.

Fuentes:

- tm_estaciones.csv
- tu_paradas.csv
- mr_estaciones.csv
- am_estaciones.csv
- metroriel_viajes.jsonl
- transurbano_transacciones.csv

### Decisión sobre Transurbano

Transurbano se procesará mediante Batch.

Aunque las transacciones podrían producirse continuamente en un sistema
real, el archivo proporcionado para este proyecto corresponde a un
extracto CSV completo.

Esta decisión simplifica el proceso de ingesta y permite diferenciar
claramente las fuentes de streaming de las cargas periódicas.

La principal consecuencia es una menor frescura de los datos de
Transurbano, ya que estos estarán disponibles después de cada ejecución
Batch y no inmediatamente después de cada transacción.

## 3. CDC

Fuente:

- cdc_padron_usuarios.csv

El archivo se procesará respetando la secuencia de las operaciones:

- INSERT
- UPDATE
- DELETE

Los registros DELETE no se eliminarán físicamente. La tarjeta será
marcada como inactiva para conservar el historial de viajes.

## 4. Capa Bronze

Todos los datos ingresados serán almacenados en Bronze conservando el
contenido original.

Bronze tendrá:

- datos sin transformación de negocio;
- fecha y hora de ingesta;
- particionamiento por fecha;
- acumulación histórica.

La carpeta de staging será temporal, mientras que Bronze conservará el
historial de las cargas.

## Flujo general

Fuentes
   |
   +-- Streaming (Kafka) --------+
   |                              |
   +-- Batch ---------------------+--> Bronze --> Staging --> Silver --> Gold
   |                              |
   +-- CDC -----------------------+

Gold nunca leerá directamente desde Bronze.