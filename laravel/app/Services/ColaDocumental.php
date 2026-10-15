<?php

namespace App\Services;

use App\Jobs\ProcesarDocumento;
use App\Models\DocumentoPrueba;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Str;

class ColaDocumental
{
    // Debe invocarse dentro de la transacción que crea o bloquea el documento.
    public function encolar(DocumentoPrueba $documento): void
    {
        $documento->update(['solicitud_uuid' => (string) Str::uuid(), 'estado_procesamiento' => 'pendiente',
            'encolado_at' => now(), 'procesamiento_inicio' => null, 'procesamiento_fin' => null, 'error_procesamiento' => null]);
        Bus::dispatch(new ProcesarDocumento($documento->id, $documento->solicitud_uuid));
    }

    public function reintentar(DocumentoPrueba $documento): bool
    {
        return DB::transaction(function () use ($documento) {
            $current = DocumentoPrueba::whereKey($documento->id)->lockForUpdate()->firstOrFail();
            if ($current->estado_procesamiento !== 'error' && ! ($current->estado_procesamiento === 'pendiente' && $current->solicitud_uuid === null)) {
                return false;
            }
            $this->encolar($current);

            return true;
        });
    }
}
