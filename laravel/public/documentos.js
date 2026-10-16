


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
                row.querySelector('[data-method]').textContent = item.sin_transcripcion ? 'Sin transcripción' : (item.metodos || 'Pendiente');
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
