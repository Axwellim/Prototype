@extends('layout')
@section('title', 'Revisión documental')
@section('content')
<a href="{{ route('documentos.index') }}" class="text-decoration-none">← Documentos</a>
<div class="card border-0 shadow-sm p-4 mt-3">
    <h1 class="h3">{{ $documento->nombre_original }}</h1>
    <p>Estado: <strong>{{ ucfirst($documento->estado_procesamiento) }}</strong></p>
    <p>La revisión estará disponible cuando termine la extracción.</p>
    @if ($documento->error_procesamiento)<p class="text-danger">{{ $documento->error_procesamiento }}</p>@endif
    <a href="{{ route('documentos.index') }}" class="btn btn-primary align-self-start">Volver al listado y consultar el estado</a>
</div>
@endsection
