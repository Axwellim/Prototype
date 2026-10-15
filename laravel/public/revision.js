const configNode = document.getElementById('review-data');
if (configNode) {
    const config = JSON.parse(configNode.textContent);
    const reference = document.getElementById('reference-text');
    const notes = document.getElementById('reference-notes');
    const form = document.getElementById('reference-form');
    const revision = document.getElementById('reference-revision');
    const save = document.getElementById('save-reference');
    const saveMessage = document.getElementById('save-message');
    const draftState = document.getElementById('draft-state');
    const extracted = document.getElementById('extracted-text');
    const copy = document.getElementById('copy-draft');
    const variant = document.getElementById('variant');
    const lineEndings = text => text.replace(/\r\n?/g, '\n');
    let baseline = {texto:lineEndings(config.baseline.texto), observaciones:lineEndings(config.baseline.observaciones)};
    let dirty = false;
    let qualityStale = false;
    const qualityForm = document.getElementById('quality-form');
    qualityForm?.addEventListener('submit', event => {
        if (dirty || qualityStale) {
            event.preventDefault();
            saveMessage.textContent = 'Guarda los cambios y recarga la página antes de evaluar la referencia actual.';
        } else {
            qualityForm.querySelector('button').disabled = true;
            qualityForm.querySelector('button').textContent = 'Calculando…';
        }
    });
    const current = () => ({texto:reference.value, observaciones:notes.value});
    const updateDraft = () => {
        dirty = JSON.stringify(current()) !== JSON.stringify(baseline);
        draftState.textContent = dirty ? 'Cambios sin guardar' : 'Sin cambios pendientes';
        copy.disabled = reference.value.length > 0 || extracted.value.length === 0;
        const results = document.getElementById('quality-results');
        if (results) results.hidden = dirty || qualityStale;
        if (qualityForm) qualityForm.querySelector('button').disabled = dirty || qualityStale;
    };
    reference.addEventListener('input', updateDraft);
    notes.addEventListener('input', updateDraft);
    window.addEventListener('beforeunload', event => {
        if (dirty) { event.preventDefault(); event.returnValue = ''; }
    });
    copy.addEventListener('click', () => {
        if (reference.value.length) return;
        reference.value = extracted.value;
        updateDraft();
        reference.focus();
    });
    const showVariant = () => {
        if (!variant) return;
        const selected = config.variantes[Number(variant.value)];
        extracted.value = selected.texto;
        document.getElementById('variant-operations').textContent = selected.operaciones.length
            ? 'Operaciones: ' + selected.operaciones.join(' · ') : 'Sin filtros adicionales. La orientación puede haberse corregido antes del OCR.';
        updateDraft();
    };
    variant?.addEventListener('change', showVariant);
    showVariant();
    updateDraft();
    form.addEventListener('submit', async event => {
        event.preventDefault();
        if (save.disabled || !form.reportValidity()) return;
        const snapshot = current();
        const data = {_token:form.elements._token.value, numero_pagina:Number(form.elements.numero_pagina.value),
            texto_referencia:snapshot.texto, observaciones:snapshot.observaciones, revision:revision.value ? Number(revision.value) : null};
        save.disabled = true;
        saveMessage.textContent = 'Guardando transcripción…';
        saveMessage.className = 'small mt-3 mb-0 text-secondary';
        try {
            const response = await fetch(form.action, {method:'POST', body:JSON.stringify(data), headers:{Accept:'application/json','Content-Type':'application/json'}, credentials:'same-origin', signal:AbortSignal.timeout(30000)});
            let result = {};
            try { result = await response.json(); } catch (_) {}
            if (!response.ok) {
                const errors = Object.values(result.errors || {}).flat().join(' ');
                const message = response.status === 419 ? 'La sesión caducó. Conserva tu borrador y recarga la página.'
                    : response.status === 401 ? 'La sesión terminó. Conserva tu borrador antes de volver a ingresar.'
                    : response.status === 429 ? 'Demasiados intentos. Espera un minuto y vuelve a guardar.'
                    : errors || result.message || 'No se pudo guardar. Conserva el borrador e inténtalo nuevamente.';
                throw new Error(message);
            }
            if (!Number.isInteger(result.revision)) throw new Error('No se pudo confirmar el guardado. Conserva tu borrador y recarga para comprobarlo.');
            qualityStale ||= revision.value !== String(result.revision);
            revision.value = result.revision;
            document.getElementById('reference-meta').textContent = 'Última versión: ' + result.guardado_en + ' · ' + result.autor;
            document.getElementById('refresh-history').hidden = false;
            baseline = snapshot;
            updateDraft();
            saveMessage.className = 'small mt-3 mb-0 text-success';
            saveMessage.textContent = dirty ? 'Versión guardada. Tienes cambios posteriores sin guardar.' : 'Transcripción de referencia guardada. El texto automático se conserva.';
        } catch (error) {
            saveMessage.className = 'small mt-3 mb-0 text-danger';
            saveMessage.textContent = error.name === 'TimeoutError' || error instanceof TypeError
                ? 'No se pudo confirmar el guardado. Conserva tu borrador y comprueba la conexión antes de reintentar.' : error.message;
        } finally { save.disabled = false; }
    });

    const container = document.getElementById('preview-container');
    const status = document.getElementById('preview-status');
    const controls = ['zoom-out','zoom-in','zoom-fit'].map(id => document.getElementById(id));
    let zoom = 1;
    try { zoom = Number(sessionStorage.getItem('review-zoom:' + config.uuid)) || 1; } catch (_) {}
    zoom = Math.max(0.5, Math.min(2, zoom));
    let pdf = null;
    let renderTask = null;
    let sequence = 0;
    const updateZoom = () => {
        document.getElementById('zoom-label').textContent = Math.round(zoom * 100) + ' %';
        controls[0].disabled = zoom <= 0.5;
        controls[1].disabled = zoom >= 2;
        controls[2].disabled = false;
        try { sessionStorage.setItem('review-zoom:' + config.uuid, String(zoom)); } catch (_) {}
    };
    const image = document.getElementById('original-image');
    const render = async () => {
        const ticket = ++sequence;
        updateZoom();
        if (image) {
            if (!image.naturalWidth) return;
            image.style.width = Math.max(1, container.clientWidth - 32) * zoom + 'px';
            status.textContent = 'Imagen original. Zoom respecto al ancho del panel.';
            return;
        }
        if (!pdf) return;
        try {
            if (renderTask) {
                renderTask.cancel();
                try { await renderTask.promise; } catch (_) {}
            }
            if (ticket !== sequence) return;
            status.textContent = 'Renderizando página…';
            const page = await pdf.getPage(config.pagina);
            if (ticket !== sequence) return;
            const initial = page.getViewport({scale:1});
            let scale = Math.max(1, container.clientWidth - 32) / initial.width * zoom;
            const ratio = Math.min(window.devicePixelRatio || 1, 2);
            let viewport = page.getViewport({scale});
            const limit = Math.min(1, Math.sqrt(6000000 / (viewport.width * viewport.height * ratio * ratio)));
            viewport = page.getViewport({scale:scale * limit});
            const canvas = document.createElement('canvas');
            canvas.setAttribute('role','img');
            canvas.setAttribute('aria-label','Página ' + config.pagina + ' del documento original');
            canvas.width = Math.ceil(viewport.width * ratio);
            canvas.height = Math.ceil(viewport.height * ratio);
            canvas.style.width = viewport.width + 'px';
            canvas.style.height = viewport.height + 'px';
            document.getElementById('pdf-surface').replaceChildren(canvas);
            const task = page.render({canvasContext:canvas.getContext('2d'), viewport,
                transform:ratio !== 1 ? [ratio,0,0,ratio,0,0] : null});
            renderTask = task;
            await task.promise;
            if (ticket === sequence) status.textContent = limit < 1
                ? 'Página ' + config.pagina + '. Resolución limitada para proteger la memoria del navegador.'
                : 'Página ' + config.pagina + ' del original. Zoom respecto al ancho del panel.';
        } catch (error) {
            if (error.name !== 'RenderingCancelledException' && ticket === sequence) status.textContent = 'No se pudo mostrar esta página. Puedes abrir el original en otra pestaña.';
        }
    };
    controls[0].addEventListener('click', () => { zoom = Math.max(0.5, zoom - 0.25); render(); });
    controls[1].addEventListener('click', () => { zoom = Math.min(2, zoom + 0.25); render(); });
    controls[2].addEventListener('click', () => { zoom = 1; render(); });
    let resizeTimer;
    new ResizeObserver(() => { clearTimeout(resizeTimer); resizeTimer = setTimeout(render, 150); }).observe(container);
    if (image) {
        image.addEventListener('load', render);
        image.addEventListener('error', () => { status.textContent = 'No se pudo cargar la imagen. Comprueba tu sesión o abre el original.'; controls.forEach(control => control.disabled = true); });
        if (image.complete && image.naturalWidth) render();
    } else {
        try {
            const pdfjs = await import(config.pdfjsUrl);
            pdfjs.GlobalWorkerOptions.workerSrc = config.workerUrl;
            pdf = await pdfjs.getDocument({url:config.originalUrl, withCredentials:true,
                isEvalSupported:false, enableXfa:false, stopAtErrors:true,
                cMapUrl:config.cmapUrl, cMapPacked:true, standardFontDataUrl:config.fontUrl, wasmUrl:config.wasmUrl}).promise;
            await render();
        } catch (_) { status.textContent = 'No se pudo cargar el PDF. Comprueba tu sesión o abre el original en otra pestaña.'; }
    }
}
