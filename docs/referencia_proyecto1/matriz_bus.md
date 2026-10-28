# Matriz del Bus - Red Metropolitana de Transporte

## Definición de grano

Se utilizarán dos procesos de negocio debido a que los operadores
no registran el movimiento con el mismo nivel de detalle.

### 1. Abordajes

Una fila representa un abordaje realizado por un usuario en un
punto de servicio, fecha y hora determinados.

Incluye:

- Transmetro
- Transurbano
- Aerómetro

Estos sistemas no ofrecen información suficiente para representar
un viaje completo origen-destino.

### 2. Viajes MetroRiel

Una fila representa un viaje completo realizado por un usuario.

Incluye:

- estación de origen;
- estación de destino;
- hora de entrada;
- hora de salida;
- duración;
- tarifa.

## Matriz del Bus

| Proceso de negocio | Usuario | Tiempo | Zona | Modo | Punto de servicio | Línea/Ruta | Origen | Destino |
|---|---|---|---|---|---|---|---|---|
| Abordajes Transmetro | X | X | X | X | X | X | | |
| Abordajes Transurbano | X | X | X | X | X | X | | |
| Abordajes Aerómetro | X | X | X | X | X | X | | |
| Viajes MetroRiel | X | X | X | X | X | | X | X |

## Dimensiones conformadas

### dim_usuario
Representa la estrategia aproximada de identidad construida en Silver.

### dim_tiempo
Dimensión calendario compartida por ambos procesos.

### dim_zona
Homologa la nomenclatura territorial entre operadores.

### dim_modo_transporte
Permite identificar Transmetro, Transurbano, MetroRiel y Aerómetro.

### dim_punto_servicio
Representa estaciones y paradas.

Para MetroRiel se utilizará la misma dimensión con dos roles:

- punto de origen;
- punto de destino.

## Tablas de hechos

### fact_abordajes

Grano:

Una fila por abordaje válido.

Fuentes:

- Transmetro
- Transurbano
- Aerómetro

### fact_viajes_metroriel

Grano:

Una fila por viaje completo válido de MetroRiel.

## Clasificación preliminar de medidas

### fact_abordajes

- cantidad_abordajes: aditiva
- tarifa_gtq: aditiva

### fact_viajes_metroriel

- cantidad_viajes: aditiva
- tarifa_gtq: aditiva
- duracion_segundos: aditiva para acumulación, aunque su promedio
  también será una medida analítica relevante.