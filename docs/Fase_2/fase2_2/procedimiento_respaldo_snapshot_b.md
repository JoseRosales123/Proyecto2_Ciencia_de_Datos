# Procedimiento propuesto: respaldo lógico consistente del snapshot P2

## Estado y alcance

**DOCUMENTO PARA REVISIÓN. Estado actualizado con resultados comunicados el 11 de noviembre de 2026.**

### Respaldo existente: registro documental, restauración pendiente

El usuario confirmó un respaldo lógico `pg_dump -Fc` con identificador
`20261111T060925Z_3dfebab0`, creado el **2026-11-11 06:09:25 UTC** según el catálogo.
Su ubicación privada es
`C:\Respaldos_Privados_P2\20261111T060925Z_3dfebab0\postgres_p2.dump`,
con manifiesto privado `manifiesto.json`. Tamaño: **313537281 bytes**. SHA256:
`3c744ae115df1fab32b67dc5d5c9fc1474be1791a721720a94aa64b4c5721a37`.
Se confirmó coincidencia de tamaño y SHA256 entre Docker y Windows. Esta revisión
registra esos resultados comunicados; no abrió el respaldo ni el manifiesto, no
recalculó sus hashes y no ejecutó los bloques operativos de este documento.

**Catálogo legible frente a restauración comprobada.** Se confirmó que
`pg_restore --list` reconoce la base `red_metropolitana_p2`, 97 entradas TOC y
compresión gzip. Esto acredita lectura del catálogo del archivo; no demuestra que
todos los datos puedan recuperarse ni que una base restaurada sea válida.
La restauración completa **no se ejecutó**: estado **RESTAURACION_PENDIENTE**.
Queda pendiente una prueba en destino aislado con comprobación de errores y
validación de la base recuperada, además de revisión de entorno/versiones,
advertencias, manifiesto y custodia.

El [descriptor borrador](descriptor_snapshot_b.borrador.json) incorpora esta referencia
en `respaldo_logico_referenciado`, separada de `evidencias`. El contrato documentado en
[modos de exportación](modos_exportacion_b.md) no admite esa ruta privada como evidencia
validable; no se amplían sus áreas permitidas. `identidad_fisica_snapshot.identificador_backup`
permanece nulo porque **no está demostrada la correspondencia del respaldo del 11 de
noviembre con el estado auditado el 10 de noviembre**. Se conserva el timestamp
histórico del descriptor; el SHA256 del dump no sustituye la huella canónica del descriptor.

Se mantienen `BORRADOR_NO_OPERATIVO`, `certificado_origen=false` y enmienda no aprobada.
Corte B no exportado ni evaluado según lo confirmado. No se crean actas ni
autorizaciones. Este registro no aprueba ni autoriza pasos posteriores.

### Antecedente de la revisión del procedimiento

El texto siguiente describe el alcance de la revisión previa a los resultados
comunicados; sus afirmaciones de no ejecución no describen el estado actual del respaldo.

**EN AQUELLA REVISIÓN NO SE EJECUTARON COMANDOS OPERATIVOS.**
No se creó un respaldo, directorio privado, reserva, acta ni autorización. No se
consultó PostgreSQL, ejecutó Docker, detuvo/reinició un contenedor ni modificó código,
datos, descriptor, política o resultados. En la revisión técnica solo se corrige este documento.

El respaldo contendría registros individuales de las fuentes, aunque no construya
etiquetas B ni las muestre. Su creación y restauración requieren autorización
posterior explícita y custodia privada. No habilitan exportación ni evaluación B,
ni aprueban la enmienda. `certificado_origen=false` permanece vigente.

Configuración leída: `docker-compose.yml` declara PostgreSQL `16-alpine`, contenedor
`red_metropolitana_p2_postgres`, puerto host 5434 y volumen de datos persistente.
El orquestador espera `proyecto2_ciencia_datos_postgres_data`; no es un volumen
versionado. `profiles.yml` usa la misma conexión configurable mediante entorno.
No se mostró `.env` ni se verificó el estado real de Docker/PostgreSQL.

**Selección de variante:** las secciones 1–6 conservan la alternativa con clientes
Windows. La sección 7 incorpora la variante Docker, adecuada al estado comunicado:
Docker 29.6.1/Compose 5.3.0, contexto desktop-linux, origen healthy y clientes 16.14
dentro del contenedor; no hay pg_dump Windows. Esas verificaciones fueron comunicadas
por el usuario, no ejecutadas nuevamente aquí. La cifra de 160.76 GB libres en C:
no sustituye verificar espacio al ejecutar ni acredita espacio en el filesystem Docker.
**No ejecutar ambas variantes ni toda la documentación secuencialmente.**

## Hallazgos de la revisión técnica y correcciones documentales

| Sección | Hallazgo | Corrección aplicada / control aún pendiente |
|---|---|---|
| 1 y 3–5 | Windows PowerShell 5.1 trata stderr de ejecutables de manera distinta a errores de cmdlets; captura con `2>` y Stop no asegura llegar al control de ExitCode. | Helper Start-Process con streams privados, argumentos citados y ExitCode explícito para dump/listado/restauración. Pendiente prueba operacional autorizada. |
| 1–2 | Ruta textual fuera de Git no excluye junctions, otra raíz OneDrive o ACL amplia. Variables libpq/contexto Docker heredados pueden cambiar destino/opciones. | Rechazo de reparse points/UNC, comprobación de raíces cloud y ACL, sesión PG limpia y Docker Desktop local. Cifrado y custodia aún requieren revisión humana. |
| 2 | Template Docker con comillas dobles internas es frágil en el paso de argumentos nativos de PowerShell 5.1; puerto/montajes solo se mostraban. | Templates JSON sin comillas internas, parsing local y validaciones de proyecto, puerto y volumen. |
| 3 | Archivo binario: no se encontró corrupción de diseño. | Conservar pg_dump custom con --file; nunca redirigir su stdout binario a través de PowerShell. Logs son texto separado. |
| 3–5 | Algunos logs/catálogos podían sobrescribirse; restauración no tenía reserva propia. | Chequeos previos para cada salida y reserva de restauración CreateNew, nombres únicos y volumen etiquetado. Requiere un solo operador; API de volumen Docker no es creación exclusiva frente a otros administradores. |
| 5 | pg_isready puede responder durante inicialización temporal y no prueba que la base destino exista. | Verificar proceso principal postgres, disponibilidad y nombre real de base antes de restaurar. |
| 2 y 5 | Igual imagen no garantiza locale, extensiones instaladas o roles necesarios. | Registrar metadatos, cotejar locale, revisar versiones disponibles y comparar extensiones después de restaurar. Roles no globales del dump siguen sujetos a revisión de dependencias. |
| 2 | Ausencia de client backends no demuestra ausencia de todo escritor ni impide nuevas conexiones. | Ventana coordinada, permisos de observación, inventario de jobs/replicación/transacciones y barrera de acceso si se requiere. No se aplicó ningún cambio de acceso. |

No se confirma ausencia de riesgos operativos: los controles anteriores no han sido
ejecutados contra el entorno. Solo se ha revisado la sintaxis de los bloques mediante
el parser de PowerShell sin ejecutarlos, según el cierre de revisión de este documento.

## Prerrequisitos y decisiones antes de ejecutar

1. Autorizar específicamente una copia lógica de la base, custodia y comprobaciones
   técnicas de metadatos. La propuesta de aceptación limitada sigue sin aprobarse.
2. Identificar operador, equipo, base y contenedor correctos; no inferirlos solo del
   puerto. Revisar el commit y cualquier cambio local. No ejecutar orquestación,
   ingestas, CDC, Prefect o dbt para preparar el respaldo.
3. Para alternativa Windows: clientes PostgreSQL 16 en Windows. Para variante Docker:
   usar exclusivamente los clientes 16.14 internos según sección 7. En ambos casos,
   permisos suficientes para leer la base completa sin modificar sus tablas.
4. Autenticación no interactiva mediante archivo de contraseñas privado ya preparado,
   protegido con ACL para el operador. No poner contraseñas en comandos, URI, historial,
   manifiesto o logs. No imprimir `.env`, `docker inspect` completo ni variables de entorno.
5. Aprobar una carpeta privada local, fuera de Git y de sincronización OneDrive, en
   disco cifrado, con acceso limitado al operador/custodio. Proteger también logs,
   manifiesto, catálogo del archivo y cualquier copia/restauración.
6. Revisar las etapas de espacio y coordinación de escritores antes del dump. Una
   prueba de restauración exige espacio adicional en el almacenamiento de Docker,
   no únicamente en el disco que guarda el archivo.

Los bloques siguientes son PowerShell para una sesión futura controlada. No son un
script instalado ni una autorización; no ejecutarlos como un bloque ciego. Revisar
cada condición y conservar fallos sin sobrescribir ni borrar evidencias.

## 1. Preparación local, versión y destino privado

Este bloque futuro no conecta a PostgreSQL ni ejecuta Docker, pero sí crea una carpeta
privada y una reserva técnica. No fue ejecutado en este bloque documental.

