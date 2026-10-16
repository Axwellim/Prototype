<?php

namespace App\Http\Requests;

use App\Rules\DocumentoSeguro;
use Illuminate\Foundation\Http\FormRequest;

class SubirDocumentoRequest extends FormRequest
{
    public function authorize(): bool
    {
        return $this->user() !== null;
    }

    public function rules(): array
    {
        $file = ['bail', 'file', 'max:'.config('documentos.max_upload_kb'), new DocumentoSeguro];

        return [
            'archivo' => array_merge(['required_without_all:archivos,invitacion', 'prohibits:archivos,invitacion'], $file),
            'archivos' => 'sometimes|array|list|min:1|max:19',
            'archivos.*' => $file,
            'invitacion' => array_merge(['sometimes'], $file),
            'confirmacion_segundo' => 'sometimes|boolean',
        ];
    }

    public function after(): array
    {
        return [function ($validator) {
            $files = $this->file('archivos', []);
            $invitation = $this->file('invitacion');
            if (! is_array($files) || $validator->errors()->isNotEmpty()) {
                return;
            }
            if (! $files && ! $invitation && ! $this->hasFile('archivo')) {
                $validator->errors()->add('archivos', 'Selecciona un documento o una invitación.');
            }
            $pdfs = collect($files)->filter(fn ($file) => (new \finfo(FILEINFO_MIME_TYPE))->file($file->getRealPath()) === 'application/pdf')->count();
            if ($pdfs > 1) {
                $validator->errors()->add('archivos', 'El documento admite un solo PDF y varias imágenes.');
            }
            $total = collect($files)->sum(fn ($file) => $file->getSize()) + ($invitation?->getSize() ?? 0);
            if ($total > config('documentos.max_upload_kb') * 1024 - 32768) {
                $validator->errors()->add('archivos', 'El conjunto de archivos supera el tamaño máximo de carga.');
            }
            if ($files && $invitation && ! $this->boolean('confirmacion_segundo')) {
                $validator->errors()->add('confirmacion_segundo', 'Confirma el aviso del segundo componente antes de guardar.');
            }
        }];
    }

    public function messages(): array
    {
        return ['archivo.required' => 'Selecciona un archivo.', 'archivo.file' => 'No se recibió un archivo válido.', 'archivo.max' => 'El archivo supera el tamaño máximo permitido.'];
    }
}
