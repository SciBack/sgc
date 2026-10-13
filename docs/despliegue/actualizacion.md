# Actualizar una instancia

Cómo se pasa una instancia del SGC a una versión nueva. Lo puede seguir alguien que no lo
diseñó: cada paso dice qué hace, cómo se ve que salió bien y qué hacer si no.

**Lo que se promete:** un corte **corto, avisado y visible**. No se promete cero corte: con
migraciones de esquema no se sostiene, y prometerlo sería mentir. Quien entra durante la
ventana ve una página de mantenimiento, no un error. Al terminar, la instancia se comprueba
sola. Y volver atrás es un comando que ya se ha ejecutado, no un párrafo.

## Antes: 24 h o más

1. **Leer la entrada del CHANGELOG** de la versión nueva. Hay que mirar dos cosas:
   - **«Requiere migrar»**: casi siempre sí. El script migra igual.
   - **Si cambia la versión MAYOR**: hay cambios de esquema que no se deshacen solos. Si hay
     que volver atrás, habrá que restaurar la base (ver [Volver atrás](#volver-atrás)).
2. **Avisar a los usuarios** desde el propio SGC: un **Comunicado** de tipo «Mantenimiento
   programado», con inicio y fin, a los roles que trabajan en el sistema. El SGC exige
   24 h de antelación para enviarlo. **El script no actualiza sin ese comunicado enviado**: comprueba
   que su ventana cubre el momento de la actualización, con 30 minutos de margen antes del inicio.
3. **Tener a mano** la imagen nueva (`ghcr.io/sciback/sgc-frappe:<versión>`, ver
   [publicación](../desarrollo/publicacion.md)) y el script de esta versión:
   ```bash
   docker run --rm --entrypoint cat ghcr.io/sciback/sgc-frappe:<versión> \
     /home/frappe/frappe-bench/apps/sgc/deploy/actualizar.sh > actualizar.sh
   chmod +x actualizar.sh
   ```
   Así el procedimiento viaja con la versión que instala.

## Durante: un comando

```bash
./actualizar.sh actualizar --proyecto <proyecto-compose> --sitio <sitio> \
  --imagen ghcr.io/sciback/sgc-frappe:<versión>
```

`<proyecto-compose>` es el nombre que da `docker compose ls`. El script lee el compose de los
propios contenedores, así que no hace falta decirle dónde está. Respaldos y estado van a
`<directorio del compose>/respaldos`, o a donde diga `--respaldos`.

| Paso | Qué hace | Quien entra ve |
|---|---|---|
| 1 | Descarga la imagen y lee su versión. Sin etiqueta de versión no sigue: no es una imagen publicada. | El sistema, normal |
| 2 | Comprueba el aviso: el Comunicado enviado cuya ventana cubre ahora. | El sistema, normal |
| 3 | Respaldo de base y ficheros, **fuera del contenedor**. Sin respaldo no sigue. | El sistema, normal |
| 4 | Modo mantenimiento en el sitio. | Página «Actualizando» de Frappe |
| 5 | Cambia la imagen en el compose (copia `.bak-<fecha>` de cada fichero tocado) y recrea backend, websocket, scheduler y colas. El frontend sigue en pie. | Página de mantenimiento del SGC |
| 6 | `clear-cache`, `migrate`, `clear-cache`. | Página «Actualizando» |
| 7 | Recrea el frontend con los assets nuevos. | Unos segundos de corte |
| 8 | Comprobación: verificación de instancia sin bloqueantes, versión de la instancia igual a la de la imagen y migrate registrado. Si pasa, **quita el modo mantenimiento**. | El sistema, actualizado |

Una corrección urgente que no puede esperar 24 h se hace con `--sin-aviso "motivo"`. El motivo
queda escrito en la salida.

## Si la comprobación final no pasa

El script **deja el sitio en mantenimiento** y explica qué hacer. Nadie trabaja sobre algo que
puede estar a medias. Para decidir:

- **Un AVISO no es motivo de volver atrás**: un periodo sin fechas o procesos sin responsable no
  los ha causado la actualización.
- **Un BLOQUEANTE, una versión que no cuadra o un migrate que falló, sí.** Primero hay que ver
  si se arregla sin cambiar de imagen, por ejemplo un paso de `f_deploy_run_all` que falló o
  una caché. Si se arregla, se comprueba y se quita el mantenimiento:
  ```bash
  ./actualizar.sh comprobar --proyecto <p> --sitio <s> --version <versión>
  docker exec <backend> bench --site <s> set-maintenance-mode off
  ```
- **Si no se arregla en minutos, se vuelve atrás.**

## Volver atrás

```bash
./actualizar.sh volver --proyecto <p> --sitio <s>
```

Repone los ficheros del compose que cambió `actualizar` (sus `.bak-<fecha>`), recrea los
servicios con la imagen anterior, migra y comprueba. Usa el estado que dejó la última
actualización en `respaldos/ultima-actualizacion.env`.

**Límite que hay que conocer:** volver a la imagen anterior **no deshace la migración**. Con
una versión MENOR o PARCHE da igual: los campos nuevos siguen en la base y la versión anterior
los ignora. Con una MAYOR, o si la vuelta atrás da bloqueantes, hay que restaurar además
**la base y los ficheros del respaldo** que se sacó en el paso 3:

```bash
SGC_DB_ROOT_USER=<superusuario> SGC_DB_ROOT_PASSWORD=<contraseña> \
  ./actualizar.sh volver --proyecto <p> --sitio <s> --restaurar-base
```

Restaurar **borra lo que se haya escrito después del respaldo**. Por eso el sitio está en
mantenimiento desde antes de respaldar hasta el final: en una actualización normal no se pierde
nada.

## Notas

- **Imagen declarada en el compose.** El script cambia la imagen donde ya esté: el `.env` de
  frappe_docker (`CUSTOM_IMAGE`/`CUSTOM_TAG`) o el propio fichero de compose. Si no la encuentra,
  no toca nada.
- **Permisos.** Si el compose es de root, el script usa `sudo` solo para escribir esos ficheros.
- **Lecturas durante la migración.** Frappe puede seguir sirviendo lecturas en modo mantenimiento
  con `allow_reads_during_maintenance` en `site_config`. No viene activado: durante una migración
  de esquema, leer puede dar resultados a medias.
- **Proxy delante.** Si delante del frontend hay otro proxy (Caddy, otro nginx), sigue pasando la
  página de mantenimiento. Solo los segundos del paso 7 dependen de ese proxy; el mismo
  `mantenimiento.html` puede servirse desde él para cubrirlos.
- **Versiones anteriores a la 1.0.0** no tienen `sgc.mantenimiento` ni `sgc.estado`. La primera
  actualización desde ellas necesita `--sin-aviso` (con el aviso hecho a mano). Al volver a una
  de ellas, la comprobación se queda en la verificación de instancia.