```powershell
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0
# Esta sesión/procedimiento debe ser exclusivo; no pegar secciones aisladas con variables antiguas.
if ($env:OS -ne 'Windows_NT' -or $PSVersionTable.PSVersion -lt [Version]'5.1') {
  throw 'Procedimiento revisado para Windows PowerShell 5.1 o PowerShell Windows posterior'
}
$P2Repo = (Resolve-Path -LiteralPath '.').Path
if ((git rev-parse --show-toplevel).Trim() -ne $P2Repo.Replace('\','/')) {
  throw 'Ejecutar desde la raiz Git; revisar normalizacion de ruta si no coincide'
}
$P2Commit = (git rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'No se pudo identificar el commit' }
git status --short
if ($LASTEXITCODE -ne 0) { throw 'No se pudo revisar estado Git' }
# Revisar manualmente los cambios antes de continuar; no hacer add/commit/reset.
$P2RunId = [DateTime]::UtcNow.ToString('yyyyMMddTHHmmssZ') + '_' + [Guid]::NewGuid().ToString('N')
$P2PrivateRoot = Join-Path $env:LOCALAPPDATA 'Proyecto2Privado/respaldos'
if (-not (Test-Path -LiteralPath $P2PrivateRoot -PathType Container)) {
  throw 'La carpeta padre privada debe estar preparada y revisada previamente'
}
# Rechazar junctions/symlinks y ubicaciones UNC; una comparacion textual no los detecta.
$P2Ancestor = Get-Item -LiteralPath $P2PrivateRoot
while ($null -ne $P2Ancestor) {
  if (($P2Ancestor.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0) {
    throw 'Ruta privada redirigida: revisar antes de crear el respaldo'
  }
  $P2Ancestor = $P2Ancestor.Parent
}
$P2BackupDir = [IO.Path]::GetFullPath((Join-Path $P2PrivateRoot $P2RunId))
if ($P2BackupDir.StartsWith('\\') -or $P2BackupDir.Contains(',')) {
  throw 'Se requiere ruta local sin comas para el bind mount Docker'
}
$P2RepoPrefix = $P2Repo.TrimEnd('\') + '\'
if ($P2BackupDir.StartsWith($P2RepoPrefix, [StringComparison]::OrdinalIgnoreCase)) {
  throw 'El respaldo debe quedar fuera del repositorio'
}
foreach ($P2CloudRoot in @($env:OneDrive,$env:OneDriveConsumer,$env:OneDriveCommercial)) {
  if (-not $P2CloudRoot) { continue }
  $P2CloudPrefix = [IO.Path]::GetFullPath($P2CloudRoot).TrimEnd('\') + '\'
  if ($P2BackupDir.StartsWith($P2CloudPrefix, [StringComparison]::OrdinalIgnoreCase)) {
    throw 'El respaldo debe quedar fuera de OneDrive'
  }
}
if (Test-Path -LiteralPath $P2BackupDir) { throw 'Directorio previo: no reutilizar' }
# La carpeta padre debe tener previamente ACL privada y cifrado verificados.
New-Item -ItemType Directory -Path $P2BackupDir -ErrorAction Stop | Out-Null
Get-Acl -LiteralPath $P2BackupDir | Format-List Owner,AccessToString
$P2AllowedSids = @([Security.Principal.WindowsIdentity]::GetCurrent().User.Value,
                  'S-1-5-18','S-1-5-32-544') # operador, SYSTEM, administradores locales
$P2Acl = Get-Acl -LiteralPath $P2BackupDir
$P2AclRules = $P2Acl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
if (@($P2AclRules | Where-Object {
    $_.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow -and
    $P2AllowedSids -notcontains $_.IdentityReference.Value
  }).Count -gt 0 -or $P2AllowedSids -notcontains $P2Acl.GetOwner([Security.Principal.SecurityIdentifier]).Value) {
  throw 'ACL/propietario fuera de la lista aprobada; no continuar ni corregir automaticamente'
}
# Validar cifrado/custodia manualmente; ACL no limita a administradores del equipo.
$P2Partial = Join-Path $P2BackupDir 'snapshot.dump.partial'
$P2DumpFile = Join-Path $P2BackupDir 'snapshot.dump'
$P2DumpLog = Join-Path $P2BackupDir 'pg_dump.stderr.log'
$P2ManifestFile = Join-Path $P2BackupDir 'manifiesto_respaldo.json'
$P2Reservation = Join-Path $P2BackupDir 'reserva_respaldo.json'
$P2ReservationStream = [IO.File]::Open($P2Reservation, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write)
try {
  $P2ReservationBytes = [Text.UTF8Encoding]::new($false).GetBytes((@{
    id=$P2RunId; fecha_utc=[DateTime]::UtcNow.ToString('o'); commit=$P2Commit
    estado='RESERVADO_NO_FINALIZADO'; certificado_origen=$false
  } | ConvertTo-Json))
  $P2ReservationStream.Write($P2ReservationBytes,0,$P2ReservationBytes.Length)
  $P2ReservationStream.Flush($true)
} finally { $P2ReservationStream.Dispose() }
```

**Fin de preparación local compartida.** La variante Docker reutiliza solo el bloque
anterior y la definición de `Invoke-P2LoggedNative` más abajo; no ejecuta las búsquedas
de clientes Windows que siguen ni las consultas/comandos de las secciones 2–5.

**Continúa únicamente alternativa Windows:**

```powershell
$P2PgDump = (Get-Command pg_dump.exe -CommandType Application | Select-Object -First 1).Source
$P2PgRestore = (Get-Command pg_restore.exe -CommandType Application | Select-Object -First 1).Source
$P2Psql = (Get-Command psql.exe -CommandType Application | Select-Object -First 1).Source
$P2Docker = (Get-Command docker.exe -CommandType Application | Select-Object -First 1).Source
if ([IO.Path]::GetDirectoryName($P2PgDump) -ne [IO.Path]::GetDirectoryName($P2PgRestore) -or
    [IO.Path]::GetDirectoryName($P2PgDump) -ne [IO.Path]::GetDirectoryName($P2Psql)) {
  throw 'Clientes PostgreSQL de instalaciones distintas: revisar PATH'
}
$P2DumpVersion = (& $P2PgDump --version) -join ' '
if ($LASTEXITCODE -ne 0 -or $P2DumpVersion -notmatch 'PostgreSQL\) 16\.') {
  throw 'Se requiere pg_dump 16 revisado'
}
$P2RestoreVersion = (& $P2PgRestore --version) -join ' '
if ($LASTEXITCODE -ne 0 -or $P2RestoreVersion -notmatch 'PostgreSQL\) 16\.') {
  throw 'Se requiere pg_restore 16 revisado'
}
$P2ClientVersion = (& $P2Psql --version) -join ' '
if ($LASTEXITCODE -ne 0 -or $P2ClientVersion -notmatch 'PostgreSQL\) 16\.') {
  throw 'Se requiere psql 16 revisado'
}
```

La reserva es de respaldo, no la reserva del test B. Un fallo no autoriza reintento
automático ni sobrescritura: conservar parcial/logs, revisar y autorizar otra ejecución
si procede. No se incluyen instrucciones de eliminación de archivos/volúmenes.

En Windows PowerShell 5.1 no confiar solo en `$ErrorActionPreference` para programas
nativos: stderr puede convertirse en NativeCommandError y los códigos de salida
no equivalen a excepciones de cmdlets. Para dump/listado/restauración se usará esta
función futura, que captura streams fuera de PowerShell y lee ExitCode del proceso:

