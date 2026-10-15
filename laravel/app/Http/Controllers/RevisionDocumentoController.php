<?php

namespace App\Http\Controllers;

use App\Models\DocumentoPrueba;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;

class RevisionDocumentoController extends Controller
{
    public function show(Request $request, DocumentoPrueba $documento)
    {
        if ($documento->estado_procesamiento !== 'completado') {
            return response()->view('documentos.sin-resultados', compact('documento'))->header('Cache-Control', 'private, no-store');
        }
        $numero = filter_var($request->query('pagina', 1), FILTER_VALIDATE_INT, ['options' => ['min_range' => 1, 'max_range' => 1000]]);
        abort_if($numero === false || $numero > $documento->numero_paginas, 404);
        $pagina = $documento->extracciones()->where('numero_pagina', $numero)->firstOrFail();
        $referencia = $documento->evaluaciones()->where('numero_pagina', $numero)->with('usuario')->latest('id')->first();
        $metricas = $referencia?->usuario_id && $referencia?->metricas && $referencia?->hash_extraccion === CalidadDocumentoController::huella($pagina) ? $referencia->metricas : null;
        $historial = $documento->evaluaciones()->where('numero_pagina', $numero)->with('usuario')->latest('id')->paginate(5, ['*'], 'historial')->withQueryString();
        $reviewConfig = ['originalUrl' => route('documentos.original', $documento), 'tipo' => $documento->tipo_archivo, 'pagina' => $numero, 'uuid' => $documento->uuid, 'pdfjsUrl' => asset('vendor/pdfjs/build/pdf.mjs'), 'workerUrl' => asset('vendor/pdfjs/build/pdf.worker.mjs'), 'fontUrl' => asset('vendor/pdfjs/standard_fonts').'/', 'cmapUrl' => asset('vendor/pdfjs/cmaps').'/', 'wasmUrl' => asset('vendor/pdfjs/wasm').'/', 'variantes' => $pagina->variantes_ocr ?? [], 'baseline' => ['texto' => $referencia?->texto_referencia ?? '', 'observaciones' => $referencia?->observaciones ?? '']];

        return response()->view('documentos.revision', compact('documento', 'pagina', 'numero', 'referencia', 'historial', 'reviewConfig', 'metricas'))
            ->header('Cache-Control', 'private, no-store')->header('X-Content-Type-Options', 'nosniff');
    }

    public function original(DocumentoPrueba $documento)
    {
        abort_unless($documento->estado_procesamiento === 'completado', 409, 'El documento aún no está disponible para revisión.');
        $relative = 'originales/'.$documento->uuid.'.'.$documento->tipo_archivo;
        abort_unless(Str::isUuid($documento->uuid) && in_array($documento->tipo_archivo, ['pdf', 'png', 'jpg'], true) && $documento->ruta_privada === $relative, 404);
        $disk = Storage::disk('documentos');
        $path = realpath($disk->path($relative));
        $root = realpath($disk->path(''));
        abort_unless($path && $root && str_starts_with($path, rtrim($root, DIRECTORY_SEPARATOR).DIRECTORY_SEPARATOR) && is_file($path), 404);
        abort_unless(filesize($path) === $documento->tamano_bytes && hash_equals($documento->hash_sha256, hash_file('sha256', $path)), 409, 'El original no coincide con el archivo registrado.');
        $mime = ['pdf' => 'application/pdf', 'png' => 'image/png', 'jpg' => 'image/jpeg'][$documento->tipo_archivo];

        return response()->file($path, ['Content-Type' => $mime, 'Cache-Control' => 'private, no-store',
            'X-Content-Type-Options' => 'nosniff', 'Content-Security-Policy' => "sandbox; default-src 'none'", 'X-Frame-Options' => 'SAMEORIGIN']);
    }

    public function texto(DocumentoPrueba $documento)
    {
        abort_unless($documento->estado_procesamiento === 'completado', 409, 'La extracción todavía no está completada.');
        $paginas = $documento->extracciones()->orderBy('numero_pagina')->get();

        return response()->view('documentos.texto', compact('documento', 'paginas'))->header('Cache-Control', 'private, no-store');
    }

