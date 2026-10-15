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
        <label for="archivo" class="dropzone d-block text-center p-4 my-3" id="dropzone">
            <span class="d-block h5">Selecciona o arrastra un documento</span>
            <span class="text-secondary">PDF, JPG, JPEG o PNG · Hasta {{ number_format(config('documentos.max_upload_kb') / 1024, 1) }} MB</span>
            <input id="archivo" name="archivo" class="form-control mt-3" type="file" accept=".pdf,.jpg,.jpeg,.png" required>
        </label>
        <p class="small text-secondary">El original se almacena de forma privada. Puedes continuar mientras el documento se procesa.</p>
        <p class="small text-secondary">El sistema digitaliza las páginas automáticamente y guarda un PDF con su transcripción.</p>
        <div class="progress mb-3 d-none" id="upload-progress" role="progressbar" aria-label="Progreso de carga" aria-valuemin="0" aria-valuemax="100"><div class="progress-bar" style="width:0%"></div></div>
        <p id="upload-message" aria-live="polite" class="small mb-3"></p>
        <button class="btn btn-primary px-4" id="upload-button">Cargar documento</button>
    </form>
</div>
<p id="processing-message" class="small text-secondary" aria-live="polite"></p>
<div class="card border-0 shadow-sm overflow-hidden" id="document-list" data-status-url="{{ route('documentos.estados') }}">
    <div class="p-4 d-flex align-items-center justify-content-between"><h2 class="h5 mb-0">Documentos cargados</h2><span class="text-secondary small">{{ $documentos->total() }} registros</span></div>
    <div class="table-responsive document-history" tabindex="0" role="region" aria-label="Historial de documentos, desplazamiento vertical y horizontal"><table class="table align-middle mb-0">
        <thead><tr><th class="ps-4">Archivo / fecha</th><th>Formato recibido</th><th>Tamaño recibido</th><th>Páginas</th><th>Método / tiempo</th><th>Estado / acción</th></tr></thead>
        <tbody>@forelse ($documentos as $documento)
            <tr data-uuid="{{ $documento->uuid }}" data-state="{{ $documento->estado_procesamiento }}"><td class="ps-4 filename"><span class="fw-semibold">{{ $documento->nombre_original }}</span><small class="d-block text-secondary">{{ $documento->fecha_carga->format('d/m/Y H:i') }}</small><small class="d-block text-secondary">{{ $documento->uuid }}</small></td>
                <td>{{ strtoupper($documento->tipo_archivo) }}</td><td>{{ number_format($documento->tamano_bytes / 1024, 1) }} KB</td><td data-pages>{{ $documento->numero_paginas ?? 'Por determinar' }}</td>
                <td><span data-method>{{ $documento->metodos_extraccion ?? 'Pendiente' }}</span><small class="d-block text-secondary" data-duration>{{ $documento->duracion_total_ms !== null ? number_format($documento->duracion_total_ms / 1000, 2).' s' : '' }}</small></td>
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
@endsection
@push('scripts')<script src="{{ asset('documentos.js') }}" defer></script>@endpush
