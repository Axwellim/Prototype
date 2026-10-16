@php
    $enListado = request()->routeIs('documentos.index');
    $enTexto = request()->routeIs('documentos.texto');
    $esInvitacion = isset($documento) && $documento->tipo_registro === 'invitacion';
@endphp
<nav id="review-start" aria-label="Ruta de navegación" class="route-navigation mb-3">
    <ol class="list-unstyled d-flex flex-wrap align-items-center gap-2 mb-0">
        <li>
            @if ($enListado)<span class="route-current" aria-current="page">Documentos</span>
            @else<a class="route-link" href="{{ route('documentos.index') }}">Documentos</a>@endif
        </li>
        @if (! $enListado && isset($documento))
            <li aria-hidden="true" class="route-separator">›</li>
            <li>
                @if ($enTexto)<a class="route-link" href="{{ route('documentos.revision', $documento) }}">Revisión documental</a>
                @else<span class="route-current" aria-current="page">{{ $esInvitacion ? 'Invitación' : 'Revisión documental' }}</span>@endif
            </li>
            @if ($enTexto)
                <li aria-hidden="true" class="route-separator">›</li>
                <li><span class="route-current" aria-current="page">Texto completo</span></li>
            @endif
        @endif
    </ol>
</nav>
