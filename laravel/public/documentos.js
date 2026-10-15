(() => {
    const form = document.getElementById('upload-form');
    if (!form) return;
    const input = document.getElementById('archivo');
    const zone = document.getElementById('dropzone');
    const button = document.getElementById('upload-button');
    const message = document.getElementById('upload-message');
    const progress = document.getElementById('upload-progress');
    for (const event of ['dragover', 'dragleave', 'drop']) zone.addEventListener(event, e => {
        e.preventDefault();
        zone.classList.toggle('dragging', event === 'dragover');
        if (event === 'drop') {
            if (e.dataTransfer.files.length !== 1) { message.textContent = 'Selecciona un solo documento por carga.'; return; }
            input.files = e.dataTransfer.files;
        }
    });
    form.addEventListener('submit', e => {
        e.preventDefault();
        if (!form.reportValidity()) return;
        button.disabled = true;
        progress.classList.remove('d-none');
        progress.firstElementChild.style.width = '0%';
        message.textContent = 'Enviando documento…';
        const request = new XMLHttpRequest();
        request.open('POST', form.action);
        request.setRequestHeader('Accept', 'application/json');
        request.timeout = 120000;
        request.upload.onprogress = e => {
            if (!e.lengthComputable) return;
            const percent = Math.round(e.loaded / e.total * 100);
            progress.setAttribute('aria-valuenow', percent);
            progress.firstElementChild.style.width = percent + '%';
            if (percent === 100) message.textContent = 'Validando y guardando el original…';
        };
        const fail = text => { message.textContent = text; button.disabled = false; };
        request.onload = () => {
            let data = {};
            try { data = JSON.parse(request.responseText); } catch (_) {}
            if (request.status === 201) { window.location.reload(); return; }
            const detail = Object.values(data.errors || {}).flat().join(' ');
            fail(detail || ({401:'La sesión terminó. Recarga la página e ingresa de nuevo.',419:'La sesión caducó. Recarga la página.',413:'El archivo supera el límite del servidor.',429:'Demasiados intentos. Espera un minuto.'}[request.status]) || data.message || 'No se pudo cargar el documento. Intenta nuevamente.');
        };
        request.onerror = () => fail('No hay conexión con el servidor. Comprueba el listado antes de reintentar.');
        request.ontimeout = () => fail('El servidor tardó demasiado. Comprueba el listado antes de reintentar.');
        request.send(new FormData(form));
    });
})();


(() => {
    const list = document.getElementById('document-list');
    if (!list) return;
    const rows = Array.from(list.querySelectorAll('tr[data-uuid]'));
    const message = document.getElementById('processing-message');
    const colors = {pendiente:'text-bg-warning', procesando:'text-bg-primary', completado:'text-bg-success', error:'text-bg-danger'};
    const poll = async () => {
        if (document.hidden) { setTimeout(poll, 4000); return; }
        if (!rows.length) return;
        const url = new URL(list.dataset.statusUrl);
        rows.forEach(row => url.searchParams.append('uuids[]', row.dataset.uuid));
        try {
            const response = await fetch(url, {headers:{Accept:'application/json'}, credentials:'same-origin', cache:'no-store'});
            if (response.status === 401) { message.textContent = 'La sesión terminó. Recarga la página para ingresar.'; return; }
            if (!response.ok) throw new Error();
            const data = await response.json();
            for (const item of data.documentos) {
                const row = rows.find(row => row.dataset.uuid === item.uuid);
                if (!row) continue;
                row.dataset.state = item.estado;
                const deletion = row.querySelector('[data-delete]');
                deletion.querySelector('button').disabled = item.estado === 'procesando';
                deletion.querySelector('[name=confirmacion]').disabled = item.estado === 'procesando';
                row.querySelector('[data-review]').hidden = item.estado !== 'completado';
                row.querySelector('[data-pdf]').hidden = !item.pdf_disponible;
                const badge = row.querySelector('[data-badge]');
                badge.textContent = item.estado.charAt(0).toUpperCase() + item.estado.slice(1);
                badge.className = 'badge ' + (colors[item.estado] || 'text-bg-secondary');
                row.querySelector('[data-pages]').textContent = item.numero_paginas ?? 'Por determinar';
                row.querySelector('[data-method]').textContent = item.metodos || 'Pendiente';
                row.querySelector('[data-duration]').textContent = item.duracion_ms === null ? '' : (item.duracion_ms / 1000).toFixed(2) + ' s';
                row.querySelector('[data-error]').textContent = item.error || '';
                const retry = row.querySelector('[data-retry]');
                retry.hidden = !item.puede_encolar;
                retry.querySelector('button').textContent = item.estado === 'error' ? 'Reintentar' : 'Procesar';
            }
            const active = rows.some(row => ['pendiente','procesando'].includes(row.dataset.state));
            message.textContent = active ? 'El estado se actualiza automáticamente. El trabajador atiende un documento a la vez.' : 'Estados actualizados.';
        } catch (_) { message.textContent = 'No se pudo actualizar el estado. Se volverá a intentar.'; }
        setTimeout(poll, 4000);
    };
    setTimeout(poll, 1000);
})();
