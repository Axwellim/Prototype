<?php

namespace App\Services;

use App\Exceptions\ProcesamientoFallido;
use ZipArchive;

class PaqueteDigitalizado
{
    public function leer(string $bytes): array
    {
        $temporary = tmpfile();
        if (! $temporary) {
            throw new ProcesamientoFallido('No se pudo preparar el resultado temporal.');
        }
        $zip = new ZipArchive;
        $opened = false;
        try {
            if (fwrite($temporary, $bytes) !== strlen($bytes)) {
                throw new ProcesamientoFallido('No se pudo guardar el paquete temporal completo.');
            }
            $opened = $zip->open(stream_get_meta_data($temporary)['uri']) === true;
            if (! $opened || $zip->numFiles !== 2) {
                throw new ProcesamientoFallido('El procesador no devolvió PDF y transcripción.');
            }
            foreach (['resultado.json' => 16777216, 'documento.pdf' => config('documentos.max_pdf_bytes')] as $name => $limit) {
                $stat = $zip->statName($name);
                if (! $stat || $stat['size'] < 1 || $stat['size'] > $limit || ($stat['encryption_method'] ?? 0) !== 0) {
                    throw new ProcesamientoFallido('El paquete contiene un resultado inválido o demasiado grande.');
                }
            }
            // No se extraen rutas del ZIP al disco.
            $pdf = $zip->getFromName('documento.pdf');
            $json = $zip->getFromName('resultado.json');
            if (! is_string($pdf) || ! str_starts_with($pdf, '%PDF-') || ! str_contains(substr($pdf, -2048), '%%EOF') || ! is_string($json)) {
                throw new ProcesamientoFallido('El PDF o la transcripción del resultado no es válido.');
            }

            return ['resultado' => json_decode($json, true), 'pdf' => $pdf];
        } finally {
            if ($opened) {
                $zip->close();
            }
            fclose($temporary);
        }
    }
}
