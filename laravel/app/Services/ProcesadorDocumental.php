<?php

namespace App\Services;

use App\Exceptions\ProcesamientoFallido;
use App\Models\DocumentoPrueba;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Facades\Validator;
use Throwable;

class ProcesadorDocumental
{
    public function procesar(DocumentoPrueba $documento): array
    {
        $url = (string) config('documentos.processor_url');
        $parts = parse_url($url);
        if (! $parts || ($parts['scheme'] ?? '') !== 'http' || ($parts['host'] ?? '') !== '127.0.0.1'
            || isset($parts['user']) || isset($parts['pass']) || isset($parts['query']) || isset($parts['fragment'])
            || ! in_array($parts['path'] ?? '', ['', '/'], true)) {
            throw new ProcesamientoFallido('La dirección del procesador debe ser HTTP local en 127.0.0.1.');
        }
        $token = (string) config('documentos.processor_token');
        if (strlen($token) < 32) {
            throw new ProcesamientoFallido('Falta configurar la clave local del procesador.');
        }
        $relative = 'originales/'.$documento->uuid.'.'.$documento->tipo_archivo;
        if ($documento->ruta_privada !== $relative || ! in_array($documento->tipo_archivo, ['pdf', 'jpg', 'png'], true)) {
            throw new ProcesamientoFallido('La ubicación privada del documento no es válida.');
        }
        $disk = Storage::disk('documentos');
        $path = realpath($disk->path($relative));
        $root = realpath($disk->path(''));
        if (! $path || ! $root || ! str_starts_with($path, rtrim($root, DIRECTORY_SEPARATOR).DIRECTORY_SEPARATOR)
            || ! is_file($path) || filesize($path) !== $documento->tamano_bytes
            || ! hash_equals($documento->hash_sha256, hash_file('sha256', $path))) {
            throw new ProcesamientoFallido('El archivo privado falta o no coincide con su hash registrado.');
        }
        $mime = ['pdf' => 'application/pdf', 'jpg' => 'image/jpeg', 'png' => 'image/png'][$documento->tipo_archivo];
        $stream = fopen($path, 'rb');
        try {
            $response = Http::withHeaders(['X-Processor-Token' => $token, 'Accept' => 'application/zip'])
                ->connectTimeout(5)->timeout(config('documentos.http_timeout'))
                ->withOptions(['proxy' => '', 'allow_redirects' => false, 'progress' => function ($total, $downloaded) {
                    if ($downloaded > config('documentos.max_response_bytes')) {
                        throw new ProcesamientoFallido('La respuesta del procesador supera el límite permitido.');
                    }
                }])->withBody($stream, $mime)->post(rtrim($url, '/').'/procesar?modo='.rawurlencode($documento->modo_ocr).'&normalizar=true');
        } catch (ProcesamientoFallido $error) {
            throw $error;
        } catch (Throwable) {
            throw new ProcesamientoFallido('No se pudo contactar con el procesador local o se agotó el tiempo de espera.');
        } finally {
            if (is_resource($stream)) {
                fclose($stream);
            }
        }
        if (! $response->successful()) {
            $code = $response->json('detail.codigo');
            $messages = [
                'pdf_cifrado' => 'El PDF está protegido con contraseña.',
                'pdf_corrupto' => 'El PDF está dañado y requiere reparación.',
                'pdf_invalido' => 'No se pudo leer el PDF.',
                'paginas_excedidas' => 'El documento supera el máximo de páginas permitido.',
                'pixeles_excedidos' => 'La imagen o página supera el límite de píxeles.',
                'imagen_invalida' => 'La imagen está dañada o no coincide con su formato.',
                'idioma_no_disponible' => 'Falta instalar el idioma requerido de Tesseract.',
                'tesseract_no_disponible' => 'Tesseract no está disponible en el servidor.',
            ];
            throw new ProcesamientoFallido($messages[$code] ?? match ($response->status()) {
                401,403 => 'La clave del procesador no es válida o el acceso no es local.',
                503 => 'El procesador está ocupado o no está disponible. Reintenta más tarde.',
                504,408 => 'El procesamiento superó el tiempo permitido.',
                default => 'El procesador rechazó el documento o devolvió un error.',
            });
        }
        if (strlen($response->body()) > config('documentos.max_response_bytes')) {
            throw new ProcesamientoFallido('La respuesta del procesador supera el límite permitido.');
        }

        $package = app(PaqueteDigitalizado::class)->leer($response->body());
        $result = $this->validar($package['resultado']);
        $result['_pdf'] = $package['pdf'];

        return $result;
    }

    public function validar(mixed $data): array
    {
        if (! is_array($data)) {
            throw new ProcesamientoFallido('El procesador no devolvió un JSON válido.');
        }
        $validator = Validator::make($data, [
            'estado' => 'required|in:completado', 'numero_paginas' => 'required|integer|min:1|max:1000',
            'duracion_total_ms' => 'required|integer|min:0', 'texto_completo' => 'present|string',
            'paginas' => 'required|array|min:1|max:1000', 'paginas.*.numero' => 'required|integer|min:1',
            'paginas.*.metodo' => 'required|in:digital,ocr', 'paginas.*.texto' => 'present|string',
            'paginas.*.duracion_ms' => 'required|integer|min:0', 'paginas.*.observaciones' => 'present|array',
            'paginas.*.observaciones.*' => 'string', 'paginas.*.texto_digital' => 'nullable|string',
            'paginas.*.variantes_ocr' => 'present|array|max:2',
            'paginas.*.variantes_ocr.*.modo' => 'required|in:original,preprocesado',
            'paginas.*.variantes_ocr.*.texto' => 'present|string',
            'paginas.*.variantes_ocr.*.duracion_ms' => 'required|integer|min:0',
            'paginas.*.variantes_ocr.*.operaciones' => 'present|array',
            'paginas.*.variantes_ocr.*.operaciones.*' => 'string',
            'paginas.*.variantes_ocr.*.texto_pagina_completa' => 'nullable|string',
            'paginas.*.variantes_ocr.*.texto_lectura_inicial' => 'nullable|string',
            'paginas.*.variantes_ocr.*.alcance' => 'sometimes|in:pagina_completa,contenido_principal',
            'paginas.*.variantes_ocr.*.exclusiones' => 'sometimes|array|max:5',
            'paginas.*.variantes_ocr.*.exclusiones.*' => 'string',
        ]);
        if ($validator->fails() || count($data['paginas'] ?? []) !== ($data['numero_paginas'] ?? null)) {
            throw new ProcesamientoFallido('La respuesta del procesador tiene una estructura inválida.');
        }
        foreach ($data['paginas'] as $index => $page) {
            if ($page['numero'] !== $index + 1 || ($page['metodo'] === 'ocr'
                ? empty($page['variantes_ocr']) || $page['texto'] !== $page['variantes_ocr'][0]['texto']
                : ! empty($page['variantes_ocr']))) {
                throw new ProcesamientoFallido('La respuesta del procesador contiene páginas o variantes inconsistentes.');
            }
        }
        if ($data['texto_completo'] !== implode("\f", array_column($data['paginas'], 'texto'))) {
            throw new ProcesamientoFallido('El texto completo no coincide con las páginas recibidas.');
        }

        return $data;
    }
}
