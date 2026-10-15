@extends('layout')
@section('title', 'Acceso al módulo')
@section('content')
<div class="mx-auto card border-0 shadow-sm p-4 login-card">
    <span class="eyebrow">ACCESO INSTITUCIONAL</span>
    <h1 class="h3 mt-2">Digitalización documental</h1>
    <p class="text-secondary">Ingresa con tu cuenta de operador para cargar documentos de prueba.</p>
    <form method="post" action="{{ route('login.store') }}">
        @csrf
        <label class="form-label" for="email">Correo electrónico</label>
        <input class="form-control mb-3" id="email" type="email" name="email" value="{{ old('email') }}" required autocomplete="username" autofocus>
        <label class="form-label" for="password">Contraseña</label>
        <input class="form-control mb-4" id="password" type="password" name="password" required autocomplete="current-password">
        <button class="btn btn-primary w-100">Ingresar</button>
    </form>
    <p class="small text-secondary mt-3 mb-0">Las cuentas se habilitan desde la administración local.</p>
</div>
@endsection
