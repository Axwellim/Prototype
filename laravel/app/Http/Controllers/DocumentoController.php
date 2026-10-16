<?php

namespace App\Http\Controllers;

use App\Http\Requests\SubirDocumentoRequest;
use App\Models\DocumentoPrueba;
use App\Services\CargaCompuesta;
use App\Services\ColaDocumental;
use Illuminate\Http\Request;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Throwable;

class DocumentoController extends Controller
{
    public function index()
    {
        return view('documentos.index', ['documentos' => DocumentoPrueba::latest('fecha_carga')->paginate(15)]);
    }

    public function store(SubirDocumentoRequest $request)
    {
        $uuid = (string) Str::uuid();
        $disk = Storage::disk('documentos');
        $path = null;
        try {
            $attributes = app(CargaCompuesta::class)->guardar($request, $uuid);
            $path = $attributes['ruta_privada'];
            $documento = DB::transaction(function () use ($uuid, $attributes) {
                $documento = DocumentoPrueba::create(array_merge($attributes, [
                    'uuid' => $uuid, 'estado_procesamiento' => 'pendiente',
                    'fecha_carga' => now(), 'modo_ocr' => 'automatico',
                ]));
                app(ColaDocumental::class)->encolar($documento);

                return $documento;
            });
        } catch (Throwable $error) {
            // Solo se limpia el archivo nuevo si falló su registro; nunca archivos existentes.
            try {
                if ($path) {
                    $disk->delete($path);
                }
            } catch (Throwable $cleanupError) {
                report($cleanupError);
            }
            Log::error('No se pudo almacenar un documento.', ['uuid' => $uuid, 'exception' => $error]);

            return $request->expectsJson()
                ? response()->json(['message' => 'No se pudo guardar el documento. Intenta nuevamente.'], 503)
                : back()->withErrors(['archivo' => 'No se pudo guardar el documento. Intenta nuevamente.']);
        }
        if ($request->expectsJson()) {
            return response()->json(['message' => 'Documento guardado y encolado para extracción.', 'uuid' => $documento->uuid, 'estado' => 'pendiente'], 201);
        }

        return to_route('documentos.index')->with('status', 'Documento guardado. La extracción se realizará en segundo plano.');
    }

    public function reintentar(DocumentoPrueba $documento, ColaDocumental $cola)
    {
        if (! $cola->reintentar($documento)) {
            return back()->withErrors(['archivo' => 'Este documento ya está en cola, se está procesando o está completado.']);
        }

        return to_route('documentos.index')->with('status', 'Documento encolado. El trabajador lo procesará en segundo plano.');
    }

    public function estados(Request $request)
    {
        $data = $request->validate(['uuids' => 'required|array|min:1|max:15', 'uuids.*' => 'required|uuid']);
        $items = DocumentoPrueba::whereIn('uuid', $data['uuids'])->get()->map(fn ($documento) => $this->estadoPublico($documento));

        return response()->json(['documentos' => $items])->header('Cache-Control', 'no-store');
    }

    public function destroy(Request $request, DocumentoPrueba $documento)
    {
        $request->validate(['confirmacion' => 'accepted']);
        DB::transaction(function () use ($documento) {
            $current = DocumentoPrueba::whereKey($documento->id)->lockForUpdate()->firstOrFail();
            abort_if($current->estado_procesamiento === 'procesando', 409, 'Espera a que termine el procesamiento antes de eliminar el documento.');
            $current->delete();
        });
        Log::info('Documento retirado del historial.', ['documento_id' => $documento->id, 'usuario_id' => $request->user()->id]);

        return to_route('documentos.index')->with('status', 'Documento eliminado del historial. Sus archivos y transcripciones se conservan.');
    }

    private function estadoPublico(DocumentoPrueba $documento): array
    {
        return ['sin_transcripcion' => $documento->tipo_registro === 'invitacion', 'uuid' => $documento->uuid, 'estado' => $documento->estado_procesamiento,
            'pdf_disponible' => $documento->estado_procesamiento === 'completado' && $documento->ruta_pdf !== null,
            'numero_paginas' => $documento->numero_paginas, 'metodos' => $documento->metodos_extraccion,
            'duracion_ms' => $documento->duracion_total_ms, 'error' => $documento->error_procesamiento,
            'puede_encolar' => $documento->estado_procesamiento === 'error' || ($documento->estado_procesamiento === 'pendiente' && $documento->solicitud_uuid === null)];
    }
}
