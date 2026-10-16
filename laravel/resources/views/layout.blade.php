<!doctype html>
<html lang="es">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="csrf-token" content="{{ csrf_token() }}">
    <title>@yield('title', 'Digitalización documental') · GAD Imantag</title>
    <link rel="stylesheet" href="{{ asset('vendor/bootstrap/bootstrap.min.css') }}">
    <link rel="stylesheet" href="{{ asset('documentos.css') }}">
</head>
<body>
<header class="border-bottom bg-white"><nav class="container py-3 d-flex align-items-center justify-content-between gap-3" aria-label="Principal">
    <a class="brand text-decoration-none" href="{{ route('documentos.index') }}"><span class="brand-mark">I</span><span>GAD IMANTAG<small class="d-block text-secondary fw-normal">Gestión documental · Fase de prueba</small></span></a>
    @auth <form method="post" action="{{ route('logout') }}">@csrf <button class="btn btn-outline-secondary btn-sm">Cerrar sesión</button></form> @endauth
</nav></header>
<main class="container py-5">
    @auth
        @if (request()->routeIs('documentos.*')) @include('documentos.navegacion') @endif
    @endauth
    @if (session('status')) <div class="alert alert-success" role="status">{{ session('status') }}</div> @endif
    @if ($errors->any()) <div class="alert alert-danger" role="alert"><ul class="mb-0">@foreach ($errors->all() as $error)<li>{{ $error }}</li>@endforeach</ul></div> @endif
    @yield('content')
</main>
<footer class="container pb-4 text-secondary small">Gobierno Autónomo Descentralizado Parroquial Rural de Imantag</footer>
@stack('scripts')
</body>
</html>