```powershell
function Invoke-P2LoggedNative {
  param([string]$FilePath,[string[]]$Arguments,[string]$Stdout,[string]$Stderr)
  foreach ($P2LogPath in @($Stdout,$Stderr)) {
    if (Test-Path -LiteralPath $P2LogPath) { throw 'Log previo: no sobrescribir' }
  }
  # ArgumentList de Start-Process se une como texto en 5.1: comillas explicitas.
  # Estos comandos fijos no necesitan argumentos con comillas, saltos o barra final.
  foreach ($P2Arg in $Arguments) {
    if ($P2Arg -match '["\r\n]' -or $P2Arg.EndsWith('\')) {
      throw 'Argumento no soportado por esta construccion revisada'
    }
  }
  $P2ArgumentText = ($Arguments | ForEach-Object { '"' + $_ + '"' }) -join ' '
  $P2Process = Start-Process -FilePath $FilePath -ArgumentList $P2ArgumentText `
    -WindowStyle Hidden -Wait -PassThru -RedirectStandardOutput $Stdout -RedirectStandardError $Stderr
  $P2Process.Refresh()
  if (-not $P2Process.HasExited -or $null -eq $P2Process.ExitCode) { throw 'Proceso sin salida verificable' }
  return $P2Process.ExitCode
}
```

El helper no se ejecutó ni se instaló como script. Sus prechequeos no son exclusión
atómica frente a un administrador: la carpeta única con reserva y ACL requiere un
solo operador y ningún proceso ajeno que cree archivos en ella.

## 2. Verificar entorno y coordinar ausencia de escritores

**Desde aquí hay comandos Docker y consultas de metadatos: requieren autorización
posterior y NO se ejecutaron.** No usar `docker compose config` ni inspección completa,
porque podrían revelar credenciales.

```powershell
$P2SourceContainer = 'red_metropolitana_p2_postgres'
# Contexto remoto + psql localhost podria respaldar una base distinta: bloquearlo.
if ($env:DOCKER_HOST -or $env:DOCKER_CONTEXT) { throw 'Overrides Docker presentes: revisar sin imprimirlos' }
$P2Context = (& $P2Docker context show).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Contexto Docker no identificado' }
$P2DockerEndpointJson = & $P2Docker context inspect --format '{{json .Endpoints.docker.Host}}' $P2Context
if ($LASTEXITCODE -ne 0) { throw 'Endpoint Docker no identificado' }
$P2DockerEndpoint = $P2DockerEndpointJson | ConvertFrom-Json
if (-not $P2DockerEndpoint.StartsWith('npipe://')) { throw 'Se requiere Docker Desktop local via named pipe' }
$P2ContainerId = (& $P2Docker inspect --format '{{.Id}}' $P2SourceContainer).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Contenedor origen no identificado' }
$P2LabelsJson = & $P2Docker inspect --format '{{json .Config.Labels}}' $P2SourceContainer
if ($LASTEXITCODE -ne 0) { throw 'Etiquetas Docker no identificadas' }
$P2Labels = $P2LabelsJson | ConvertFrom-Json
$P2ProjectLabel = $P2Labels.'com.docker.compose.project'
if ($P2ProjectLabel -ne 'proyecto2_ciencia_datos') {
  throw 'Entorno Docker distinto del proyecto esperado'
}
$P2ImageId = (& $P2Docker inspect --format '{{.Image}}' $P2SourceContainer).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Imagen no identificada' }
$P2Ports = @(& $P2Docker port $P2SourceContainer 5432/tcp)
if ($LASTEXITCODE -ne 0) { throw 'No se pudo verificar puerto' }
$P2MountsJson = & $P2Docker inspect --format '{{json .Mounts}}' $P2SourceContainer
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron verificar montajes' }
$P2Mounts = ConvertFrom-Json -InputObject ($P2MountsJson -join "`n")
$P2DataMounts = @($P2Mounts | Where-Object { $_.Destination -eq '/var/lib/postgresql/data' })
if (@($P2Ports | Where-Object { $_ -match ':5434$' }).Count -eq 0 -or
    $P2DataMounts.Count -ne 1 -or $P2DataMounts[0].Type -ne 'volume' -or
    $P2DataMounts[0].Name -ne 'proyecto2_ciencia_datos_postgres_data') {
  throw 'Puerto o volumen distinto del entorno aprobado'
}
# Imagen/ID/volumen identifican recursos; no son hashes del contenido de la base.
$P2Db = Read-Host 'Nombre de base P2 confirmado por el operador'
$P2User = Read-Host 'Rol autorizado para respaldo'
if ($P2Db -notmatch '^[A-Za-z_][A-Za-z0-9_]*$' -or $P2User -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
  throw 'Revisar nombres; no se admiten URI ni cadenas de conexion'
}
# PGPASSFILE debe apuntar a un archivo privado existente fuera del repositorio.
if (-not $env:PGPASSFILE -or -not (Test-Path -LiteralPath $env:PGPASSFILE -PathType Leaf)) {
  throw 'Falta archivo de autenticacion privado aprobado'
}
# libpq puede heredar PGHOSTADDR/PGSERVICE/PGOPTIONS/PGPASSWORD y otros defaults.
# No imprimir valores, ni limpiarlos automaticamente en una sesion de trabajo.
$P2UnexpectedPgNames = @(Get-ChildItem Env: | Where-Object { $_.Name -like 'PG*' -and $_.Name -ne 'PGPASSFILE' })
if ($P2UnexpectedPgNames.Count -gt 0) { throw 'Entorno PG heredado: usar sesion limpia revisada' }
$P2PassPath = [IO.Path]::GetFullPath($env:PGPASSFILE)
if ($P2PassPath.StartsWith($P2RepoPrefix,[StringComparison]::OrdinalIgnoreCase)) {
  throw 'Archivo de autenticacion dentro del repositorio'
}
# Verificar ACL y ausencia de redirecciones del archivo y sus ancestros como en seccion 1.
# No mostrar su contenido. No usar entradas wildcard para otros destinos sin revision.
$P2Connection = @('--host=127.0.0.1','--port=5434',"--username=$P2User", "--dbname=$P2Db",'--no-password')
$P2ServerVersion = (& $P2Psql @P2Connection -X -A -t -v ON_ERROR_STOP=1 -c 'SHOW server_version_num').Trim()
if ($LASTEXITCODE -ne 0 -or [int]$P2ServerVersion -lt 160000 -or [int]$P2ServerVersion -ge 170000) {
  throw 'Servidor no es PostgreSQL 16 o consulta fallo'
}
$P2DatabaseMetadataSql = @'
SELECT pg_encoding_to_char(encoding), datcollate, datctype,
       datlocprovider, COALESCE(daticulocale,''), COALESCE(datcollversion,'')
