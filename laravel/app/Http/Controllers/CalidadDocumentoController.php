<?php

namespace App\Http\Controllers;

use App\Models\DocumentoPrueba;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Validator;
use Throwable;

class CalidadDocumentoController extends Controller
{
    public static function variantes($pagina): array
    {
        $variantes = ['principal' => $pagina->texto_extraido];
        foreach ($pagina->variantes_ocr ?? [] as $variante) {
            $variantes[$variante['modo']] = $variante['texto'];
        }

        return $variantes;
    }

    public static function huella($pagina): string
    {
        return hash('sha256', json_encode(self::variantes($pagina), JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR));
    }

    public function store(Request $request, DocumentoPrueba $documento)
    {
        $data = $request->validate(['numero_pagina' => 'required|integer|min:1|max:1000',
            'revision' => 'required|integer|min:1', 'confirmacion' => 'accepted']);
        abort_unless($documento->estado_procesamiento === 'completado', 409, 'La extracción debe estar completada.');
        $pagina = $documento->extracciones()->where('numero_pagina', $data['numero_pagina'])->firstOrFail();
        $referencia = $documento->evaluaciones()->where('numero_pagina', $data['numero_pagina'])->latest('id')->first();
        abort_unless($referencia && $referencia->id === (int) $data['revision'], 409, 'La referencia cambió. Recarga y revisa la última versión.');
        abort_unless($referencia->usuario_id && trim($referencia->texto_referencia ?? '') !== '', 422, 'Guarda primero una referencia humana identificada.');
        $variantes = self::variantes($pagina);
        foreach ([$referencia->texto_referencia, ...array_values($variantes)] as $texto) {
            abort_if(mb_strlen($texto) > 10000, 422, 'La evaluación admite hasta 10 000 caracteres por texto; no se trunca el contenido.');
        }
        $hash = self::huella($pagina);
        $url = (string) config('documentos.processor_url');
        $parts = parse_url($url);
        abort_unless($parts && ($parts['scheme'] ?? '') === 'http' && ($parts['host'] ?? '') === '127.0.0.1'
            && ! isset($parts['user']) && ! isset($parts['pass'])
            && ! isset($parts['query']) && ! isset($parts['fragment']) && in_array($parts['path'] ?? '', ['', '/'], true)
            && strlen((string) config('documentos.processor_token')) >= 32, 503, 'Configura el servicio local de evaluación.');
        try {
            $response = Http::withHeaders(['X-Processor-Token' => config('documentos.processor_token')])->acceptJson()
                ->connectTimeout(3)->timeout(20)->withOptions(['proxy' => '', 'allow_redirects' => false])
                ->post(rtrim($url, '/').'/evaluar', ['referencia' => $referencia->texto_referencia, 'variantes' => $variantes]);
        } catch (Throwable) {
            abort(503, 'No se pudo contactar con el evaluador local. Conserva la referencia e intenta de nuevo.');
        }
        abort_unless($response->successful(), 503, 'El evaluador está ocupado o no pudo completar el cálculo. Intenta de nuevo.');
        $result = $response->json();
        $validator = Validator::make(is_array($result) ? $result : [], [
            'motor' => 'required|in:jiwer', 'version' => 'required|string|max:40', 'politica' => 'required|in:nfc-espacios-v1',
            'variantes' => 'required|array', 'variantes.*.cer' => 'required|array', 'variantes.*.wer' => 'required|array',
            'variantes.*.*.tasa' => 'required|numeric|min:0',
            'variantes.*.*.sustituciones' => 'required|integer|min:0', 'variantes.*.*.eliminaciones' => 'required|integer|min:0',
            'variantes.*.*.inserciones' => 'required|integer|min:0', 'variantes.*.*.unidades_referencia' => 'required|integer|min:1',
        ]);
        abort_if($validator->fails() || array_keys($result['variantes'] ?? []) !== array_keys($variantes), 502, 'El evaluador devolvió una respuesta inválida.');
        DB::transaction(function () use ($documento, $pagina, $referencia, $hash, $result) {
            $current = DocumentoPrueba::whereKey($documento->id)->lockForUpdate()->firstOrFail();
            $latest = $current->evaluaciones()->where('numero_pagina', $pagina->numero_pagina)->latest('id')->first();
            abort_unless($latest?->id === $referencia->id && $current->estado_procesamiento === 'completado'
                && hash_equals($hash, self::huella($pagina->fresh())), 409, 'La referencia o extracción cambió durante el cálculo. Vuelve a evaluar.');
            $latest->metricas = $result;
            $latest->hash_extraccion = $hash;
            $latest->evaluada_at = now();
            $latest->save();
        });

        return to_route('documentos.revision', ['documento' => $documento, 'pagina' => $pagina->numero_pagina])->with('status', 'CER y WER calculados con la referencia guardada.');
    }
}
