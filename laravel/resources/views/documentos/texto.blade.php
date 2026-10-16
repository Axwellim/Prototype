@extends('layout')
@section('title', 'Texto completo')
@section('content')
<p class="small text-secondary">Se reúnen las transcripciones principales de todas las páginas. Si se omitieron zonas auxiliares, el OCR de página completa se conserva en la revisión de cada página.</p>
<div class="d-flex flex-wrap justify-content-between align-items-center gap-3 my-4"><div><span class="eyebrow">TEXTO COMPLETO</span><h1 class="h3 mt-2">{{ $documento->nombre_original }}</h1><p class="text-secondary small">Extracción automática · {{ $documento->numero_paginas }} páginas. Las referencias humanas se consultan en la revisión de cada página.</p></div></div>
@foreach ($paginas as $pagina)<section class="card border-0 shadow-sm p-4 mb-4"><div class="d-flex flex-wrap justify-content-between align-items-center gap-2 mb-3"><h2 class="h5 mb-0">Página {{ $pagina->numero_pagina }}</h2><a class="btn btn-sm btn-outline-secondary" href="{{ route('documentos.revision',['documento'=>$documento,'pagina'=>$pagina->numero_pagina]) }}">Revisar esta página</a></div><pre class="text-block">{{ $pagina->texto_extraido }}</pre>@if (! trim($pagina->texto_extraido))<p class="text-secondary small">Sin texto reconocido.</p>@endif</section>@endforeach
@endsection
