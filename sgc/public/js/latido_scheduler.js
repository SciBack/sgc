// SGC — aviso de tareas programadas paradas (#42)
// -----------------------------------------------------------------------------
// Si el scheduler se para, nada falla a la vista: las tareas dejan de correr y
// ya. Este aviso lo detecta DESDE EL DESK, no desde el scheduler: si la
// vigilancia corriera en el scheduler, caería con él y no avisaría nunca.
//
// Solo para System Manager, una vez por sesión del navegador. La lógica
// (umbral, qué cuenta como atrasada) está en `sgc/latido.py`; aquí solo se pinta.
// No se lee de `frappe.boot` a propósito: el boot se cachea por usuario
// (sessions.py:139), y un aviso cacheado seguiría saliendo tras arreglarse.
(() => {
	const boot = frappe.boot || {};
	const roles = (boot.user && boot.user.roles) || [];
	if (!roles.includes("System Manager")) return;

	const CLAVE = "sgc-latido-avisado";
	const ya_avisado = () => {
		try {
			return sessionStorage.getItem(CLAVE) === "1";
		} catch (e) {
			return false;
		}
	};
	const marcar_avisado = () => {
		try {
			sessionStorage.setItem(CLAVE, "1");
		} catch (e) {
			// sin sessionStorage, avisa en cada carga: molesto, pero no se pierde
		}
	};

	const esc = (v) => frappe.utils.escape_html(v == null ? "" : String(v));

	const describir = (t) => {
		if (t.detenida) return __("detenida");
		if (t.nunca) return __("nunca ha terminado bien");
		return __("hace {0} h (límite {1} h)", [t.horas, t.limite]);
	};

	const mostrar = (r) => {
		const filas = r.tareas
			.filter((t) => t.alerta)
			.map(
				(t) => `<tr>
					<td><code>${esc(t.metodo)}</code></td>
					<td>${esc(describir(t))}</td>
					<td>${esc(t.ultimo_estado || "—")}</td>
				</tr>`
			)
			.join("");

		const apagado = r.scheduler_apagado
			? `<p><b>${__(
					"El scheduler está desactivado en System Settings o en site_config."
			  )}</b></p>`
			: "";

		const tabla = filas
			? `<table class="table table-bordered table-sm">
					<thead><tr>
						<th>${__("Tarea")}</th>
						<th>${__("Última ejecución completa")}</th>
						<th>${__("Último estado")}</th>
					</tr></thead>
					<tbody>${filas}</tbody>
				</table>`
			: "";

		frappe.msgprint({
			title: __("Las tareas programadas no están corriendo"),
			indicator: "red",
			message: `${apagado}
				<p>${__(
					"Mientras sigan así, el sistema deja de marcar como vencidas las evidencias y los acuerdos que caducan."
				)}</p>
				${tabla}
				<p><a href="/desk/scheduled-job-log">${__("Ver el registro de ejecuciones")}</a> · ${__(
				"Queda anotado en el Error Log."
			)}</p>`,
		});
	};

	$(document).on("app_ready", () => {
		if (ya_avisado()) return;
		frappe
			.call({ method: "sgc.latido.estado", type: "POST" })
			.then((r) => {
				const res = r && r.message;
				if (res && res.alerta) {
					marcar_avisado();
					mostrar(res);
				}
			})
			// La vigilancia no debe estorbar a quien entra: si falla, calla.
			.catch(() => {});
	});
})();
