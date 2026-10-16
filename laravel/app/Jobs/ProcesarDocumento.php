<?php

namespace App\Jobs;

use App\Exceptions\ProcesamientoFallido;
use App\Models\DocumentoPrueba;
use App\Services\ProcesadorDocumental;
use Illuminate\Contracts\Queue\ShouldQueue;
use Illuminate\Foundation\Queue\Queueable;
use Illuminate\Support\Facades\Cache;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Log;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Throwable;

class ProcesarDocumento implements ShouldQueue
{
    use Queueable;

    public int $tries = 50;

    public int $maxExceptions = 1;

    public int $timeout;

    public bool $failOnTimeout = true;

    public function __construct(public int $documentoId, public string $solicitudUuid)
    {
        $this->timeout = (int) config('documentos.job_timeout');
        $this->onConnection('documentos')->onQueue((string) config('queue.connections.documentos.queue', 'ocr'))->beforeCommit();
    }

    public function handle(ProcesadorDocumental $processor): void
    {
        $documento = DocumentoPrueba::find($this->documentoId);
        if (! $documento || $documento->solicitud_uuid !== $this->solicitudUuid
            || in_array($documento->estado_procesamiento, ['completado', 'error'], true)) {
            return;
        }
        $pgsql = DB::getDriverName() === 'pgsql';
        $lock = $pgsql ? null : Cache::store('database')->lock('documentos:ocr', $this->timeout + 60);
        $locked = $pgsql ? (bool) DB::selectOne('SELECT pg_try_advisory_lock(758199) AS acquired')->acquired : $lock->get();
        if (! $locked) {
            $this->release(15);

            return;
        }
        $pdfPath = null;
        $invitationPath = null;
        $published = false;
        try {
            $documento->refresh();
            if ($documento->solicitud_uuid !== $this->solicitudUuid || in_array($documento->estado_procesamiento, ['completado', 'error'], true)) {
                return;
            }
            if ($documento->estado_procesamiento === 'procesando') {
                if ($documento->procesamiento_inicio?->gt(now()->subSeconds($this->timeout + 30))) {
                    $this->release(15);

                    return;
                }
                throw new ProcesamientoFallido('El trabajador anterior se interrumpió. Puedes reintentar el documento.');
            }
            $changed = $this->actual()->where('estado_procesamiento', 'pendiente')->update([
                'estado_procesamiento' => 'procesando', 'procesamiento_inicio' => now(), 'procesamiento_fin' => null,
                'intentos' => DB::raw('intentos + 1'), 'error_procesamiento' => null,
            ]);
            if (! $changed) {
                return;
            }
            $result = $processor->procesar($documento->fresh());
            if (! isset($result['_pdf']) || ! is_string($result['_pdf'])) {
                throw new ProcesamientoFallido('Falta el PDF del documento digitalizado.');
            }
            $pdfPath = 'normalizados/'.$documento->uuid.'/'.Str::uuid().'.pdf';
            if (! Storage::disk('documentos')->put($pdfPath, $result['_pdf'])) {
                throw new ProcesamientoFallido('No se pudo guardar el PDF digitalizado.');
            }
            if (isset($result['_invitacion'])) {
                $invitationPath = 'invitaciones/'.$documento->uuid.'/'.Str::uuid().'.pdf';
                if (! Storage::disk('documentos')->put($invitationPath, $result['_invitacion'])) {
                    throw new ProcesamientoFallido('No se pudo guardar la invitación.');
                }
            }
            $published = DB::transaction(function () use ($result, $pdfPath, $invitationPath) {
                $current = $this->actual()->lockForUpdate()->first();
                if (! $current || $current->estado_procesamiento !== 'procesando') {
                    return false;
                }
                if (isset($result['componentes_paginas'])) {
                    $components = $current->componentes;
                    $index = 0;
                    foreach ($components as &$component) {
                        if ($component['tipo'] === 'documento') {
                            $component['paginas'] = $result['componentes_paginas'][$index++];
                        }
                    }
                    unset($component);
                    $current->componentes = $components;
                }
                foreach ($result['paginas'] as $page) {
                    if ($page['metodo'] === 'sin_transcripcion') {
                        continue;
                    }
                    $current->extracciones()->updateOrCreate(['numero_pagina' => $page['numero']], [
                        'metodo_extraccion' => $page['metodo'], 'texto_extraido' => $page['texto'],
                        'duracion_ms' => $page['duracion_ms'], 'observaciones' => implode("\n", $page['observaciones']),
                        'texto_digital' => $page['texto_digital'] ?? null, 'variantes_ocr' => $page['variantes_ocr'],
                    ]);
                }
                $current->update(['estado_procesamiento' => 'completado', 'numero_paginas' => $result['numero_paginas'],
                    'ruta_invitacion' => $invitationPath,
                    'hash_invitacion' => $invitationPath ? hash('sha256', $result['_invitacion']) : null,
                    'tamano_invitacion' => $invitationPath ? strlen($result['_invitacion']) : null,
                    'paginas_invitacion' => $result['invitacion_paginas'] ?? null,
                    'ruta_pdf' => $pdfPath, 'hash_pdf' => hash('sha256', $result['_pdf']), 'tamano_pdf' => strlen($result['_pdf']),
                    'politica_digitalizacion' => $current->tipo_registro === 'invitacion' ? 'sin-transcripcion-v1' : ($current->modo_ocr === 'automatico' ? 'automatico-cierre-v4' : 'manual-v1'),
                    'duracion_total_ms' => $result['duracion_total_ms'], 'metodos_extraccion' => implode(' + ', array_unique(array_column($result['paginas'], 'metodo'))),
                    'procesamiento_fin' => now(), 'error_procesamiento' => null]);

                return true;
            });
            Log::info('Documento procesado.', ['documento_id' => $this->documentoId, 'solicitud' => $this->solicitudUuid]);
        } catch (Throwable $error) {
            $message = $error instanceof ProcesamientoFallido ? $error->getMessage() : 'No se pudo guardar el resultado del procesamiento. Revisa el servicio y reintenta.';
            $this->actual()->whereIn('estado_procesamiento', ['pendiente', 'procesando'])->update([
                'estado_procesamiento' => 'error', 'error_procesamiento' => $message, 'procesamiento_fin' => now(),
            ]);
            Log::error('Falló el procesamiento documental.', ['documento_id' => $this->documentoId, 'solicitud' => $this->solicitudUuid, 'motivo' => $message, 'tipo' => get_class($error)]);
            throw new ProcesamientoFallido($message);
        } finally {
            if ($invitationPath && ! $published) {
                try {
                    Storage::disk('documentos')->delete($invitationPath);
                } catch (Throwable $cleanupError) {
                    report($cleanupError);
                }
            }
            if ($pdfPath && ! $published) {
                try {
                    Storage::disk('documentos')->delete($pdfPath);
                } catch (Throwable $cleanupError) {
                    report($cleanupError);
                }
            }
            if ($pgsql) {
                DB::select('SELECT pg_advisory_unlock(758199)');
            } else {
                $lock->release();
            }
        }
    }

    private function actual()
    {
        return DocumentoPrueba::whereKey($this->documentoId)->where('solicitud_uuid', $this->solicitudUuid);
    }

    public function failed(?Throwable $error): void
    {
        $this->actual()->whereIn('estado_procesamiento', ['pendiente', 'procesando'])->update([
            'estado_procesamiento' => 'error', 'error_procesamiento' => 'El trabajador se interrumpió o agotó sus intentos. Puedes reintentar.', 'procesamiento_fin' => now(),
        ]);
    }
}
