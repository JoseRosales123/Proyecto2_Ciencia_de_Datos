# Estrategia de identidad de usuarios

Los cuatro operadores utilizan identificadores diferentes y no existe una
tabla oficial que permita relacionar directamente las tarjetas de una misma
persona.

Por esta razón, la integración de identidad se considera una aproximación
y no una identidad confirmada.

## Estrategia utilizada

Para Transmetro, Transurbano y MetroRiel se utilizará el componente numérico
de la llave como identificador aproximado.

Ejemplos:

- TC-00012345  -> N:12345
- 0000012345   -> N:12345
- MR0012345    -> N:12345

La coincidencia del componente numérico se tratará como una relación
probable entre tarjetas de diferentes operadores.

Para Aerómetro no existe un componente reversible equivalente, ya que la
llave entregada corresponde a un hash.

Por lo tanto, sus usuarios se conservarán como identidades independientes:

- abc123def456 -> AM:abc123def456

## Supuesto

Se asume que un mismo componente numérico en Transmetro, Transurbano y
MetroRiel puede representar a la misma persona.

Este supuesto sirve para realizar análisis multimodales dentro del proyecto,
pero no debe interpretarse como una identidad confirmada.

## Limitaciones

- No existe una tabla maestra que confirme la relación.
- Dos operadores podrían reutilizar números de tarjeta para personas distintas.
- Los usuarios de Aerómetro no pueden relacionarse de forma confiable con los
  demás operadores.
- En un sistema real sería necesario contar con una llave maestra, proceso de
  conciliación o mecanismo institucional de identidad.

## Principio aplicado

Se prefiere mantener una identidad separada cuando no existe evidencia
suficiente antes que inventar una relación entre usuarios.