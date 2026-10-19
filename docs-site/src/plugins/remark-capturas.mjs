// Capturas de pantalla que pone cada institución, no el producto.
//
// El manual es agnóstico: una captura del SGC en marcha enseña la marca, los procesos y las
// personas de una institución concreta. Por eso las páginas solo NOMBRAN la captura:
//
//     ![Árbol del mapa de procesos](captura:procesos-arbol)
//
// y la imagen la aporta quien construye su manual, en `public/capturas/<id>.<ext>`. Si está, se
// pinta; si no, la referencia desaparece sin dejar hueco. El manual público sale sin capturas.
import { existsSync } from 'node:fs';
import path from 'node:path';

export const PREFIJO = 'captura:';
export const EXTENSIONES = ['webp', 'png', 'jpg'];
const ID = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

export function buscarCaptura(dir, id) {
  for (const ext of EXTENSIONES) {
    const fichero = `${id}.${ext}`;
    if (existsSync(path.join(dir, fichero))) return fichero;
  }
  return null;
}

export default function remarkCapturas({ dir, base = '/' } = {}) {
  if (!dir) throw new Error('remark-capturas: falta `dir`');
  const prefijo = `${base.replace(/\/+$/, '')}/capturas/`;

  const resolver = (padre) => {
    if (!padre.children) return;
    padre.children = padre.children.flatMap((nodo) => {
      if (nodo.type === 'image' && nodo.url.startsWith(PREFIJO)) {
        const id = nodo.url.slice(PREFIJO.length);
        if (!ID.test(id)) throw new Error(`remark-capturas: id no válido «${id}»`);
        if (!nodo.alt) throw new Error(`remark-capturas: la captura «${id}» no tiene texto alternativo`);
        const fichero = buscarCaptura(dir, id);
        if (!fichero) return [];
        return [{ ...nodo, url: prefijo + fichero, title: nodo.title ?? nodo.alt }];
      }
      resolver(nodo);
      // Un párrafo que solo llevaba la captura no deja un <p> vacío.
      if (nodo.type === 'paragraph' && nodo.children.every((h) => h.type === 'text' && !h.value.trim())) return [];
      return [nodo];
    });
  };

  return (arbol) => resolver(arbol);
}
