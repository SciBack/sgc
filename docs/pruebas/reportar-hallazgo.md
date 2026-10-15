---
title: Cómo reportar un hallazgo
description: Evidencia reproducible y segura para defectos funcionales.
---

## Plantilla

**Título:** `[Módulo][Rol][Estado] resultado incorrecto`  
**Entorno/versión:** URL, commit o versión, navegador, fecha/hora.  
**Rol y ámbito:** rol único y Programa Sede sintético.  
**Precondiciones:** datos y servicios necesarios.  
**Pasos:** numerados, una acción por paso.  
**Esperado:** resultado respaldado por este manual/código.  
**Obtenido:** resultado observable, sin interpretación.  
**Evidencia:** capturas sanitizadas, respuesta HTTP y log correlacionable.  
**Impacto:** flujo/roles afectados y si existe alternativa.  
**Repetibilidad:** siempre/intermitente y número de intentos.

## Severidad sugerida

- **Crítica:** exposición de datos, pérdida/corrupción o sistema indisponible.
- **Alta:** flujo principal o autorización incorrecta sin alternativa segura.
- **Media:** función degradada con alternativa controlada.
- **Baja:** texto, presentación o fricción sin afectar el resultado.

## Evidencia prohibida

No adjuntes contraseñas, cookies, tokens, DNI, correos personales, nombres reales ni expedientes.
Reproduce con datos sintéticos o redacta antes de compartir.
