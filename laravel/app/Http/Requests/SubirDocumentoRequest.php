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
        return ['archivo' => ['bail', 'required', 'file', 'max:'.config('documentos.max_upload_kb'), new DocumentoSeguro]];
    }

    public function messages(): array
    {
        return ['archivo.required' => 'Selecciona un archivo.', 'archivo.file' => 'No se recibió un archivo válido.', 'archivo.max' => 'El archivo supera el tamaño máximo permitido.'];
    }
}
