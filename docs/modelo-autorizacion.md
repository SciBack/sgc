# Modelo de autorización del SGC

Quién puede hacer qué, sobre qué registros, y qué queda registrado. Es el
contrato que toda pantalla del sistema debe respetar.

Este documento es **canónico y agnóstico**: describe el mecanismo, no los cargos
de ninguna institución concreta. El mapeo entre los cargos reales de una
institución y los perfiles de aquí vive en su capa de institución, nunca aquí.

## El principio: dos ejes que se cruzan

El permiso efectivo es la intersección de dos preguntas independientes:

```
permiso efectivo  =  QUÉ puede hacer          ×  SOBRE QUÉ registros
                     (Role / Role Profile)       (User Permission)
```

- **El qué** son los permisos por DocType: crear, leer, escribir, enviar,
  cancelar, y el nivel de campo. Vive en el catálogo de roles.
- **El sobre qué** es el ámbito: la sede, el programa o el proceso al que
  pertenece cada registro.

No hay un motor de autorización propio. El framework calcula esa intersección, y
el sistema solo aporta los casos que el framework no puede resolver solo.

## Las cuatro dimensiones

El requisito de "permisos por módulo, proceso, programa y sede" se reparte entre
los dos ejes. No son cuatro cosas del mismo tipo:

| Dimensión | Eje | Cómo se expresa |
|---|---|---|
| Módulo | QUÉ | Permisos por DocType en el catálogo de roles |
| Sede | SOBRE QUÉ | User Permission sobre `Unidad Organica` |
| Programa | SOBRE QUÉ | User Permission sobre `Programa Sede` |
| Proceso | SOBRE QUÉ | User Permission sobre `Proceso` |

Confundir el módulo con las otras tres es el error más fácil: "que este rol no
vea el módulo de auditorías" no se resuelve con un ámbito, se resuelve quitando
el permiso de lectura sobre esos DocTypes.

### Cómo se combinan

- **Dimensiones distintas se intersectan.** Quien tiene una sede y un proceso
  asignados ve solo lo que cumple ambas.
- **Varios valores de la misma dimensión se suman.** Dos sedes asignadas dejan
  ver las dos.
- **Sede y proceso alcanzan a sus descendientes.** Ambos son árboles: asignar un
  nodo padre incluye todo lo que cuelga de él. Un responsable de sede no necesita
  una asignación por facultad, y una facultad nueva no le rompe el acceso.
- **Un registro sin ámbito es visible para todos.** Lo que no es atribuible a una
  sede, un programa o un proceso es transversal. Ocultarlo escondería justo lo
  institucional.

## Los dos niveles de nombres

El catálogo tiene roles finos, pensados para expresar permisos con precisión. Las
personas se asignan por **perfiles**, que agrupan roles bajo el nombre que usa el
área de calidad.

Se asigna un perfil, no roles sueltos. Los roles finos existen para que el perfil
signifique algo preciso, no para repartirse a mano.

Cuatro roles quedan fuera de todo perfil a propósito, porque no corresponden a un
cargo sino a una responsabilidad puntual: dueño de proceso, responsable de un
dominio de dato, responsable de sede y autoridad que aprueba publicaciones. Se
asignan individualmente.

**El gobierno funcional del sistema de calidad y la administración técnica de la
plataforma son perfiles distintos, y no deben unirse.** Quien gobierna el
contenido no administra el servidor. Es el control interno más básico que tiene
el sistema.

## Activación: el ámbito es opt-in

Mientras a una persona no se le siembre ningún ámbito, **ve todo**. El mecanismo
está construido pero inactivo hasta que alguien lo activa, persona por persona.

Esto es deliberado. Una institución que arranca con un equipo pequeño en una sola
dirección no gana nada acotando, y sí puede perder registros de vista por un
ámbito mal sembrado. El acotamiento se activa cuando entra gente de fuera de ese
equipo.

Para activar y para verificar:

```bash
bench --site <sitio> execute sgc.permissions.otorgar_ambito \
  --kwargs '{"user":"persona@dominio","unidad_organica":"<sede>","proceso":"<proceso>"}'

bench --site <sitio> execute sgc.permissions.ambito_de \
  --kwargs '{"user":"persona@dominio"}'
```

`ambito_de` devuelve `acotado: false` cuando esa persona todavía ve todo. Es la
comprobación que conviene hacer después de cada alta.

Algunos roles están exentos por diseño y ven todo aunque se les siembre un
ámbito: el gobierno del sistema y el aseguramiento. Un auditor acotado no podría
auditar.

## Qué queda registrado

| Qué | Dónde | Quién lo lee |
|---|---|---|
| Cambios en los datos, con el valor anterior | `Version` | Gobierno y aseguramiento |
| Inicios y cierres de sesión, incluidos los fallidos, con IP | `Activity Log` | Solo administración técnica |

El registro de cambios lo alimenta `track_changes` en cada DocType. Sin esa marca
no se guarda nada, y la ausencia no da ningún error: hay un test que verifica que
los DocTypes de datos críticos la tienen.

**El registro de sesiones no se expone a ningún rol funcional, ni al de
auditoría.** Quién entró, cuándo y desde dónde es dato personal de la persona
trabajadora. Auditar el sistema de calidad no requiere vigilar a las personas, y
sin una finalidad declarada y una base legal, exponerlo sería un tratamiento de
datos sin sustento.

### Límite conocido

Ninguno de los dos registros es inmutable: la administración técnica de la
plataforma puede borrarlos. Si una auditoría externa exige no repudio, hay que
construir esa garantía encima; el framework no la da.

## Contraseñas

No las gobierna este sistema. El acceso es por proveedor de identidad externo y
no existen contraseñas locales que caducar o complejizar. Cualquier política de
contraseñas se define en el proveedor de identidad.

## Al añadir un DocType nuevo

1. Si el registro pertenece a una sede, un programa o un proceso, dale el campo
   Link correspondiente. Con eso el acotamiento funciona sin escribir código.
2. Si el ámbito se hereda del documento padre en lugar de estar en un campo
   propio, hay que añadirlo a los hooks de permisos: el framework no puede
   deducirlo.
3. Si es un dato crítico, verifica que tenga `track_changes` activo.
4. Añádelo a la matriz de permisos por rol. Un DocType fuera de la matriz solo lo
   ve la administración técnica, que casi nunca es lo que se quiere.
