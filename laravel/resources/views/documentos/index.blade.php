@extends('layout')
@section('content')
<div class="d-flex flex-wrap align-items-center justify-content-between gap-3 mb-4">
    <div><span class="eyebrow">ARCHIVO INSTITUCIONAL</span><h1 class="mt-2 mb-1">Digitalización documental</h1><p class="text-secondary mb-0">Carga tus documentos y consulta el avance de su extracción de texto.</p></div>
    <span class="badge rounded-pill text-bg-light border p-3">Extracción en segundo plano</span>
</div>
<div class="card border-0 shadow-sm p-4 mb-4">
    <h2 class="h5">Nuevo documento</h2>
    <form id="upload-form" method="post" action="{{ route('documentos.store') }}" enctype="multipart/form-data">
        @csrf
        <fieldset id="upload-fields" class="my-3" data-max-bytes="{{ config('documentos.max_upload_kb') * 1024 - 32768 }}">
            <div class="d-flex gap-4 mb-3">
                <label><input id="tipo-documento" type="checkbox" checked> Documento</label>
                <label><input id="tipo-invitacion" type="checkbox"> Invitación</label>
            </div>
            <label for="archivo" class="dropzone d-block text-center p-4 mb-3" id="dropzone">
                <span class="d-block h5" id="upload-target">Selecciona o arrastra las partes del documento</span>
                <span class="text-secondary" id="upload-help">Un PDF con imágenes, solo un PDF o varias imágenes. Máximo 19 archivos.</span>
                <input id="archivo" class="form-control mt-3" type="file" accept=".pdf,.jpg,.jpeg,.png" multiple>
            </label>
            <section id="document-section">
                <p class="small text-secondary">Ordena las partes: las páginas del PDF mantienen su orden interno. Se generará un solo PDF con transcripción.</p>
                <ol id="document-parts" class="ps-4"></ol>
            </section>
            <section id="invitation-section" hidden>
                <p class="small text-secondary mt-2">Se guarda como PDF sin transcripción. Puedes cargar una invitación sola desmarcando Documento.</p>
                <div id="invitation-file"></div>
            </section>
            <input type="hidden" name="confirmacion_segundo" id="confirmacion-segundo" value="0">
            <p class="small text-secondary mt-3">Hasta {{ number_format(config('documentos.max_upload_kb') / 1024, 1) }} MB entre todos los archivos. Los originales se conservan de forma privada.</p>
        </fieldset>
        <noscript><p class="alert alert-warning">Activa JavaScript para seleccionar y ordenar los archivos.</p></noscript>
        <div class="progress mb-3 d-none" id="upload-progress" role="progressbar" aria-label="Progreso de carga" aria-valuemin="0" aria-valuemax="100"><div class="progress-bar" style="width:0%"></div></div>
        <p id="upload-message" aria-live="polite" class="small mb-3"></p>
        <button class="btn btn-primary px-4" id="upload-button">Guardar y procesar</button>
    </form>