FROM pg_database WHERE datname = current_database();
'@
$P2DatabaseMetadata = (& $P2Psql @P2Connection -X -A -t -v ON_ERROR_STOP=1 -c $P2DatabaseMetadataSql).Trim()
if ($LASTEXITCODE -ne 0) { throw 'No se pudo registrar encoding/locale de origen' }
$P2ExtensionsMetadata = @(& $P2Psql @P2Connection -X -A -t -v ON_ERROR_STOP=1 `
  -c 'SELECT extname, extversion FROM pg_extension ORDER BY extname')
if ($LASTEXITCODE -ne 0) { throw 'No se pudo registrar extensiones de origen' }
```

Antes de fijar: el operador debe identificar todas las tareas Batch/CDC, ejecuciones
Prefect, dbt, scripts manuales, reintentos y planificadores externos; acordar una ventana
sin nuevas escrituras y esperar el término de trabajos/transacciones en curso. Si hay
programaciones automáticas, suspender sus disparadores solo bajo autorización específica,
sin detener ni reiniciar PostgreSQL/Kafka. No inventar nombres de deployments/jobs ni
ejecutar órdenes genéricas para pararlos. Registrar su estado y responsable de bloqueo.

Una verificación futura, sin leer tablas de negocio ni texto de consultas:

```powershell
$P2SessionCheck = @'
SELECT COUNT(*) AS otras_sesiones_cliente,
       COUNT(*) FILTER (WHERE xact_start IS NOT NULL) AS con_transaccion
FROM pg_stat_activity
WHERE datname = current_database()
  AND backend_type = 'client backend'
  AND pid <> pg_backend_pid();
'@
& $P2Psql @P2Connection -X -A -t -v ON_ERROR_STOP=1 -c $P2SessionCheck
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron revisar sesiones' }
```

Revisar manualmente que no existan clientes ajenos pendientes de resolución. Durante
el dump habrá su sesión; una supervisión autorizada debe distinguirla mediante metadatos
de aplicación y registrar incidentes, sin imprimir query, usuarios individuales o datos.
Los contadores y una observación puntual **no impiden conexiones/escrituras futuras**.
El rol supervisor debe poder observar las sesiones/transacciones relevantes (permisos
de monitorizacion aprobados); sin esa visibilidad no afirmar ausencia de escritores.
Incluir tambien transacciones preparadas, replicacion/suscripciones y jobs de extensiones
si existen: el conteo de client backends no cubre todos esos mecanismos.
Si se exige una barrera fuerte, habrá que aprobar previamente un control de acceso
de escritores diseñado para los roles reales; con roles compartidos/superusuario no
puede garantizarse solo cerrando una ventana de Prefect. No aplicar REVOKE, ALTER ROLE,
terminación de sesiones o cambios de configuración a ciegas.

`pg_dump` obtiene una copia consistente aun con escrituras concurrentes. La coordinación
adicional busca fijar una versión operativa sin cambios de esquema/ingesta, no atribuir
inmutabilidad al volumen. Si no puede acreditarse ausencia de escritores, registrarlo
y no afirmar que la base viva quedó congelada, aunque el archivo de respaldo sea consistente.

## 3. Espacio y respaldo custom

Consulta futura de tamaño de la base, no de registros de tablas:

```powershell
$P2DbSizeText = (& $P2Psql @P2Connection -X -A -t -v ON_ERROR_STOP=1 -c 'SELECT pg_database_size(current_database())').Trim()
if ($LASTEXITCODE -ne 0 -or $P2DbSizeText -notmatch '^\d+$') { throw 'Tamano de base no disponible' }
$P2DbBytes = [long]$P2DbSizeText
$P2Disk = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($P2BackupDir))
$P2FreeBefore = $P2Disk.AvailableFreeSpace
$P2RequiredBytes = [long](3 * $P2DbBytes + 1GB)
if ($P2FreeBefore -lt $P2RequiredBytes) { throw 'Espacio insuficiente segun margen operativo' }
```

Tres veces el tamaño más 1 GiB es una **política conservadora propuesta**, no una cota
matemática de pg_dump ni garantía de capacidad. Revisar cuotas, crecimiento y espacio
del disco real; no inferir espacio de Docker/VM a partir de este valor. No iniciar
una restauración sin un presupuesto separado para datos, índices, WAL y temporales.

```powershell
foreach ($P2Artifact in @($P2Partial,$P2DumpFile,$P2DumpLog,$P2ManifestFile)) {
  if (Test-Path -LiteralPath $P2Artifact) { throw 'Artefacto previo: no sobrescribir' }
}
$P2StartUtc = [DateTime]::UtcNow.ToString('o')
$P2DumpOut = Join-Path $P2BackupDir 'pg_dump.stdout.log'
$P2DumpExit = Invoke-P2LoggedNative -FilePath $P2PgDump `
  -Arguments ($P2Connection + @('--format=custom','--lock-wait-timeout=30s',"--file=$P2Partial")) `
  -Stdout $P2DumpOut -Stderr $P2DumpLog
$P2EndUtc = [DateTime]::UtcNow.ToString('o')
if ($P2DumpExit -ne 0) { throw 'pg_dump fallo; conservar parcial y log privado para revision' }
if (-not (Test-Path -LiteralPath $P2Partial -PathType Leaf)) { throw 'No existe archivo de respaldo' }
$P2DumpBytes = (Get-Item -LiteralPath $P2Partial).Length
if ($P2DumpBytes -le 0) { throw 'Respaldo vacio' }
$P2DumpSha = (Get-FileHash -LiteralPath $P2Partial -Algorithm SHA256).Hash.ToLowerInvariant()
$P2ArchiveList = Join-Path $P2BackupDir 'catalogo_archivo.txt'
$P2ArchiveLog = Join-Path $P2BackupDir 'pg_restore_list.stderr.log'
$P2ArchiveOut = Join-Path $P2BackupDir 'pg_restore_list.stdout.log'
if (Test-Path -LiteralPath $P2ArchiveList) { throw 'Catalogo previo: no sobrescribir' }
$P2ListExit = Invoke-P2LoggedNative -FilePath $P2PgRestore `
  -Arguments @('--list',"--file=$P2ArchiveList",$P2Partial) `
  -Stdout $P2ArchiveOut -Stderr $P2ArchiveLog
if ($P2ListExit -ne 0) { throw 'Archivo no supera lectura de catalogo; no aceptar respaldo' }
# Revisar warnings del dump y catalogo solo en privado, sin mostrar datos o adjuntar logs publicos.
# Un log no vacio no implica necesariamente error; cualquier warning exige clasificacion.
if (Test-Path -LiteralPath $P2DumpFile) { throw 'Destino final ya existe' }
Move-Item -LiteralPath $P2Partial -Destination $P2DumpFile -ErrorAction Stop
if ((Get-FileHash -LiteralPath $P2DumpFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $P2DumpSha) {
  throw 'Huella posterior a publicacion no coincide'
}
```

No usar `docker exec ... pg_dump > archivo` ni canalizar el stream binario a comandos
de texto PowerShell. `--file` hace que pg_dump escriba directamente el custom. La
carpeta única privada, reserva y controles de existencia evitan reutilización normal;
se requiere un único operador y ausencia de procesos que escriban en esa carpeta.
El comando no limita tablas: conserva una base completa, incluyendo las dependencias
de Staging/Silver/features ya existentes, sin calcular etiquetas B. No copia roles
globales del clúster ni pretende un respaldo físico de PGDATA.
Puede contener secretos almacenados en objetos de base, además de registros
individuales; por ejemplo, opciones de conexiones externas. Custodiar el archivo
completo como sensible aunque no se exporten contraseñas de roles globales.

## 4. Manifiesto técnico privado de respaldo

Solo tras salida 0, archivo no vacío y catálogo legible, producir un manifiesto nuevo
en la misma carpeta privada. No usar estado RESTAURACION_VALIDADA antes de probarla.

```powershell
$P2Manifest = [ordered]@{
  version=1; id=$P2RunId; tipo='PG_DUMP_CUSTOM_LOGICO'
  estado='RESPALDO_CREADO_RESTAURACION_PENDIENTE'
  inicio_utc=$P2StartUtc; fin_utc=$P2EndUtc; commit=$P2Commit
  entorno=[ordered]@{
    proyecto='proyecto2_ciencia_datos'; contenedor=$P2SourceContainer
    contenedor_id=$P2ContainerId; imagen_id=$P2ImageId
    host='127.0.0.1'; puerto=5434; base=$P2Db
    equipo=$env:COMPUTERNAME; volumen_declarado='proyecto2_ciencia_datos_postgres_data'
  }
  version_servidor_num=$P2ServerVersion; version_pg_dump=$P2DumpVersion
  version_pg_restore=$P2RestoreVersion; formato='custom'; pg_dump_exit=$P2DumpExit
  metadatos_base_encoding_locale=$P2DatabaseMetadata
  extensiones_origen=$P2ExtensionsMetadata
  contexto_docker=$P2Context; endpoint_docker=$P2DockerEndpoint
  control_escritores='PENDIENTE_REVISION_DEL_REGISTRO_PRIVADO_NO_APROBADO_AUTOMATICAMENTE'
  lectura_catalogo_exit=$P2ListExit; archivo='snapshot.dump'; bytes=$P2DumpBytes
  sha256_respaldo=$P2DumpSha; bytes_base_estimados=$P2DbBytes
  espacio_disponible_previo=$P2FreeBefore
  certificado_origen=$false; procedencia_generador='no_acreditada'
  aprobacion_enmienda='NO_ACREDITADA_POR_ESTE_RESPALDO'
  relacion_auditoria_20261110='NO_DEMOSTRADA; no afirma igualdad con snapshot de 04:06:49 UTC'
}
$P2ManifestStream = [IO.File]::Open($P2ManifestFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try {
  $P2ManifestBytes = [Text.UTF8Encoding]::new($false).GetBytes(($P2Manifest | ConvertTo-Json -Depth 8))
  $P2ManifestStream.Write($P2ManifestBytes,0,$P2ManifestBytes.Length)
  $P2ManifestStream.Flush($true)
} finally { $P2ManifestStream.Dispose() }
```

Este bloque no crea un acta de aprobación ni autorización. Antes de aceptar el
respaldo, un revisor debe adjuntar al registro privado el resultado real de coordinación
de escritores, warnings, identidad/montaje/puerto verificados y cadena de custodia.
Si falta algún control, conservar estado pendiente sin marcarlo como resuelto.
No guardar contraseñas, archivos pgpass, URI con credenciales o contenido individual
en el manifiesto. El inicio/fin delimita la captura: no es el identificador exacto
del snapshot MVCC interno de pg_dump ni el timestamp de otra auditoría.

## 5. Restauración futura aislada — autorización separada

Primero verificar espacio de la VM/disco Docker, huella del archivo y acceso al mismo
image ID de PostgreSQL 16. No crear bases en el contenedor actual ni usar su volumen.
Antes de ejecutar, revisar encoding/locale/proveedor de colacion y extensiones del
origen registrados en seccion 2. La misma imagen no garantiza el mismo locale de
initdb ni bibliotecas instaladas posteriormente en la capa escribible del contenedor.
El proyecto usa pgcrypto; confirmar que esa y las demas extensiones/versiones reales
estan disponibles. El dump no incluye sus binarios, roles globales ni configuracion
externa del servidor. Si hay dependencias ausentes, detenerse y revisar la imagen
aislada; no instalar paquetes ni cambiar origen automaticamente.
La prueba siguiente no publica puertos y usa `--network none` para impedir ingestas
externas. El acceso local de prueba usa trust **solo en ese contenedor nuevo aislado**;
no cambiar autenticación del origen ni reutilizar esta configuración para servicio.
Quien controla Docker ya puede acceder a los datos: limitar operadores del host.
`--no-owner --no-privileges` evita restaurar propietarios/ACL originales, pero no
elimina toda dependencia de roles (por ejemplo, nombres de roles en políticas RLS).
Revisar esas dependencias de metadatos antes de ejecutar y preparar, si hace falta,
solo roles mínimos sin LOGIN en el destino, mediante otro cambio aprobado. No copiar
contraseñas de roles ni crear equivalentes superusuario. La prueba no certifica
equivalencia de permisos de producción. El archivo restaurado ejecuta DDL/funciones
de su procedencia: aceptar solo el respaldo propio custodiado y revisar sus dependencias.

```powershell
if ((Get-FileHash -LiteralPath $P2DumpFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $P2DumpSha) {
  throw 'Respaldo alterado'
}
$P2RestoreName = 'p2_restore_' + $P2RunId
$P2RestoreVolume = 'p2_restore_data_' + $P2RunId
if ($P2RestoreName -eq $P2SourceContainer -or $P2RestoreVolume -eq 'proyecto2_ciencia_datos_postgres_data') {
  throw 'Destino no aislado'
}
$P2RestoreReservation = Join-Path $P2BackupDir 'reserva_restauracion.json'
$P2RestoreReservationStream = [IO.File]::Open($P2RestoreReservation,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try {
  $P2RestoreReservationBytes = [Text.UTF8Encoding]::new($false).GetBytes((@{
    estado='RESERVADA_NO_VALIDADA'; fecha_utc=[DateTime]::UtcNow.ToString('o')
    contenedor=$P2RestoreName; volumen=$P2RestoreVolume; respaldo_sha256=$P2DumpSha
  } | ConvertTo-Json))
  $P2RestoreReservationStream.Write($P2RestoreReservationBytes,0,$P2RestoreReservationBytes.Length)
  $P2RestoreReservationStream.Flush($true)
} finally { $P2RestoreReservationStream.Dispose() }
$P2ExistingContainers = @(& $P2Docker ps -a --format '{{.Names}}')
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron listar nombres de contenedores' }
$P2ExistingVolumes = @(& $P2Docker volume ls --format '{{.Name}}')
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron listar nombres de volumenes' }
if ($P2ExistingContainers -contains $P2RestoreName -or $P2ExistingVolumes -contains $P2RestoreVolume) {
  throw 'Nombre previo: no reutilizar'
}
& $P2Docker volume create --label 'uso=p2_prueba_restauracion' --label "run_id=$P2RunId" $P2RestoreVolume | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear volumen de prueba' }
$P2VolumeLabelsJson = & $P2Docker volume inspect --format '{{json .Labels}}' $P2RestoreVolume
if ($LASTEXITCODE -ne 0) { throw 'No se pudo identificar volumen de prueba' }
$P2VolumeLabels = $P2VolumeLabelsJson | ConvertFrom-Json
if ($P2VolumeLabels.run_id -ne $P2RunId -or $P2VolumeLabels.uso -ne 'p2_prueba_restauracion') {
  throw 'Volumen no pertenece a esta reserva'
}
& $P2Docker run --detach --name $P2RestoreName --network none `
  --mount "type=volume,source=$P2RestoreVolume,target=/var/lib/postgresql/data" `
  --mount "type=bind,source=$P2DumpFile,target=/backup/snapshot.dump,readonly" `
  --env POSTGRES_USER=postgres --env POSTGRES_DB=p2_snapshot_restore --env POSTGRES_HOST_AUTH_METHOD=trust `
  $P2ImageId | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'No se pudo crear instancia aislada' }
# Comprobar por separado, sin inspeccionar Config.Env ni usar comillas Go anidadas.
$P2RestoreActualName = (& $P2Docker inspect --format '{{.Name}}' $P2RestoreName).Trim()
if ($LASTEXITCODE -ne 0 -or $P2RestoreActualName -ne ('/' + $P2RestoreName)) { throw 'Contenedor inesperado' }
$P2RestoreNetwork = (& $P2Docker inspect --format '{{.HostConfig.NetworkMode}}' $P2RestoreName).Trim()
if ($LASTEXITCODE -ne 0 -or $P2RestoreNetwork -ne 'none') { throw 'Red de prueba no aislada' }
$P2RestorePortsJson = & $P2Docker inspect --format '{{json .HostConfig.PortBindings}}' $P2RestoreName
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron revisar puertos aislados' }
$P2RestorePorts = $P2RestorePortsJson | ConvertFrom-Json
if ($null -ne $P2RestorePorts -and @($P2RestorePorts.PSObject.Properties).Count -gt 0) {
  throw 'La instancia de prueba no debe publicar puertos'
}
$P2RestoreMountsJson = & $P2Docker inspect --format '{{json .Mounts}}' $P2RestoreName
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron revisar montajes aislados' }
$P2RestoreMounts = ConvertFrom-Json -InputObject ($P2RestoreMountsJson -join "`n")
$P2RestoreData = @($P2RestoreMounts | Where-Object { $_.Destination -eq '/var/lib/postgresql/data' })
$P2RestoreArchive = @($P2RestoreMounts | Where-Object { $_.Destination -eq '/backup/snapshot.dump' })
if ($P2RestoreData.Count -ne 1 -or $P2RestoreData[0].Name -ne $P2RestoreVolume -or
    $P2RestoreData[0].Type -ne 'volume' -or $P2RestoreArchive.Count -ne 1 -or
    $P2RestoreArchive[0].Type -ne 'bind' -or $P2RestoreArchive[0].RW -ne $false) {
  throw 'Montajes de prueba inesperados'
}
# Revisar ademas Source del bind (Docker Desktop puede normalizar su ruta Windows)
# y confirmar que corresponde al archivo con hash aprobado, nunca al PGDATA origen.
# pg_isready solo puede responder durante el servidor temporal de initdb: no basta.
$P2RestorePid1 = (& $P2Docker exec $P2RestoreName cat /proc/1/comm).Trim()
if ($LASTEXITCODE -ne 0 -or $P2RestorePid1 -ne 'postgres') {
  throw 'Inicializacion no finalizada: detener esta etapa, no repetir docker run'
}
& $P2Docker exec $P2RestoreName pg_isready -U postgres -d p2_snapshot_restore
if ($LASTEXITCODE -ne 0) { throw 'Instancia aislada no lista: no restaurar aun' }
$P2RestoreDb = (& $P2Docker exec $P2RestoreName psql -X -A -t -v ON_ERROR_STOP=1 `
  -U postgres -d p2_snapshot_restore -c 'SELECT current_database()').Trim()
if ($LASTEXITCODE -ne 0 -or $P2RestoreDb -ne 'p2_snapshot_restore') { throw 'Base de destino incorrecta' }
$P2RestoreMetadata = (& $P2Docker exec $P2RestoreName psql -X -A -t -v ON_ERROR_STOP=1 `
  -U postgres -d p2_snapshot_restore -c $P2DatabaseMetadataSql).Trim()
if ($LASTEXITCODE -ne 0 -or $P2RestoreMetadata -cne $P2DatabaseMetadata) {
  throw 'Encoding/locale/proveedor/version de colacion distintos: revisar inicializacion antes de restaurar'
}
# Consulta solo catalogo de extensiones disponibles; revisar privadamente contra origen.
& $P2Docker exec $P2RestoreName psql -X -A -t -v ON_ERROR_STOP=1 -U postgres `
  -d p2_snapshot_restore -c 'SELECT name, version FROM pg_available_extension_versions ORDER BY name, version'
if ($LASTEXITCODE -ne 0) { throw 'No se pudo verificar disponibilidad de extensiones' }
# DETENERSE para revisar que todas las extensiones/versiones necesarias son restaurables.
$P2RestoreOut = Join-Path $P2BackupDir 'restauracion.stdout.log'
$P2RestoreErr = Join-Path $P2BackupDir 'restauracion.stderr.log'
$P2RestoreExit = Invoke-P2LoggedNative -FilePath $P2Docker `
  -Arguments @('exec',$P2RestoreName,'pg_restore','--exit-on-error','--single-transaction',
               '--no-owner','--no-privileges','-U','postgres','-d','p2_snapshot_restore','/backup/snapshot.dump') `
  -Stdout $P2RestoreOut -Stderr $P2RestoreErr
if ($P2RestoreExit -ne 0) { throw 'Restauracion fallida: no repetir sobre esta base' }
$P2RestoredExtensions = @(& $P2Docker exec $P2RestoreName psql -X -A -t -v ON_ERROR_STOP=1 `
  -U postgres -d p2_snapshot_restore -c 'SELECT extname, extversion FROM pg_extension ORDER BY extname')
