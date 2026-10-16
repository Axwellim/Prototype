(() => {
    const form = document.getElementById('upload-form');
    if (!form) return;
    const fields = document.getElementById('upload-fields');
    const docCheck = document.getElementById('tipo-documento');
    const invCheck = document.getElementById('tipo-invitacion');
    const input = document.getElementById('archivo');
    const list = document.getElementById('document-parts');
    const invitationView = document.getElementById('invitation-file');
    const button = document.getElementById('upload-button');
    const message = document.getElementById('upload-message');
    const progress = document.getElementById('upload-progress');
    const confirm = document.getElementById('confirmacion-segundo');
    const dialog = document.getElementById('second-component-dialog');
    let documents = [];
    let invitation = null;
    let pending = null;
    let busy = false;
    const nextRole = () => invCheck.checked && (!docCheck.checked || documents.length > 0) && !invitation ? 'invitacion'
        : docCheck.checked && (!invCheck.checked || !documents.length) ? 'documento' : 'invitacion';
    const action = (label, handler) => {
        const control = document.createElement('button');
        control.type = 'button';
        control.className = 'btn btn-sm btn-outline-secondary ms-2';
        control.textContent = label;
        control.addEventListener('click', handler);
        return control;
    };
    const render = () => {
        if (!docCheck.checked && !invCheck.checked) docCheck.checked = true;
        document.getElementById('document-section').hidden = !docCheck.checked;
        document.getElementById('invitation-section').hidden = !invCheck.checked;
        const role = nextRole();
        input.multiple = role === 'documento';
        input.disabled = role === 'documento' ? documents.length >= 19 : invitation !== null;
        document.getElementById('upload-target').textContent = role === 'documento'
            ? 'Selecciona o arrastra las partes del documento' : 'Selecciona o arrastra una invitación';
        document.getElementById('upload-help').textContent = documents.length && invitation
            ? 'Ambos componentes están adjuntos. Quita uno para sustituirlo.'
            : role === 'documento' ? 'Un PDF con imágenes, solo un PDF o varias imágenes. Máximo 19 archivos.'
                : 'Un único PDF o imagen. Se guardará sin transcripción.';
        fields.disabled = busy;
        button.disabled = busy || (!documents.length && !invitation);
        if (!documents.length || !invitation) confirm.value = '0';
        list.replaceChildren();
        documents.forEach((file, index) => {
            const row = document.createElement('li');
            row.className = 'mb-2';
            row.append(document.createTextNode(file.name));
            if (index) row.append(action('Subir', () => {
                [documents[index-1], documents[index]] = [documents[index], documents[index-1]];
                render();
            }));
            if (index < documents.length-1) row.append(action('Bajar', () => {
                [documents[index+1], documents[index]] = [documents[index], documents[index+1]];
                render();
            }));
            row.append(action('Quitar', () => { documents.splice(index, 1); render(); }));
            list.append(row);
        });
        invitationView.replaceChildren();
        if (invitation) {
            invitationView.append(document.createTextNode(invitation.name));
            invitationView.append(action('Quitar invitación', () => { invitation = null; render(); }));
        }
    };
    const validate = (docs, invite) => {
        const all = [...docs, ...(invite ? [invite] : [])];
        if (docs.length > 19) return 'El documento admite hasta 19 archivos.';
        if (docs.filter(file => /\.pdf$/i.test(file.name)).length > 1) return 'El documento admite un solo PDF y varias imágenes.';
        if (all.some(file => !/\.(pdf|jpe?g|png)$/i.test(file.name))) return 'Selecciona archivos PDF, JPG o PNG.';
        if (all.reduce((sum, file) => sum + file.size, 0) > Number(fields.dataset.maxBytes)) return 'El conjunto supera el tamaño máximo permitido.';
        return '';
    };
    const accept = (role, files) => {
        if (!files.length) return;
        if (role === 'invitacion' && (files.length !== 1 || invitation)) {
            message.textContent = 'La invitación admite un único archivo. Quita la invitación actual para sustituirla.';
            return;
        }
        const docs = role === 'documento' ? [...documents, ...files] : documents;
        const invite = role === 'invitacion' ? files[0] : invitation;
        const error = validate(docs, invite);
        if (error) { message.textContent = error; return; }
        const commit = () => {
            documents = docs;
            invitation = invite;
            confirm.value = documents.length && invitation ? '1' : '0';
            message.textContent = '';
            render();
        };
        if ((role === 'invitacion' && documents.length) || (role === 'documento' && invitation && !documents.length)) {
            pending = commit;
            document.getElementById('second-component-message').textContent = role === 'invitacion'
                ? 'Este archivo se considerará una invitación y se guardará como PDF sin transcripción. ¿Deseas adjuntarlo?'
                : 'Estos archivos se considerarán un documento y serán procesados para obtener su transcripción. ¿Deseas continuar?';
            dialog.showModal();
        } else commit();
    };
    document.getElementById('second-accept').addEventListener('click', () => {
        const commit = pending; pending = null; dialog.close(); if (commit) commit();
    });
    document.getElementById('second-cancel').addEventListener('click', () => { pending = null; dialog.close(); });
    dialog.addEventListener('cancel', () => { pending = null; });
    docCheck.addEventListener('change', () => {
        if (!docCheck.checked) { documents = []; if (!invCheck.checked) invCheck.checked = true; }
        render();
    });
    invCheck.addEventListener('change', () => {
        if (!invCheck.checked) { invitation = null; if (!docCheck.checked) docCheck.checked = true; }
        render();
    });
    input.addEventListener('change', () => {
        if (input.files.length && !input.disabled) accept(nextRole(), Array.from(input.files));
        input.value = '';
    });
    const zone = document.getElementById('dropzone');
    for (const event of ['dragover', 'dragleave', 'drop']) zone.addEventListener(event, e => {
        e.preventDefault();
        zone.classList.toggle('dragging', event === 'dragover');
        if (event === 'drop' && !busy && !input.disabled) accept(nextRole(), Array.from(e.dataTransfer.files));
    });
    form.addEventListener('submit', e => {
        e.preventDefault();
        if (busy || !documents.length && !invitation) return;
        if (docCheck.checked && !documents.length) { message.textContent = 'Adjunta el documento o desmarca Documento para guardar solo la invitación.'; return; }
        if (invCheck.checked && !invitation) { message.textContent = 'Adjunta la invitación o desmarca Invitación.'; return; }
        const error = validate(documents, invitation);
        if (error) { message.textContent = error; return; }
        const body = new FormData(form);
        documents.forEach(file => body.append('archivos[]', file));
        if (invitation) body.append('invitacion', invitation);
        busy = true; render();
        progress.classList.remove('d-none');
        progress.firstElementChild.style.width = '0%';
        message.textContent = 'Enviando archivos…';
        const request = new XMLHttpRequest();
        request.open('POST', form.action);
        request.setRequestHeader('Accept', 'application/json');
        request.timeout = 120000;
        request.upload.onprogress = event => {
            if (!event.lengthComputable) return;
            const percent = Math.round(event.loaded / event.total * 100);
            progress.setAttribute('aria-valuenow', percent);
            progress.firstElementChild.style.width = percent + '%';
        };
        const fail = text => { busy = false; render(); message.textContent = text; };
        request.onload = () => {
            let data = {};
            try { data = JSON.parse(request.responseText); } catch (_) {}
            if (request.status === 201) { window.location.reload(); return; }
            fail(Object.values(data.errors || {}).flat().join(' ') || data.message || 'No se pudo guardar. Comprueba la sesión y el tamaño de los archivos.');
        };
        request.onerror = () => fail('No hay conexión. Comprueba el historial antes de reintentar.');
        request.ontimeout = () => fail('La carga tardó demasiado. Comprueba el historial antes de reintentar.');
        request.send(body);
    });
    render();
})();