</div>
<p id="processing-message" class="small text-secondary" aria-live="polite"></p>
<div class="card border-0 shadow-sm overflow-hidden" id="document-list" data-status-url="{{ route('documentos.estados') }}">
    <div class="p-4 d-flex align-items-center justify-content-between"><h2 class="h5 mb-0">Documentos cargados</h2><span class="text-secondary small">{{ $documentos->total() }} registros</span></div>
    <div class="table-responsive document-history" tabindex="0" role="region" aria-label="Historial de documentos, desplazamiento vertical y horizontal"><table class="table align-middle mb-0">
        <thead><tr><th class="ps-4">Archivo / fecha</th><th>Formato recibido</th><th>Tamaño recibido</th><th>Páginas</th><th>Método / tiempo</th><th>Estado / acción</th></tr></thead>
        <tbody>@forelse ($documentos as $documento)
            <tr data-uuid="{{ $documento->uuid }}" data-state="{{ $documento->estado_procesamiento }}"><td class="ps-4 filename"><span class="fw-semibold">{{ $documento->nombre_original }}</span><small class="d-block text-secondary">{{ $documento->fecha_carga->format('d/m/Y H:i') }}</small><small class="d-block text-secondary">{{ $documento->uuid }}</small></td>
                <td>{{ $documento->tipo_registro === 'invitacion' ? 'Invitación' : ($documento->tipo_archivo === 'zip' ? 'Documento compuesto' : strtoupper($documento->tipo_archivo)) }}@if ($documento->invitacion_nombre)<small class="d-block">Con invitación adjunta</small>@endif</td><td>{{ number_format($documento->tamano_bytes / 1024, 1) }} KB</td><td data-pages>{{ $documento->numero_paginas ?? 'Por determinar' }}</td>
                <td><span data-method>{{ $documento->tipo_registro === 'invitacion' ? 'Sin transcripción' : ($documento->metodos_extraccion ?? 'Pendiente') }}</span><small class="d-block text-secondary" data-duration>{{ $documento->duracion_total_ms !== null ? number_format($documento->duracion_total_ms / 1000, 2).' s' : '' }}</small></td>
                <td><span data-badge class="badge {{ ['completado'=>'text-bg-success','error'=>'text-bg-danger','procesando'=>'text-bg-primary'][$documento->estado_procesamiento] ?? 'text-bg-warning' }}">{{ ucfirst($documento->estado_procesamiento) }}</span>
                    <a data-review class="btn btn-sm btn-outline-primary mt-2" href="{{ route('documentos.revision', $documento) }}" @if ($documento->estado_procesamiento !== 'completado') hidden @endif>Revisar</a>
                    <a data-pdf class="btn btn-sm btn-outline-secondary mt-2" href="{{ route('documentos.pdf', $documento) }}" target="_blank" rel="noopener" @if (! $documento->ruta_pdf || $documento->estado_procesamiento !== 'completado') hidden @endif>PDF</a>
                    <small data-error class="d-block text-danger mt-1">{{ $documento->error_procesamiento }}</small>
                    <form data-retry method="post" action="{{ route('documentos.reintentar', $documento) }}" @if (! ($documento->estado_procesamiento === 'error' || ($documento->estado_procesamiento === 'pendiente' && $documento->solicitud_uuid === null))) hidden @endif>
                        @csrf <button class="btn btn-sm btn-outline-secondary mt-2">{{ $documento->estado_procesamiento === 'error' ? 'Reintentar' : 'Procesar' }}</button>
                    </form>
                    <form data-delete data-document-name="{{ $documento->nombre_original }}" method="post" action="{{ route('documentos.destroy', $documento) }}">
                        @csrf @method('DELETE')
                        <label class="small d-block mt-2"><input type="checkbox" name="confirmacion" value="1" required @disabled($documento->estado_procesamiento === 'procesando')> Retirar del historial</label>
                        <button class="btn btn-sm btn-outline-danger mt-1" @disabled($documento->estado_procesamiento === 'procesando')>Eliminar</button>
                        <small class="d-block text-secondary">Se conservan archivos y transcripciones.</small>
                    </form>
                </td></tr>
        @empty <tr><td colspan="6" class="text-center text-secondary p-5">Aún no hay documentos. Carga el primero para comenzar.</td></tr>@endforelse</tbody>
    </table></div>
    @if ($documentos->hasPages())<div class="p-3">{{ $documentos->links('pagination::simple-bootstrap-5') }}</div>@endif
</div>
<dialog id="second-component-dialog" class="border-0 rounded shadow p-4" aria-labelledby="second-component-title">
    <h2 id="second-component-title" class="h5">Confirmar segundo componente</h2>
    <p id="second-component-message"></p>
    <div class="d-flex gap-2"><button type="button" id="second-accept" class="btn btn-primary">Continuar</button><button type="button" id="second-cancel" class="btn btn-outline-secondary">Cancelar</button></div>
</dialog>
@endsection
@push('scripts')<script src="{{ asset('carga-compuesta.js') }}" defer></script><script src="{{ asset('documentos.js') }}" defer></script>@endpush
