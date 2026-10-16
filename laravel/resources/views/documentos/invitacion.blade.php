@extends('layout')
@section('content')
<h1 class="h3 mt-3">{{ $documento->nombre_original }}</h1>
<p class="alert alert-info">Invitación archivada sin transcripción. El archivo se conserva para su consulta.</p>
<a class="btn btn-primary mb-3" href="{{ route('documentos.pdf', $documento) }}" target="_blank" rel="noopener">Abrir PDF de la invitación</a>
<p>{{ $documento->numero_paginas }} página(s). No se aplicó OCR ni se generaron métricas de transcripción.</p>
@endsection
