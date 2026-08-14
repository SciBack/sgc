<script setup>
/** Título de página. Reemplaza al `PageHeaderTitle` de frappe-ui.
 *  El breadcrumb expresa la ubicación; este es el objeto de trabajo (estilo §3.1). */
defineProps({ title: { type: String, required: true } })
</script>

<template>
  <h1 class="font-display text-xl font-bold tracking-[-0.02em] text-tinta">{{ title }}</h1>
</template>