    public function pdf(DocumentoPrueba $documento)
    {
        abort_unless($documento->estado_procesamiento === 'completado' && $documento->ruta_pdf, 404);
        $relative = $documento->ruta_pdf;
        $filename = basename($relative, '.pdf');
        abort_unless(Str::isUuid($documento->uuid) && Str::isUuid($filename)
            && $relative === 'normalizados/'.$documento->uuid.'/'.$filename.'.pdf', 404);
        $disk = Storage::disk('documentos');
        $path = realpath($disk->path($relative));
        $root = realpath($disk->path(''));
        abort_unless($path && $root && str_starts_with($path, rtrim($root, DIRECTORY_SEPARATOR).DIRECTORY_SEPARATOR) && is_file($path), 404);
        abort_unless(filesize($path) === (int) $documento->tamano_pdf && hash_equals($documento->hash_pdf ?? '', hash_file('sha256', $path)), 409, 'El PDF no coincide con el resultado registrado.');

        return response()->file($path, ['Content-Type' => 'application/pdf', 'Cache-Control' => 'private, no-store',
            'Content-Disposition' => 'inline; filename="documento-'.$documento->uuid.'.pdf"',
            'X-Content-Type-Options' => 'nosniff', 'Content-Security-Policy' => "sandbox; default-src 'none'", 'X-Frame-Options' => 'SAMEORIGIN']);
    }

    public function guardar(Request $request, DocumentoPrueba $documento)
    {
        $data = $request->validate([
            'numero_pagina' => 'required|integer|min:1|max:1000',
            'texto_referencia' => 'required|string|max:'.config('documentos.max_reference_chars'),
            'observaciones' => 'nullable|string|max:10000', 'revision' => 'present|nullable|integer|min:1',
        ], [
            'texto_referencia.required' => 'Introduce una transcripción de referencia no vacía.',
            'texto_referencia.max' => 'La transcripción supera el límite de caracteres permitido.',
            'observaciones.max' => 'Las observaciones superan el máximo de 10 000 caracteres.',
            'revision.present' => 'Falta la versión de referencia. Recarga la página.',
        ]);

        return DB::transaction(function () use ($request, $documento, $data) {
            $current = DocumentoPrueba::whereKey($documento->id)->lockForUpdate()->firstOrFail();
            if ($current->estado_procesamiento !== 'completado') {
                return $this->conflicto($request, 'La extracción debe estar completada antes de guardar una referencia.');
            }
            abort_unless($current->extracciones()->where('numero_pagina', $data['numero_pagina'])->exists(), 404);
            $latest = $current->evaluaciones()->where('numero_pagina', $data['numero_pagina'])->latest('id')->first();
            $revision = isset($data['revision']) ? (int) $data['revision'] : null;
            if ($revision !== $latest?->id) {
                return $this->conflicto($request, 'Otra persona guardó una versión de esta página. Conserva tu borrador y recarga para comparar antes de guardar.');
            }
            $notes = $data['observaciones'] ?? null;
            if ($latest && $latest->texto_referencia === $data['texto_referencia'] && $latest->observaciones === $notes) {
                $saved = $latest;
            } else {
                $saved = $current->evaluaciones()->create(['numero_pagina' => $data['numero_pagina'],
                    'texto_referencia' => $data['texto_referencia'], 'observaciones' => $notes, 'usuario_id' => $request->user()->id]);
            }
            if ($request->expectsJson()) {
                return response()->json(['message' => 'Transcripción de referencia guardada.', 'revision' => $saved->id, 'guardado_en' => $saved->created_at->timezone(config('app.timezone'))->format('d/m/Y H:i'), 'autor' => $saved->usuario?->name ?? 'Operador no disponible'])->header('Cache-Control', 'no-store');
            }

            return to_route('documentos.revision', ['documento' => $documento, 'pagina' => $data['numero_pagina']])->with('status', 'Transcripción de referencia guardada.');
        });
    }

    private function conflicto(Request $request, string $message)
    {
        return $request->expectsJson() ? response()->json(['message' => $message], 409)
            : back()->withInput()->withErrors(['texto_referencia' => $message]);
    }
}
