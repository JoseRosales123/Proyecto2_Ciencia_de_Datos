# Modelo Dimensional - Red Metropolitana de Transporte

## 1. Diseño general

La capa Gold utiliza un modelo dimensional con dos procesos de negocio
diferentes debido a que los operadores no registran sus operaciones
con el mismo nivel de detalle.

Se definieron dos tablas de hechos:

- `fact_abordajes`
- `fact_viajes_metroriel`

Ambas comparten dimensiones conformadas.

---

# 2. Dimensiones

## dim_tiempo

Grano:

Una fila por día.

Llave:

`tiempo_key`

Jerarquía:

Año → Trimestre → Mes → Día

Principales atributos:

- fecha
- año
- trimestre
- número de mes
- nombre de mes
- día del mes
- día de semana
- indicador de fin de semana

---

## dim_usuario

Grano:

Una fila por identidad integrada aproximada.

Llave:

`usuario_key`

La integración entre Transmetro, Transurbano y MetroRiel se realiza
utilizando el componente numérico de sus identificadores.

Aerómetro se conserva como una identidad independiente debido a que
su identificador es un hash y no existe una relación confiable con
los otros operadores.

La identidad debe considerarse aproximada y no confirmada.

---

## dim_zona

Grano:

Una fila por zona conformada.

Llave:

`zona_key`

Permite homologar diferentes representaciones territoriales utilizadas
por los operadores, por ejemplo:

- `Z10`
- `Zona 10`

ambas se representan finalmente como:

`Zona 10`

---

## dim_modo_transporte

Grano:

Una fila por modo de transporte.

Llave:

`modo_key`

Valores:

- Transmetro
- Transurbano
- MetroRiel
- Aerómetro

---

## dim_punto_servicio

Grano:

Una fila por estación o parada de un operador.

Llave:

`punto_servicio_key`

Incluye:

- 104 estaciones de Transmetro
- 328 paradas de Transurbano
- 22 estaciones de MetroRiel
- 14 estaciones de Aerómetro

Total:

468 puntos de servicio.

En MetroRiel esta dimensión cumple dos roles:

- punto de origen
- punto de destino

---

# 3. Tabla de hechos: fact_abordajes

## Grano

Una fila representa un abordaje válido.

Incluye:

- Transmetro
- Transurbano
- Aerómetro

No se construye artificialmente un viaje origen-destino para estos
operadores porque sus archivos solamente registran el abordaje.

## Llaves dimensionales

- modo_key
- usuario_key
- tiempo_key
- zona_key
- punto_servicio_key

## Medidas

### cantidad_abordajes

Tipo:

Aditiva.

Valor:

1 por cada fila.

Puede sumarse por cualquier dimensión.

### tarifa_gtq

Tipo:

Aditiva.

Representa el monto pagado en quetzales.

## Volumen

Total de abordajes:

1,393,448

Distribución:

- Aerómetro: 203,554
- Transmetro: 362,106
- Transurbano: 827,788

---

# 4. Tabla de hechos: fact_viajes_metroriel

## Grano

Una fila representa un viaje completo válido de MetroRiel.

## Llaves dimensionales

- modo_key
- usuario_key
- tiempo_key
- punto_origen_key
- punto_destino_key
- zona_origen_key
- zona_destino_key

## Medidas

### cantidad_viajes

Tipo:

Aditiva.

Valor:

1 por cada viaje.

### tarifa_gtq

Tipo:

Aditiva.

Representa el monto pagado por el viaje.

### duracion_segundos

Tipo:

Aditiva para acumulaciones.

También puede utilizarse para obtener medidas derivadas como:

- duración promedio
- duración mínima
- duración máxima

## Volumen

Total de viajes válidos:

295,511

---

# 5. Diagrama lógico

```mermaid
erDiagram

    DIM_TIEMPO ||--o{ FACT_ABORDAJES : fecha
    DIM_USUARIO ||--o{ FACT_ABORDAJES : usuario
    DIM_ZONA ||--o{ FACT_ABORDAJES : zona
    DIM_MODO_TRANSPORTE ||--o{ FACT_ABORDAJES : modo
    DIM_PUNTO_SERVICIO ||--o{ FACT_ABORDAJES : punto

    DIM_TIEMPO ||--o{ FACT_VIAJES_METRORIEL : fecha
    DIM_USUARIO ||--o{ FACT_VIAJES_METRORIEL : usuario
    DIM_MODO_TRANSPORTE ||--o{ FACT_VIAJES_METRORIEL : modo

    DIM_PUNTO_SERVICIO ||--o{ FACT_VIAJES_METRORIEL : origen
    DIM_PUNTO_SERVICIO ||--o{ FACT_VIAJES_METRORIEL : destino

    DIM_ZONA ||--o{ FACT_VIAJES_METRORIEL : zona_origen
    DIM_ZONA ||--o{ FACT_VIAJES_METRORIEL : zona_destino