if ($LASTEXITCODE -ne 0 -or ($P2RestoredExtensions -join "`n") -cne ($P2ExtensionsMetadata -join "`n")) {
  throw 'Extensiones restauradas distintas de las registradas: no validar recuperabilidad'
}
```

Nunca añadir `--clean` o `--create`: aquí el destino es la base nueva explícita, y
`--create` podría redirigir al nombre almacenado en el archivo. No usar 5434 ni el
contenedor/volumen productivo para restaurar. No iniciar Prefect/dbt/CDC en la copia.

Restauración con salida 0 y sin incidencias pendientes acredita recuperabilidad técnica;
la lectura del catálogo por sí sola no la acredita. Documentar errores/warnings,
tablas/esquemas/índices/extensiones esperados y, solo con autorización posterior,
reconciliaciones agregadas en la copia, sin abrir filas/etiquetas. Registrar resultado
en **otro archivo privado nuevo**, ligado al SHA256 del respaldo y a IDs de contenedor,
imagen y volumen restaurados. No sobrescribir el manifiesto inicial para borrar historia.

Una instancia PostgreSQL en funcionamiento escribe archivos internos: no presentar
su volumen como inmutable ni montar PGDATA simplemente como read-only. Conservar
el archivo original como artefacto maestro protegido y restaurar siempre en una copia.
Antes de un eventual acceso del exportador habría que diseñar otra etapa de permisos
y conexión controlada a la copia: lectura de relaciones permanentes y capacidad de
crear las tablas temporales que su código requiere. No conectar ahora el exportador,
ni cambiar su .env, ni otorgar permisos o puertos adicionales mediante este procedimiento.

## 6. Vínculo con descriptor, custodia e inmutabilidad

Solo tras revisar respaldo y prueba de restauración, proponer una nueva versión del
descriptor borrador que referencie ID y SHA256 del respaldo, manifiesto, evidencia de
restauración, versiones/entorno y límites conocidos. No modificar el descriptor actual
automáticamente. Su contrato vigente admite evidencias agregadas y manifiestos en
áreas específicas; un respaldo privado fuera del repositorio **no se añade como ruta
de evidencia permitida ni se abre desde el validador**. Haría falta revisar cómo
referenciar un resumen técnico sin datos y ligar privadamente la custodia, antes de
considerarlo operativo; este documento no altera ese contrato.

La nueva copia fijaría el estado capturado durante el futuro pg_dump. No demuestra
igualdad con `2026-11-10T04:06:49.332515+00:00` ni recupera por sí sola ese momento.
Si se necesita tal vínculo, requerir evidencia histórica adicional o una nueva
comparación agregada autorizada, que tampoco prueba igualdad de contenido solo por conteos.
No atribuir al descriptor anterior una copia física que nunca se conservó.

El SHA256 identifica bytes y permite detectar cambios si se conserva una referencia
confiable; no impide modificación ni sustitución conjunta de archivo/manifiesto.
Usar ACL restrictiva, cifrado y copia custodiada; si se requiere inmutabilidad fuerte,
almacenamiento con retención/WORM y registro independiente de huellas. No confundir
atributo read-only de Windows o permisos del volumen con una garantía frente al administrador.

Fuera de Git deben permanecer `.dump`, `.partial`, logs, catálogo del archivo,
reserva/manifiestos técnicos privados, pgpass, cualquier copia de restauración y sus
volúmenes. El destino propuesto está fuera del árbol; no se modificó `.gitignore`.
Si se eligiera otro destino dentro del proyecto, detener y revisar exclusión efectiva
antes de crear nada; la regla local `datos_modelado_local/` no se propaga a otros clones.
No confiar en `*.log` para proteger un respaldo `.dump`, ni forzar git add.

Un respaldo verificable resuelve identidad de un artefacto y recuperabilidad; **no
certifica el origen, no cierra tardios y no aprueba la enmienda ni el test único**.

## 7. Variante Docker: dump interno y copia binaria con docker cp

### D0. Alcance y prerrequisitos adicionales

**PROPUESTA NO EJECUTADA.** Se requieren autorización expresa de respaldo y custodia,
coordinación de escritores de sección 2, aprobación del espacio, ACL/cifrado y revisión
de estos bloques. No ejecutar ingestas, restauraciones ni evaluación B. No detener
ni reiniciar el origen. Esta variante crea un archivo sensible temporal en `/tmp`
del contenedor y un archivo privado en Windows; no escribe en las tablas ni en PGDATA.

Usar de sección 1 **solo preparación local compartida hasta la reserva** y la
definición de `Invoke-P2LoggedNative`. No se necesita pg_dump, pg_restore ni psql en
Windows. Los nombres/variables de destino son los de ese bloque compartido, con un
UUID nuevo; no reutilizar una carpeta de otra variante o ejecución fallida.

No usar stdout para transferir el dump, `docker cp ... -`, `docker exec -t`, pipes de
texto, `Get-Content` sobre el dump ni redirecciones PowerShell para el binario.
`pg_dump --file` escribe dentro del contenedor y `docker cp` copia a un nombre de
archivo local explícito. Solo los logs/metadatos textuales pasan por stdout capturado.

### D1. Identidad del origen, herramientas y autenticación

Todos los comandos Docker siguientes son **futuros**. Helper con logs exclusivos:

```powershell
$P2Docker = (Get-Command docker.exe -CommandType Application | Select-Object -First 1).Source
$P2SourceContainer = 'red_metropolitana_p2_postgres'
$P2ExpectedImage = 'sha256:57c72fd2a128e416c7fcc499958864df5301e940bca0a56f58fddf30ffc07777'
function Invoke-P2DockerStep {
  param([string]$Step,[string[]]$Arguments)
  if ($Step -notmatch '^[a-z0-9_]+$') { throw 'Identificador de paso no valido' }
  $P2StepOut = Join-Path $P2BackupDir ($Step + '.stdout.log')
  $P2StepErr = Join-Path $P2BackupDir ($Step + '.stderr.log')
  $P2StepExit = Invoke-P2LoggedNative -FilePath $P2Docker -Arguments $Arguments `
    -Stdout $P2StepOut -Stderr $P2StepErr
  if ($P2StepExit -ne 0) { throw "Paso $Step fallo: conservar logs privados; no reintentar automaticamente" }
  return $P2StepOut
}
if ($env:DOCKER_HOST -or $env:DOCKER_CONTEXT) { throw 'Overrides Docker: revisar sin imprimir valores' }
$P2ContextLog = Invoke-P2DockerStep 'd_context' @('context','show')
$P2Context = (Get-Content -LiteralPath $P2ContextLog -Raw).Trim()
if ($P2Context -ne 'desktop-linux') { throw 'Contexto distinto del revisado' }
$P2EndpointLog = Invoke-P2DockerStep 'd_endpoint' @('context','inspect','--format','{{json .Endpoints.docker.Host}}',$P2Context)
$P2Endpoint = Get-Content -LiteralPath $P2EndpointLog -Raw | ConvertFrom-Json
if (-not $P2Endpoint.StartsWith('npipe://')) { throw 'Docker no es local al Windows que recibe la copia' }
$P2ContainerLog = Invoke-P2DockerStep 'd_container_id' @('inspect','--format','{{.Id}}',$P2SourceContainer)
$P2ContainerId = (Get-Content -LiteralPath $P2ContainerLog -Raw).Trim()
$P2ImageLog = Invoke-P2DockerStep 'd_image' @('inspect','--format','{{.Image}}',$P2SourceContainer)
$P2ImageId = (Get-Content -LiteralPath $P2ImageLog -Raw).Trim()
if ($P2ImageId -ne $P2ExpectedImage) { throw 'Imagen distinta: revisar antes de respaldar' }
$P2HealthLog = Invoke-P2DockerStep 'd_health' @('inspect','--format','{{.State.Health.Status}}',$P2SourceContainer)
if ((Get-Content -LiteralPath $P2HealthLog -Raw).Trim() -ne 'healthy') { throw 'Origen no healthy' }
$P2LabelsLog = Invoke-P2DockerStep 'd_labels' @('inspect','--format','{{json .Config.Labels}}',$P2SourceContainer)
$P2Labels = Get-Content -LiteralPath $P2LabelsLog -Raw | ConvertFrom-Json
if ($P2Labels.'com.docker.compose.project' -ne 'proyecto2_ciencia_datos') { throw 'Proyecto Docker distinto' }
$P2PortsLog = Invoke-P2DockerStep 'd_ports' @('port',$P2SourceContainer,'5432/tcp')
if (@(Get-Content -LiteralPath $P2PortsLog | Where-Object { $_ -match ':5434$' }).Count -eq 0) {
  throw 'Puerto distinto del declarado'
}
$P2MountsLog = Invoke-P2DockerStep 'd_mounts' @('inspect','--format','{{json .Mounts}}',$P2SourceContainer)
$P2DockerMounts = Get-Content -LiteralPath $P2MountsLog -Raw | ConvertFrom-Json
$P2DockerData = @($P2DockerMounts | Where-Object { $_.Destination -eq '/var/lib/postgresql/data' })
if ($P2DockerData.Count -ne 1 -or $P2DockerData[0].Type -ne 'volume' -or
    $P2DockerData[0].Name -ne 'proyecto2_ciencia_datos_postgres_data') { throw 'PGDATA no coincide' }
# --user postgres se refiere al usuario del SO del contenedor, no al rol SQL.
# env -i elimina defaults libpq heredados y contrasenas del entorno del proceso hijo.
$P2ExecTools = @('exec','--user','postgres',$P2ContainerId,
                'env','-i','PATH=/usr/local/bin:/usr/bin:/bin','LC_ALL=C')
$P2DumpVersionLog = Invoke-P2DockerStep 'd_pg_dump_version' ($P2ExecTools + @('pg_dump','--version'))
$P2RestoreVersionLog = Invoke-P2DockerStep 'd_pg_restore_version' ($P2ExecTools + @('pg_restore','--version'))
$P2DumpVersion = (Get-Content -LiteralPath $P2DumpVersionLog -Raw).Trim()
$P2RestoreVersion = (Get-Content -LiteralPath $P2RestoreVersionLog -Raw).Trim()
if ($P2DumpVersion -notmatch 'PostgreSQL\) 16\.14\b' -or $P2RestoreVersion -notmatch 'PostgreSQL\) 16\.14\b') {
  throw 'Herramientas distintas de 16.14: revisar cambio de entorno'
}
$P2Db = Read-Host 'Nombre de base P2 confirmado'
$P2User = Read-Host 'Rol SQL autorizado para respaldo'
if ($P2Db -notmatch '^[A-Za-z_][A-Za-z0-9_]*$' -or $P2User -notmatch '^[A-Za-z_][A-Za-z0-9_]*$') {
  throw 'Nombres no admitidos; no usar URI ni contrasenas'
}
$P2SocketConnection = @('--host=/var/run/postgresql',"--username=$P2User", "--dbname=$P2Db",'--no-password')
$P2ServerLog = Invoke-P2DockerStep 'd_server_version' ($P2ExecTools + @('psql') + $P2SocketConnection +
  @('-X','-A','-t','-v','ON_ERROR_STOP=1','-c','SHOW server_version_num'))
$P2ServerVersion = (Get-Content -LiteralPath $P2ServerLog -Raw).Trim()
if ($P2ServerVersion -notmatch '^16\d{4}$') { throw 'Servidor no es PostgreSQL 16' }
$P2DataDirectoryLog = Invoke-P2DockerStep 'd_data_directory' ($P2ExecTools + @('psql') + $P2SocketConnection +
  @('-X','-A','-t','-v','ON_ERROR_STOP=1','-c','SHOW data_directory'))
$P2ActualDataDirectory = (Get-Content -LiteralPath $P2DataDirectoryLog -Raw).Trim().TrimEnd('/')
if ($P2ActualDataDirectory -cne '/var/lib/postgresql/data') { throw 'Directorio real PostgreSQL distinto: revisar antes de crear temporales' }
```

La autenticación debe funcionar con la política existente del socket y el rol
autorizado, sin cambiar pg_hba.conf. No se usa POSTGRES_PASSWORD ni se muestran
variables/credenciales. Si se necesita contraseña, `--no-password` hace fallar el
paso: detener y preparar mediante otro cambio aprobado un pgpass interno privado,
legible solo por postgres, pasando únicamente su **ruta** a env -i. No improvisar
`--env PGPASSWORD=...`, trust en el origen ni secretos en argumentos/logs. La limpieza
de entorno solo afecta al proceso hijo, no a PostgreSQL ni a su contenedor.

### D2. Espacio host/contenedor y reserva temporal exclusiva

La observación de C: 160.76 GB libres es histórica; actualizarla antes de ejecutar.
`/tmp` puede usar el almacenamiento de la VM Docker y compartir capacidad física
con los volúmenes, aunque C: muestre espacio. No escribir el dump en PGDATA.

```powershell
$P2SizeLog = Invoke-P2DockerStep 'd_size' ($P2ExecTools + @('psql') + $P2SocketConnection +
  @('-X','-A','-t','-v','ON_ERROR_STOP=1','-c','SELECT pg_database_size(current_database())'))
$P2SizeText = (Get-Content -LiteralPath $P2SizeLog -Raw).Trim()
if ($P2SizeText -notmatch '^\d+$') { throw 'Tamano de base no verificable' }
$P2DbBytes = [long]$P2SizeText
$P2RequiredBytes = [long](3 * $P2DbBytes + 1GB)
$P2HostDisk = [IO.DriveInfo]::new([IO.Path]::GetPathRoot($P2BackupDir))
$P2FreeBefore = $P2HostDisk.AvailableFreeSpace
if ($P2FreeBefore -lt $P2RequiredBytes) { throw 'Espacio host insuficiente para margen acordado' }
$P2DfTmpLog = Invoke-P2DockerStep 'd_df_tmp' ($P2ExecTools + @('df','-Pk','/tmp'))
$P2DfDataLog = Invoke-P2DockerStep 'd_df_pgdata' ($P2ExecTools + @('df','-Pk','/var/lib/postgresql/data'))
function Get-P2AvailableBytesFromDf([string]$Path) {
  $P2DfLines = @(Get-Content -LiteralPath $Path | Where-Object { $_.Trim() })
  if ($P2DfLines.Count -ne 2) { throw 'Formato df inesperado: revisar manualmente' }
  $P2DfFields = $P2DfLines[1].Trim() -split '\s+'
  if ($P2DfFields.Count -lt 6 -or $P2DfFields[3] -notmatch '^\d+$') { throw 'df no verificable' }
  return [long]$P2DfFields[3] * 1024
}
$P2TmpFreeBefore = Get-P2AvailableBytesFromDf $P2DfTmpLog
$P2DataFreeBefore = Get-P2AvailableBytesFromDf $P2DfDataLog
if ($P2TmpFreeBefore -lt $P2RequiredBytes -or $P2DataFreeBefore -lt $P2RequiredBytes) {
  throw 'Espacio Docker insuficiente para margen acordado; no iniciar dump'
}
# Es un margen operativo propuesto, no garantia matematica ni reserva real de capacidad.
if ($P2RunId -notmatch '^\d{8}T\d{6}Z_[a-f0-9]{32}$') { throw 'ID temporal no generado por este procedimiento' }
$P2ContainerTmpDir = '/tmp/p2_backup_' + $P2RunId
$P2ContainerDump = $P2ContainerTmpDir + '/snapshot.dump'
# Rechazar /tmp dentro de cualquier montaje declarado; solo capa temporal del contenedor.
foreach ($P2Mount in $P2DockerMounts) {
  $P2MountPrefix = $P2Mount.Destination.TrimEnd('/') + '/'
  if ($P2ContainerTmpDir.StartsWith($P2MountPrefix)) { throw 'Temporal cae dentro de un montaje: revisar' }
}
$null = Invoke-P2DockerStep 'd_mkdir_exclusivo' ($P2ExecTools + @('mkdir','-m','700',$P2ContainerTmpDir))
# mkdir sin -p falla ante una ruta previa; no reutilizarla ni lanzar otro dump sobre ella.
$P2TmpRealLog = Invoke-P2DockerStep 'd_tmp_real' ($P2ExecTools + @('readlink','-f',$P2ContainerTmpDir))
if ((Get-Content -LiteralPath $P2TmpRealLog -Raw).Trim() -ne $P2ContainerTmpDir) {
  throw 'Directorio temporal redirigido; no respaldar'
}
```

La reserva privada en Windows precede estas comprobaciones. El directorio interno
700 pertenece al usuario OS postgres. Un fallo conserva rutas/logs para revisión,
no dispara eliminación ni reintentos. Antes del dump, cerrar el control de escritores
de sección 2 sin ejecutar sus comandos Windows/psql: las consultas de metadatos
aprobadas pueden ejecutarse mediante `$P2ExecTools + @('psql') + $P2SocketConnection`.
La coordinación de jobs y la visibilidad de sesiones siguen siendo prerrequisitos;
no hay aquí una orden automática para parar servicios o revocar permisos.

### D3. Escritura custom directa, copia y cotejo binario

```powershell
foreach ($P2File in @($P2Partial,$P2DumpFile,$P2ManifestFile)) {
  if (Test-Path -LiteralPath $P2File) { throw 'Salida host previa: no sobrescribir' }
}
$P2StartUtc = [DateTime]::UtcNow.ToString('o')
$null = Invoke-P2DockerStep 'd_pg_dump' ($P2ExecTools + @('pg_dump') + $P2SocketConnection +
  @('--format=custom','--lock-wait-timeout=30s',"--file=$P2ContainerDump"))
$P2EndUtc = [DateTime]::UtcNow.ToString('o')
$P2DumpExit = 0 # El helper solo retorna tras ExitCode=0; cualquier fallo detiene el bloque.
$P2TmpFileTypeLog = Invoke-P2DockerStep 'd_tmp_file_type' ($P2ExecTools + @('stat','-c','%F',$P2ContainerDump))
$P2TmpFileRealLog = Invoke-P2DockerStep 'd_tmp_file_real' ($P2ExecTools + @('readlink','-f',$P2ContainerDump))
if ((Get-Content -LiteralPath $P2TmpFileTypeLog -Raw).Trim() -ne 'regular file' -or
    (Get-Content -LiteralPath $P2TmpFileRealLog -Raw).Trim() -ne $P2ContainerDump) {
  throw 'Dump temporal no es archivo regular propio en la ruta esperada'
}
$P2InsideSizeLog = Invoke-P2DockerStep 'd_size_dump' ($P2ExecTools + @('stat','-c','%s',$P2ContainerDump))
$P2InsideSizeText = (Get-Content -LiteralPath $P2InsideSizeLog -Raw).Trim()
if ($P2InsideSizeText -notmatch '^\d+$' -or [long]$P2InsideSizeText -le 0) { throw 'Dump interno vacio/invalido' }
$P2InsideSize = [long]$P2InsideSizeText
$P2InsideHashLog = Invoke-P2DockerStep 'd_sha_dump' ($P2ExecTools + @('sha256sum',$P2ContainerDump))
$P2InsideHashLine = (Get-Content -LiteralPath $P2InsideHashLog -Raw).Trim()
if ($P2InsideHashLine -notmatch '^([a-f0-9]{64})\s+') { throw 'SHA256 interno no verificable' }
$P2InsideSha = $Matches[1]
if ($P2HostDisk.AvailableFreeSpace -lt ($P2InsideSize + 1GB)) { throw 'Espacio host insuficiente antes de copiar' }
if (Test-Path -LiteralPath $P2Partial) { throw 'Destino de copia ya existe' }
$P2CopySource = $P2ContainerId + ':' + $P2ContainerDump
$null = Invoke-P2DockerStep 'd_cp_dump' @('cp',$P2CopySource,$P2Partial)
# docker cp no recibe '-' ni -L/-a: copia un archivo, sin pipeline ni follow-link deliberado.
if (-not (Test-Path -LiteralPath $P2Partial -PathType Leaf)) { throw 'Copia local ausente' }
$P2CopyAcl = Get-Acl -LiteralPath $P2Partial
$P2CopyRules = $P2CopyAcl.GetAccessRules($true,$true,[Security.Principal.SecurityIdentifier])
if (@($P2CopyRules | Where-Object {
    $_.AccessControlType -eq [Security.AccessControl.AccessControlType]::Allow -and
    $P2AllowedSids -notcontains $_.IdentityReference.Value
  }).Count -gt 0) { throw 'ACL de la copia no privada' }
$P2DumpBytes = (Get-Item -LiteralPath $P2Partial).Length
$P2DumpSha = (Get-FileHash -LiteralPath $P2Partial -Algorithm SHA256).Hash.ToLowerInvariant()
if ($P2DumpBytes -ne $P2InsideSize -or $P2DumpSha -ne $P2InsideSha) {
  throw 'Copia distinta: conservar ambos archivos y logs; no limpiar ni aceptar'
}
$P2CatalogLog = Invoke-P2DockerStep 'd_catalogo_custom' ($P2ExecTools + @('pg_restore','--list',$P2ContainerDump))
$P2ListExit = 0 # Catalogo legible no equivale a restauracion validada.
if (Test-Path -LiteralPath $P2DumpFile) { throw 'Archivo final previo' }
Move-Item -LiteralPath $P2Partial -Destination $P2DumpFile -ErrorAction Stop
if ((Get-FileHash -LiteralPath $P2DumpFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $P2InsideSha) {
  throw 'Archivo final no coincide con el origen temporal'
}
```

`docker cp` puede sobrescribir un destino existente: por eso se exige carpeta privada
única, reserva, control de existencia y paso con logs exclusivos; no ejecutar el mismo
paso por fuera de este flujo. No hay exclusión frente a un administrador que manipule
concurrentemente las rutas. Un operador, contenedor estable y ningún escritor ajeno
en esas carpetas son condiciones obligatorias. Revisar warnings privados del dump
antes de aceptar el respaldo; no basta salida 0.

### D4. Manifiesto Docker y enlace futuro al descriptor

Usar este manifiesto, **no el bloque de sección 4 que requiere variables de clientes
Windows**. La versión/locale/extensiones para futura restauración siguen pendientes
de obtener con metadatos autorizados o del catálogo y comprobar en instancia aislada;
no rellenarlos con supuestos.

```powershell
$P2DockerManifest = [ordered]@{
  version=1; id=$P2RunId; variante='DOCKER_PG_DUMP_CUSTOM'
  estado='COPIA_LOGICA_VERIFICADA_RESTAURACION_PENDIENTE'
  inicio_utc=$P2StartUtc; fin_utc=$P2EndUtc; commit=$P2Commit
  entorno=[ordered]@{proyecto='proyecto2_ciencia_datos'; contexto=$P2Context
    contenedor=$P2SourceContainer; contenedor_id=$P2ContainerId; imagen_id=$P2ImageId
    base=$P2Db; host_puerto_declarado=5434; conexion_dump='socket Unix interno'
    data_directory_verificado=$P2ActualDataDirectory
    volumen_declarado='proyecto2_ciencia_datos_postgres_data'; equipo=$env:COMPUTERNAME}
  pg_dump_version=$P2DumpVersion; pg_restore_version=$P2RestoreVersion; servidor_version_num=$P2ServerVersion
  formato='custom'; pg_dump_exit=$P2DumpExit; docker_cp_exit=0; lectura_catalogo_exit=$P2ListExit
  archivo='snapshot.dump'; bytes=$P2DumpBytes; sha256_respaldo=$P2DumpSha
  temporal_contenedor=$P2ContainerDump; bytes_temporal=$P2InsideSize; sha256_temporal=$P2InsideSha
  espacio_host_previo=$P2FreeBefore; espacio_tmp_previo=$P2TmpFreeBefore; espacio_pgdata_previo=$P2DataFreeBefore
  escritores='REQUIERE_REGISTRO_PRIVADO_DE_COORDINACION_Y_REVISION'
  advertencias_pg_dump='REQUIERE_REVISION_PRIVADA'; extensiones_locale='PENDIENTE_REGISTRO_Y_RESTAURACION'
  certificado_origen=$false; procedencia_generador='no_acreditada'
  enmienda='NO_APROBADA_POR_ESTE_RESPALDO'; retiro_temporal='NO_EJECUTADO'
  relacion_auditoria_20261110='NO_DEMOSTRADA; no recrea el instante historico auditado'
}
$P2DockerManifestStream = [IO.File]::Open($P2ManifestFile,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try {
  $P2DockerManifestBytes = [Text.UTF8Encoding]::new($false).GetBytes(($P2DockerManifest | ConvertTo-Json -Depth 8))
  $P2DockerManifestStream.Write($P2DockerManifestBytes,0,$P2DockerManifestBytes.Length)
  $P2DockerManifestStream.Flush($true)
} finally { $P2DockerManifestStream.Dispose() }
```

Los códigos 0 se registran solo después de que cada helper haya comprobado su
ExitCode; no crear manifiesto desde variables reutilizadas de otra sesión. Los hashes
de temporal/copia identifican bytes del respaldo, no certificados del origen de datos.
El manifiesto no incluye usuario SQL, credenciales ni Config.Env. Su aceptación humana
y prueba de restauración continúan pendientes. El descriptor solo podría revisarse
después bajo el procedimiento de sección 6, sin atribuir equivalencia histórica.

### D5. Retiro opcional y posterior de un único temporal propio

**ELIMINACIÓN NO EJECUTADA.** Requiere confirmación posterior del custodio de respaldo,
revisión de warnings, manifiesto persistido y archivo host validado/custodiado.
Si existe cualquier duda/fallo, no limpiar. Mantener la misma sesión y contenedor
identificado; si se reinició o cambió, detenerse y revisar. El bloque no contiene rm -r,
wildcards, eliminación de volúmenes ni borrado de PGDATA; deja el directorio vacío.

```powershell
if ($P2ContainerTmpDir -notmatch '^/tmp/p2_backup_\d{8}T\d{6}Z_[a-f0-9]{32}$' -or
    $P2ContainerDump -cne ($P2ContainerTmpDir + '/snapshot.dump')) { throw 'Temporal fuera del alcance propio' }
$P2SavedManifest = Get-Content -LiteralPath $P2ManifestFile -Raw -Encoding utf8 | ConvertFrom-Json
if ($P2SavedManifest.id -ne $P2RunId -or $P2SavedManifest.sha256_respaldo -ne $P2InsideSha -or
    (Get-FileHash -LiteralPath $P2DumpFile -Algorithm SHA256).Hash.ToLowerInvariant() -ne $P2InsideSha) {
  throw 'Respaldo/manifiesto no validado: no retirar temporal'
}
$P2BeforeCleanIdLog = Invoke-P2DockerStep 'd_before_clean_container' @('inspect','--format','{{.Id}}',$P2SourceContainer)
if ((Get-Content -LiteralPath $P2BeforeCleanIdLog -Raw).Trim() -ne $P2ContainerId) { throw 'Contenedor distinto' }
$P2BeforeCleanRealLog = Invoke-P2DockerStep 'd_before_clean_real' ($P2ExecTools + @('readlink','-f',$P2ContainerDump))
$P2BeforeCleanTypeLog = Invoke-P2DockerStep 'd_before_clean_type' ($P2ExecTools + @('stat','-c','%F',$P2ContainerDump))
$P2BeforeCleanLinksLog = Invoke-P2DockerStep 'd_before_clean_links' ($P2ExecTools + @('stat','-c','%h',$P2ContainerDump))
$P2BeforeCleanOwnerLog = Invoke-P2DockerStep 'd_before_clean_owner' ($P2ExecTools + @('stat','-c','%u',$P2ContainerDump))
$P2PostgresUidLog = Invoke-P2DockerStep 'd_postgres_uid' ($P2ExecTools + @('id','-u'))
if ((Get-Content -LiteralPath $P2BeforeCleanRealLog -Raw).Trim() -cne $P2ContainerDump -or
    (Get-Content -LiteralPath $P2BeforeCleanTypeLog -Raw).Trim() -ne 'regular file' -or
    (Get-Content -LiteralPath $P2BeforeCleanLinksLog -Raw).Trim() -ne '1' -or
    (Get-Content -LiteralPath $P2BeforeCleanOwnerLog -Raw).Trim() -ne
      (Get-Content -LiteralPath $P2PostgresUidLog -Raw).Trim()) { throw 'Archivo no es el temporal propio verificable' }
$P2BeforeCleanHashLog = Invoke-P2DockerStep 'd_before_clean_hash' ($P2ExecTools + @('sha256sum',$P2ContainerDump))
$P2BeforeCleanHash = (Get-Content -LiteralPath $P2BeforeCleanHashLog -Raw).Trim()
if ($P2BeforeCleanHash -notmatch '^([a-f0-9]{64})\s+' -or $Matches[1] -ne $P2InsideSha) {
  throw 'Temporal cambiado: no eliminar'
}
# Punto de detencion manual: solo despues de confirmar custodia/aceptacion del respaldo.
$P2CleanupConfirmation = Read-Host 'Confirmar RETIRAR_SOLO_TEMPORAL_PROPIO'
if ($P2CleanupConfirmation -cne 'RETIRAR_SOLO_TEMPORAL_PROPIO') { throw 'Retiro no confirmado' }
$null = Invoke-P2DockerStep 'd_rm_solo_temporal' ($P2ExecTools + @('rm','--',$P2ContainerDump))
# Registro nuevo; no reescribir el manifiesto que indicaba retiro aun pendiente.
$P2CleanupRecord = Join-Path $P2BackupDir 'retiro_temporal.json'
$P2CleanupStream = [IO.File]::Open($P2CleanupRecord,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write)
try {
  $P2CleanupBytes = [Text.UTF8Encoding]::new($false).GetBytes((@{
    id=$P2RunId; fecha_utc=[DateTime]::UtcNow.ToString('o'); contenedor_id=$P2ContainerId
    ruta_temporal=$P2ContainerDump; respaldo_sha256=$P2InsideSha; estado='RETIRADO_SOLO_ARCHIVO_PROPIO'
  } | ConvertTo-Json))
  $P2CleanupStream.Write($P2CleanupBytes,0,$P2CleanupBytes.Length)
  $P2CleanupStream.Flush($true)
} finally { $P2CleanupStream.Dispose() }
```

La verificación previa no elimina una carrera frente a otro administrador con acceso
al contenedor: exigir ausencia de manipulación concurrente. No añadir `-f`/`-r`, no
borrar el directorio padre y no limpiar automáticamente si falló dump/copia/hash.
Un fallo al registrar el retiro después de borrar debe auditarse; no repetir el bloque
ni inferir que el temporal sigue presente a partir del manifiesto inicial.

### D6. Restauración posterior y condiciones aún pendientes

La restauración seguirá siendo otra autorización, en contenedor/volumen nuevos de
sección 5, red none y sin puertos, nunca en el origen. Los comandos internos de
pg_restore ya documentados no necesitan un cliente Windows; no ejecutar los bloques
Windows de listado/dump. Antes deben registrarse encoding/locale, extensiones y roles
necesarios mediante metadatos autorizados usando psql interno y verificarlos en el
destino. Adaptar esas lecturas de sección 2 a Docker no equivale a tenerlas verificadas.

Pendientes antes del primer respaldo: aprobación de variante y alcance de lectura,
ACL/cifrado/custodia, disponibilidad de socket autenticado, herramientas auxiliares
Alpine (`env`, `df`, `mkdir`, `readlink`, `stat`, `sha256sum`, `id`, `rm`) y espacio
real en host y VM; coordinación de escritores y una sola ejecución/operador. No se
instalan herramientas ni cambian permisos/autenticación automáticamente si faltan.
El temporal puede perderse al recrear el contenedor; por ello debe copiarse y custodiarse
sin presentarlo como respaldo definitivo hasta superar los controles. Ninguna etapa
certifica el origen, aprueba la enmienda ni autoriza exportar/evaluar B.

## Referencias y punto de detención

- [PostgreSQL 16: pg_dump](https://www.postgresql.org/docs/16/app-pgdump.html): copia consistente de una base y formato custom.
- [PostgreSQL 16: pg_restore](https://www.postgresql.org/docs/16/app-pgrestore.html): restauración de archivos custom, comprobación de errores y destino.
- [Microsoft: Start-Process, PowerShell 5.1](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process?view=powershell-5.1): quoting de ArgumentList y streams de procesos nativos.
- [PostgreSQL 16: entorno libpq](https://www.postgresql.org/docs/16/libpq-envars.html) y [archivo de contraseñas](https://www.postgresql.org/docs/16/libpq-pgpass.html).
- [Docker: ejecución de contenedores](https://docs.docker.com/engine/containers/run/) e [imagen oficial PostgreSQL](https://hub.docker.com/_/postgres).
- [Docker: docker cp](https://docs.docker.com/reference/cli/docker/container/cp/) y [docker exec](https://docs.docker.com/reference/cli/docker/container/exec/): copia archivo-a-archivo y ausencia de pseudo-TTY para esta variante.
- Configuración local: `docker-compose.yml`, `dbt_red_metropolitana/config/profiles.yml`, `.git/info/exclude` y orquestador P2.

Los bloques PowerShell se revisaron documentalmente, no se probaron en ejecución.
Validación sintáctica efectuada con `System.Management.Automation.Language.Parser`
de Windows PowerShell **5.1.26100.9711**: **14 bloques, 0 errores**, incluida la variante Docker, sin ejecutar
ningún bloque ni comando Docker/PostgreSQL. Esto no verifica disponibilidad de
herramientas, permisos, espacio, respuestas de Docker o comportamiento del servidor.
Pendientes: aprobación del procedimiento y alcance de lectura de respaldo, custodia,
autenticación, espacio, control de escritores y autorización separada de restauración.
**Detenerse aquí: ningún comando Docker/PostgreSQL está autorizado por este documento.**
