const configNode = document.getElementById('review-data');
if (configNode) {
    const config = JSON.parse(configNode.textContent);
    window.addEventListener('pageshow', event => {
        if (event.persisted || (location.hash && !location.hash.startsWith('#preview-page-'))) return;
        requestAnimationFrame(() => {
            const heading = document.getElementById('review-start');
            if (heading) window.scrollTo({top: Math.max(0, window.scrollY + heading.getBoundingClientRect().top - 12), behavior:'instant'});
        });
    });
    const bindReferencePanel = () => {
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
        let selectedText = config.textos?.find(page => page.numero === config.pagina)?.texto ?? extracted.value;
        const lineEndings = text => text.replace(/\r\n?/g, '\n');
        let baseline = {texto:lineEndings(config.baseline.texto), observaciones:lineEndings(config.baseline.observaciones)};
        let dirty = false;
        let saving = false;
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
            copy.disabled = reference.value.length > 0 || selectedText.length === 0;
            const results = document.getElementById('quality-results');
            if (results) results.hidden = dirty || qualityStale;
            if (qualityForm) qualityForm.querySelector('button').disabled = dirty || qualityStale;
        };
        reference.addEventListener('input', updateDraft);
        notes.addEventListener('input', updateDraft);
        copy.addEventListener('click', () => {
            if (reference.value.length) return;
            reference.value = selectedText;
            updateDraft();
            reference.focus();
        });
        const showVariant = () => {
            if (variant) {
                const selected = config.variantes[Number(variant.value)];
                selectedText = selected.texto;
                document.getElementById('variant-operations').textContent = selected.operaciones.length
                    ? 'Operaciones de la página seleccionada: ' + selected.operaciones.join(' · ') : 'Página seleccionada sin filtros adicionales.';
            }
            extracted.value = config.textos?.length > 1 ? config.textos.map(page =>
                'Página ' + page.numero + '\n\n' + (page.numero === config.pagina ? selectedText : page.texto)).join('\n\n') : selectedText;
            scrollTranscription();
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
            saving = true;
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
            } finally { save.disabled = false; saving = false; }
        });
        return {isDirty: () => dirty, isSaving: () => saving};
    };
    let panel = bindReferencePanel();
    window.addEventListener('beforeunload', event => {
        if (panel.isDirty()) { event.preventDefault(); event.returnValue = ''; }
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
    let collectionObserver = null;
    let collectionVersion = 0;
    const renderCollection = async () => {
        const version = ++collectionVersion;
        collectionObserver?.disconnect();
        renderTask?.cancel();
        const surface = document.getElementById('pdf-surface');
        const first = await pdf.getPage(1);
        if (version !== collectionVersion) return;
        const original = first.getViewport({scale:1});
        const width = Math.max(1, container.clientWidth - 32) * zoom;
        const height = original.height * width / original.width;
        surface.querySelectorAll('canvas').forEach(canvas => { canvas.width = canvas.height = 0; });
        surface.replaceChildren();
        const visible = new Set();
        const queue = [];
        let drawing = false;
        let activeCard = null;
        const release = card => {
            if (card === activeCard) return;
            const canvas = card.querySelector('canvas');
            if (canvas) { canvas.width = canvas.height = 0; canvas.remove(); }
            card.dataset.rendered = 'false';
        };
        const drawNext = async () => {
            if (drawing) return;
            drawing = true;
            try {
                while (queue.length && version === collectionVersion) {
                    const card = queue.shift();
                    if (!visible.has(card) || card.querySelector('canvas')) continue;
                    activeCard = card;
                    try {
                        const number = Number(card.dataset.page);
                        const page = await pdf.getPage(number);
                        if (version !== collectionVersion) break;
                        const base = page.getViewport({scale:1});
                        const ratio = Math.min(window.devicePixelRatio || 1, 2);
                        const scale = width / base.width;
                        const raw = page.getViewport({scale});
                        const limit = Math.min(1, Math.sqrt(6000000 / (raw.width * raw.height * ratio * ratio)));
                        const viewport = page.getViewport({scale:scale * limit});
                        const canvas = document.createElement('canvas');
                        canvas.setAttribute('role', 'img');
                        canvas.setAttribute('aria-label', 'Página ' + number + ' del documento unificado');
                        canvas.width = Math.ceil(viewport.width * ratio);
                        canvas.height = Math.ceil(viewport.height * ratio);
                        canvas.style.width = viewport.width + 'px';
                        canvas.style.height = viewport.height + 'px';
                        card.querySelector('.unified-page-surface').append(canvas);
                        const task = page.render({canvasContext:canvas.getContext('2d'), viewport,
                            transform:ratio !== 1 ? [ratio,0,0,ratio,0,0] : null});
                        renderTask = task;
                        await task.promise;
                        if (version === collectionVersion) {
                            card.querySelector('.unified-page-surface').style.minHeight = canvas.style.height;
                            card.dataset.rendered = 'true';
                        }
                    } catch (error) {
                        if (error.name !== 'RenderingCancelledException' && version === collectionVersion) {
                            card.querySelector('.unified-page-error').textContent = 'No se pudo mostrar esta página. Puedes abrir el PDF unificado completo.';
                        }
                    } finally {
                        activeCard = null;
                        if (!visible.has(card)) release(card);
                    }
                }
            } finally { drawing = false; }
        };
        for (let number = 1; number <= pdf.numPages; number++) {
            const card = document.createElement('section');
            card.className = 'unified-page mb-3';
            card.dataset.page = String(number);
            card.id = 'preview-page-' + number;
            const link = document.createElement('a');
            link.className = 'd-block bg-white p-2 small';
            link.href = config.reviewUrl + '?pagina=' + number + '#preview-page-' + number;
            link.addEventListener('click', event => {
                if (event.ctrlKey || event.metaKey || event.shiftKey || event.altKey || event.button !== 0) return;
                event.preventDefault();
                selectPage(number);
            });
            const origin = config.origenes?.find(item => number >= item.inicio && number <= item.fin);
            link.textContent = 'Página ' + number + ' de ' + pdf.numPages + (origin ? ' · ' + origin.nombre : '') + ' · Revisar transcripción';
            if (number === config.pagina) link.setAttribute('aria-current', 'page');
            const slot = document.createElement('div');
            slot.className = 'unified-page-surface';
            slot.addEventListener('click', () => {
                if (number !== config.pagina) selectPage(number);
            });
            slot.style.minHeight = height + 'px';
            slot.style.width = width + 'px';
            const error = document.createElement('p');
            error.className = 'unified-page-error small text-danger';
            card.append(link, slot, error);
            surface.append(card);
        }
        status.textContent = '';
        collectionObserver = new IntersectionObserver(entries => {
            for (const entry of entries) {
                if (entry.isIntersecting) {
                    visible.add(entry.target);
                    if (!queue.includes(entry.target)) queue.push(entry.target);
                } else { visible.delete(entry.target); release(entry.target); }
            }
            drawNext();
        }, {root:container, rootMargin:'150px 0px'});
        surface.querySelectorAll('.unified-page').forEach(card => collectionObserver.observe(card));
        container.scrollTop = document.getElementById('preview-page-' + config.pagina).offsetTop;
    };
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
        if (config.conjunto) {
            try { await renderCollection(); }
            catch (_) { status.textContent = 'No se pudo mostrar el conjunto. Abre el PDF unificado completo.'; }
            return;
        }
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
    let navigationVersion = 0;
    let navigationRequest = null;
    const pageInput = document.getElementById('pagina');
    const navigationMessage = document.createElement('p');
    navigationMessage.className = 'small text-danger mb-0';
    navigationMessage.setAttribute('role', 'status');
    navigationMessage.hidden = true;
    document.getElementById('preview-page-form').after(navigationMessage);
    const tellNavigation = message => {
        navigationMessage.textContent = message;
        navigationMessage.hidden = !message;
    };
    function scrollTranscription() {
        const text = document.getElementById('extracted-text');
        if (!text) return;
        let offset = 0;
        if (config.textos?.length > 1) {
            for (const page of config.textos) {
                if (page.numero === config.pagina) break;
                offset += ('Página ' + page.numero + '\n\n' + page.texto + '\n\n').replace(/\r\n?/g, '\n').length;
            }
        }
        if (!offset) { text.scrollTop = 0; return; }
        const style = getComputedStyle(text);
        const mirror = document.createElement('div');
        for (const property of ['fontFamily','fontSize','fontWeight','fontStyle','lineHeight','letterSpacing',
            'textIndent','tabSize','paddingTop','paddingRight','paddingBottom','paddingLeft','wordBreak']) {
            mirror.style[property] = style[property];
        }
        Object.assign(mirror.style, {position:'fixed',left:'-100000px',top:'0',width:text.clientWidth+'px',
            boxSizing:'border-box',whiteSpace:'pre-wrap',overflowWrap:'break-word',visibility:'hidden'});
        mirror.setAttribute('aria-hidden','true');
        mirror.append(document.createTextNode(text.value.slice(0,offset)));
        const marker = document.createElement('span');
        marker.textContent = '|';
        mirror.append(marker);
        document.body.append(mirror);
        const top = marker.getBoundingClientRect().top - mirror.getBoundingClientRect().top - parseFloat(style.paddingTop || '0');
        mirror.remove();
        text.scrollTop = Math.max(0,top);
    }
    const positionPage = () => {
        pageInput.value = config.pagina;
        document.querySelectorAll('.unified-page > a').forEach(link => {
            if (Number(link.parentElement.dataset.page) === config.pagina) link.setAttribute('aria-current', 'page');
            else link.removeAttribute('aria-current');
        });
        const card = document.getElementById('preview-page-' + config.pagina);
        if (card) container.scrollTo({top:card.offsetTop, behavior:'instant'});
        scrollTranscription();
    };
    async function selectPage(number, push = true) {
        if (!Number.isInteger(number) || number < 1 || number > config.textos.length) {
            tellNavigation('Introduce un número de página válido.');
            return false;
        }
        if (panel.isSaving()) {
            tellNavigation('Espera a que termine de guardarse la referencia.');
            return false;
        }
        if (number === config.pagina) { positionPage(); return true; }
        if (panel.isDirty() && !window.confirm('Hay cambios sin guardar en la referencia. ¿Deseas descartarlos y cambiar de página?')) {
            pageInput.value = config.pagina;
            return false;
        }
        const ticket = ++navigationVersion;
        navigationRequest?.abort();
        navigationRequest = new AbortController();
        const oldPanel = document.querySelector('[aria-labelledby="extraction-heading"]');
        oldPanel.inert = true;
        oldPanel.setAttribute('aria-busy', 'true');
        tellNavigation('Cargando página…');
        try {
            const url = new URL(config.reviewUrl, location.href);
            url.searchParams.set('pagina', number);
            const response = await fetch(url, {credentials:'same-origin', redirect:'error',
                headers:{Accept:'text/html'}, signal:AbortSignal.any([navigationRequest.signal, AbortSignal.timeout(30000)])});
            if (!response.ok) throw new Error('No se pudo cargar la página. Comprueba la conexión y la sesión.');
            const html = new DOMParser().parseFromString(await response.text(), 'text/html');
            if (ticket !== navigationVersion) return false;
            const data = JSON.parse(html.getElementById('review-data')?.textContent || 'null');
            const nextPanel = html.querySelector('[aria-labelledby="extraction-heading"]');
            if (!data || data.uuid !== config.uuid || data.pagina !== number || !nextPanel) {
                throw new Error('No se pudo confirmar la página recibida. Intenta nuevamente.');
            }
            oldPanel.replaceWith(document.importNode(nextPanel, true));
            Object.assign(config, data);
            configNode.textContent = JSON.stringify(config);
            panel = bindReferencePanel();
            positionPage();
            if (!config.conjunto) await render();
            if (push) history.pushState({reviewPage:number}, '', url.pathname + url.search + '#preview-page-' + number);
            tellNavigation('');
            return true;
        } catch (error) {
            if (ticket === navigationVersion) {
                pageInput.value = config.pagina;
                tellNavigation(error.name === 'AbortError' ? '' : 'No se pudo cambiar de página. Tu contenido actual se conserva. Intenta nuevamente.');
            }
            return false;
        } finally {
            if (ticket === navigationVersion) {
                oldPanel.inert = false;
                oldPanel.removeAttribute('aria-busy');
            }
        }
    }
    document.getElementById('preview-page-form').addEventListener('submit', event => {
        event.preventDefault();
        if (event.currentTarget.reportValidity()) selectPage(Number(pageInput.value));
    });
    window.addEventListener('popstate', async () => {
        const requested = Number(new URL(location.href).searchParams.get('pagina') || 1);
        if (!await selectPage(requested, false)) {
            history.pushState({reviewPage:config.pagina}, '', config.reviewUrl + '?pagina=' + config.pagina);
        }
    });
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
