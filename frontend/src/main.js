import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { FrappeUI } from 'frappe-ui'
import { router } from './router'
import './style.css'
import App from './App.vue'

const app = createApp(App)

app.use(router) // requerido: frappe-ui inyecta Symbol(router) en <Button route>
app.use(createPinia())
app.use(FrappeUI)

app.mount('#app')
