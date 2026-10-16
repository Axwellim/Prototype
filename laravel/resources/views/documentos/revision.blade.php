@extends('layout')
@section('title', 'Revisión documental')
@section('content')
@if ($documento->invitacion_nombre)<p><a class="btn btn-outline-secondary" href="{{ route('documentos.invitacion', $documento) }}" target="_blank" rel="noopener">Ver invitación adjunta: {{ $documento->invitacion_nombre }} (sin transcripción)</a></p>@endif
<div class="d-flex flex-wrap align-items-center justify-content-end gap-3 mb-4">
    <div class="d-flex gap-2 flex-wrap">@if ($documento->ruta_pdf)<a href="{{ route('documentos.pdf', $documento) }}" target="_blank" rel="noopener" class="btn btn-outline-primary">Abrir PDF digitalizado</a>@endif<a href="{{ route('documentos.texto', $documento) }}" class="btn btn-outline-secondary">Ver texto completo</a></div>
</div>

<div class="row g-4 review-grid">
    <section class="col-12 col-xl-6" aria-label="Vista previa del documento">
        <div class="card border-0 shadow-sm overflow-hidden">
            <div class="p-3 border-bottom d-flex align-items-center justify-content-between gap-2 flex-wrap">
                <form id="preview-page-form" method="get" class="d-flex align-items-center gap-2">
        <label class="small" for="pagina">Ir a página</label><input type="number" id="pagina" name="pagina" min="1" max="{{ $documento->numero_paginas }}" value="{{ $numero }}" class="form-control form-control-sm page-input" required><button class="btn btn-sm btn-outline-secondary">Ir</button>
    </form>
                <div class="d-flex align-items-center gap-2"><button type="button" id="zoom-out" class="btn btn-sm btn-outline-secondary" aria-label="Reducir zoom" disabled>−</button><output id="zoom-label" class="small">100 %</output><button type="button" id="zoom-in" class="btn btn-sm btn-outline-secondary" aria-label="Aumentar zoom" disabled>+</button><button type="button" id="zoom-fit" class="btn btn-sm btn-outline-secondary" disabled>Ajustar</button></div>
            </div>
            <p id="preview-status" class="small text-secondary px-3 pt-3 mb-2" role="status">Cargando vista previa…</p>
            <div class="preview-scroll" id="preview-container" aria-label="Vista previa de la página {{ $numero }}">
                @if (! in_array($documento->tipo_archivo, ['pdf', 'zip'], true))<img id="original-image" src="{{ route('documentos.original', $documento) }}" alt="Original de {{ $documento->nombre_original }}" class="original-image">@else<div id="pdf-surface"></div>@endif
            </div>
        </div>
    </section>
    <section class="col-12 col-xl-6" aria-labelledby="extraction-heading">
        <div class="card border-0 shadow-sm p-4 mb-4">
            <div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3"><h2 class="h5 mb-0" id="extraction-heading">Texto extraído automáticamente</h2><span class="badge text-bg-light border">{{ $pagina->metodo_extraccion === 'digital' ? 'Texto digital' : 'OCR' }} · {{ number_format($pagina->duracion_ms / 1000, 2) }} s</span></div>
            @if (count($pagina->variantes_ocr ?? []) > 1)
                <label class="form-label small" for="variant">Resultado OCR</label><select id="variant" class="form-select form-select-sm mb-2">@foreach ($pagina->variantes_ocr as $index=>$variante)<option value="{{ $index }}">{{ $variante['modo'] === 'original' ? 'Sin filtros adicionales' : 'Con preprocesamiento' }} · {{ number_format($variante['duracion_ms']/1000, 2) }} s</option>@endforeach</select>
            @endif
            <p class="small text-secondary" id="variant-operations"></p>
            @if (($pagina->variantes_ocr[0]['alcance'] ?? '') === 'contenido_principal')
                <p class="small text-secondary">Se muestra el contenido principal del oficio. Revisa las zonas omitidas en el OCR completo; número, fecha, destinatario y asunto deben conservarse.</p>
            @endif
            <p class="small text-secondary">Se muestra el texto de todas las páginas, en orden. La referencia editable corresponde a la página {{ $numero }}.</p>
            <label class="visually-hidden" for="extracted-text">Texto completo del documento</label><textarea id="extracted-text" class="form-control extracted-text" rows="14" readonly>@foreach ($textos as $item){{ count($textos) > 1 ? 'Página '.$item['numero']."\n\n" : '' }}{{ $item['texto'] }}{{ !$loop->last ? "\n\n" : '' }}@endforeach</textarea>
            @if (! trim($pagina->texto_extraido))<p class="small text-warning-emphasis mt-2 mb-0">No se reconoció texto. Revisa visualmente el original.</p>@endif
            @if ($pagina->observaciones)<details class="mt-3 small"><summary>Observaciones del procesamiento</summary><pre class="text-block mt-2">{{ $pagina->observaciones }}</pre></details>@endif
            @foreach ($pagina->variantes_ocr ?? [] as $variante)
                @if (isset($variante['texto_lectura_inicial']))
                    <details class="mt-3 small"><summary>Lectura inicial antes de recuperar zonas sin transcribir</summary><pre class="text-block mt-2">{{ $variante['texto_lectura_inicial'] }}</pre></details>
                @endif
                @if (isset($variante['texto_pagina_completa']))
                    <details class="mt-3 small"><summary>OCR de página completa antes de excluir zonas auxiliares</summary>
                        @foreach ($variante['exclusiones'] ?? [] as $exclusion)<p class="mt-2 mb-1">{{ $exclusion }}</p>@endforeach
                        <pre class="text-block mt-2">{{ $variante['texto_pagina_completa'] }}</pre>
                    </details>
                @endif
            @endforeach
            @if ($pagina->texto_digital !== null)<details class="mt-3 small"><summary>Capa digital original antes del procesamiento</summary><pre class="text-block mt-2">{{ $pagina->texto_digital }}</pre></details>@endif
        </div>
        <div class="card border-0 shadow-sm p-4">
            <h2 class="h5">Transcripción de referencia</h2><p class="small text-secondary">Revisa el original e introduce una transcripción corregida. Se guarda por separado del texto automático.</p>
            <form method="post" action="{{ route('documentos.referencia', $documento) }}" id="reference-form">
                @csrf<input type="hidden" name="numero_pagina" value="{{ $numero }}"><input type="hidden" name="revision" id="reference-revision" value="{{ old('revision', $referencia?->id) }}">
                <button type="button" id="copy-draft" class="btn btn-sm btn-outline-secondary mb-3" disabled>Copiar página {{ $numero }} como borrador</button>
                <label class="visually-hidden" for="reference-text">Transcripción corregida de la página {{ $numero }}</label><textarea class="form-control mb-3" id="reference-text" name="texto_referencia" rows="12" maxlength="{{ config('documentos.max_reference_chars') }}" required>{{ old('texto_referencia', $referencia?->texto_referencia) }}</textarea>
                <label class="form-label small" for="reference-notes">Observaciones de revisión (opcional)</label><textarea class="form-control mb-3" id="reference-notes" name="observaciones" rows="2" maxlength="10000">{{ old('observaciones', $referencia?->observaciones) }}</textarea>
                <div class="d-flex flex-wrap gap-3 align-items-center"><button class="btn btn-primary" id="save-reference">Guardar transcripción de referencia</button><span class="small text-secondary" id="draft-state" role="status"></span></div>
                <p class="small mt-3 mb-0" id="save-message" role="status"></p>
            </form>
            <p class="small text-secondary mt-3 mb-0" id="reference-meta">@if ($referencia)Última versión: {{ $referencia->created_at->timezone(config('app.timezone'))->format('d/m/Y H:i') }} · {{ $referencia->usuario?->name ?? 'Operador no disponible' }}@endif</p>
            <a id="refresh-history" class="small mt-2" href="{{ route('documentos.revision',['documento'=>$documento,'pagina'=>$numero]) }}#reference-history" hidden>Actualizar historial</a>
            @if ($historial->count())<details class="mt-4" id="reference-history"><summary class="small">Historial de referencias · {{ $historial->total() }} {{ $historial->total() === 1 ? 'versión' : 'versiones' }}</summary>
                @foreach ($historial as $version)<article class="border-top pt-3 mt-3"><p class="small text-secondary">Versión {{ $version->id }} · {{ $version->created_at->timezone(config('app.timezone'))->format('d/m/Y H:i') }} · {{ $version->usuario?->name ?? 'Operador no disponible' }}</p><pre class="text-block reference-history">{{ $version->texto_referencia }}</pre>@if ($version->observaciones)<p class="small">{{ $version->observaciones }}</p>@endif</article>@endforeach
                {{ $historial->links('pagination::simple-bootstrap-5') }}
            </details>@endif
        </div>
        <div class="card border-0 shadow-sm p-4 mt-4" id="quality-panel">
            <h2 class="h5">Evaluación CER / WER</h2>
            <p class="small text-secondary">Compara con la versión guardada de la referencia. Menor error es mejor; las tasas pueden superar el 100 %. No representan la confianza de Tesseract.</p>
            <p class="small text-secondary">La referencia debe abarcar las mismas zonas que el texto comparado. CER/WER normaliza espacios y saltos de línea; el orden y la separación visual de las líneas deben revisarse por separado.</p>
            @if ($metricas)
                <p class="small">Referencia versión {{ $referencia->id }} · {{ $referencia->evaluada_at->timezone(config('app.timezone'))->format('d/m/Y H:i') }}</p>
                <div class="table-responsive"><table class="table table-sm" id="quality-results"><thead><tr><th>Resultado</th><th>CER</th><th>WER</th></tr></thead><tbody>
                @foreach ($metricas['variantes'] as $nombre=>$resultado)
                    <tr><th>{{ ['principal'=>'Texto principal', 'original'=>'OCR sin filtros', 'preprocesado'=>'OCR con preprocesamiento'][$nombre] ?? $nombre }}</th><td>{{ number_format($resultado['cer']['tasa']*100, 2) }} %</td><td>{{ number_format($resultado['wer']['tasa']*100, 2) }} %</td></tr>
                @endforeach
                </tbody></table></div>
                <details class="small"><summary>Detalles del cálculo</summary><p class="mt-2">{{ $metricas['motor'] }} {{ $metricas['version'] }} · {{ $metricas['politica'] }}. Unicode NFC y espacios consecutivos normalizados; se conservan mayúsculas, tildes y puntuación. CER incluye espacios y cuenta puntos de código Unicode.</p>
                @foreach ($metricas['variantes'] as $nombre=>$resultado)
                    @foreach (['cer','wer'] as $medida)<p>{{ $nombre }} · {{ strtoupper($medida) }}: ({{ $resultado[$medida]['sustituciones'] }} sustituciones + {{ $resultado[$medida]['eliminaciones'] }} eliminaciones + {{ $resultado[$medida]['inserciones'] }} inserciones) / {{ $resultado[$medida]['unidades_referencia'] }} unidades de referencia.</p>@endforeach
                @endforeach</details>
            @else<p class="small">No hay métricas para la versión actual.</p>@endif
            @if ($referencia?->usuario_id)
                <form method="post" action="{{ route('documentos.calidad', $documento) }}" class="mt-3" id="quality-form">
                    @csrf<input type="hidden" name="numero_pagina" value="{{ $numero }}"><input type="hidden" name="revision" value="{{ $referencia->id }}">
                    <div class="form-check mb-3"><input class="form-check-input" type="checkbox" name="confirmacion" value="1" id="quality-confirm" required><label class="form-check-label small" for="quality-confirm">He cotejado la referencia guardada con el original y corregido su transcripción.</label></div>
                    <button class="btn btn-outline-primary">Calcular CER y WER</button>
                    <p class="small text-secondary mt-2 mb-0">Si acabas de guardar cambios, recarga esta página antes de evaluar. Máximo 10 000 caracteres por texto; los originales permanecen completos.</p>
                </form>
            @else<p class="small">Guarda una referencia humana revisada para habilitar el cálculo.</p>@endif
        </div>
    </section>
</div>
@endsection
@push('scripts')
<script type="application/json" id="review-data">@json($reviewConfig)</script>
<script type="module" src="{{ asset('revision.js') }}"></script>
@endpush
