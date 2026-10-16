<?php

namespace App\Services;

use App\Http\Requests\SubirDocumentoRequest;
use Illuminate\Support\Facades\Storage;
use RuntimeException;
use ZipArchive;

class CargaCompuesta
{
    public function guardar(SubirDocumentoRequest $request, string $uuid): array
    {
        $files = $request->file('archivos', []);
        if ($request->hasFile('archivo')) {
            $files = [$request->file('archivo')];
        }
        $invitation = $request->file('invitacion');
        $all = array_merge($files, $invitation ? [$invitation] : []);
        $components = [];
        foreach ($all as $index => $file) {
            $mime = (new \finfo(FILEINFO_MIME_TYPE))->file($file->getRealPath());
            $extension = ['application/pdf' => 'pdf', 'image/jpeg' => 'jpg', 'image/png' => 'png'][$mime];
            $name = preg_replace('/[\x00-\x1F\x7F]/u', '', str_replace('\\', '/', $file->getClientOriginalName()));
            $components[] = ['archivo' => sprintf('p%03d.%s', $index, $extension),
                'nombre' => mb_substr(basename($name ?: 'archivo.'.$extension), 0, 255),
                'tipo' => $index < count($files) ? 'documento' : 'invitacion',
                'tamano' => $file->getSize(), 'hash' => hash_file('sha256', $file->getRealPath())];
        }
        $disk = Storage::disk('documentos');
        $extension = count($all) > 1 ? 'zip' : pathinfo($components[0]['archivo'], PATHINFO_EXTENSION);
        $path = 'originales/'.$uuid.'.'.$extension;
        if (count($all) === 1) {
            if (! $disk->putFileAs('originales', $all[0], $uuid.'.'.$extension)) {
                throw new RuntimeException('No se pudo conservar el original.');
            }
            $size = $all[0]->getSize();
            $hash = $components[0]['hash'];
        } else {
            $temporary = tempnam(sys_get_temp_dir(), 'imantag-carga-');
            if (! $temporary) {
                throw new RuntimeException('No se pudo preparar la composición.');
            }
            $zip = new ZipArchive;
            $opened = false;
            try {
                $opened = $zip->open($temporary, ZipArchive::OVERWRITE) === true;
                if (! $opened) {
                    throw new RuntimeException('No se pudo preparar la composición.');
                }
                $manifest = ['documentos' => array_slice($components, 0, count($files)),
                    'invitacion' => $invitation ? end($components) : null];
                if (! $zip->addFromString('manifest.json', json_encode($manifest, JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE))) {
                    throw new RuntimeException('No se pudo preparar la composición.');
                }
                $zip->setCompressionName('manifest.json', ZipArchive::CM_STORE);
                foreach ($all as $index => $file) {
                    if (! $zip->addFile($file->getRealPath(), $components[$index]['archivo'])) {
                        throw new RuntimeException('No se pudo preparar la composición.');
                    }
                    $zip->setCompressionName($components[$index]['archivo'], ZipArchive::CM_STORE);
                }
                $opened = false;
                if (! $zip->close()) {
                    throw new RuntimeException('No se pudo finalizar la composición.');
                }
                $local = $temporary;
                $size = filesize($local);
                $hash = hash_file('sha256', $local);
                $stream = fopen($local, 'rb');
                try {
                    if ($size > config('documentos.max_upload_kb') * 1024 || ! $disk->put($path, $stream)) {
                        throw new RuntimeException('No se pudo conservar la composición.');
                    }
                } finally {
                    fclose($stream);
                }
            } finally {
                if ($opened) {
                    $zip->close();
                }
                unlink($temporary);
            }
        }

        $principal = collect($components)->first(fn ($part) => $part['tipo'] === 'documento' && str_ends_with($part['archivo'], '.pdf'));

        return ['nombre_original' => $principal['nombre'] ?? $components[0]['nombre'], 'tipo_archivo' => $extension,
            'tamano_bytes' => $size, 'hash_sha256' => $hash, 'ruta_privada' => $path,
            'numero_paginas' => $extension === 'pdf' || $extension === 'zip' ? null : 1,
            'tipo_registro' => $files ? 'documento' : 'invitacion', 'componentes' => $components,
            'invitacion_nombre' => $files && $invitation ? end($components)['nombre'] : null];
    }
}
