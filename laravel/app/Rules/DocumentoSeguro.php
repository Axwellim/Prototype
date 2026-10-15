<?php

namespace App\Rules;

use Closure;
use Illuminate\Contracts\Validation\ValidationRule;
use Illuminate\Http\UploadedFile;

class DocumentoSeguro implements ValidationRule
{
    public function validate(string $attribute, mixed $value, Closure $fail): void
    {
        if (! $value instanceof UploadedFile || ! $value->isValid()) {
            $fail('No se pudo recibir el archivo.');

            return;
        }
        $path = $value->getRealPath();
        $mime = (new \finfo(FILEINFO_MIME_TYPE))->file($path);
        $extensions = ['application/pdf' => ['pdf'], 'image/jpeg' => ['jpg', 'jpeg'], 'image/png' => ['png']];
        if (! isset($extensions[$mime]) || ! in_array(strtolower($value->getClientOriginalExtension()), $extensions[$mime], true)) {
            $fail('El contenido debe ser PDF, JPG, JPEG o PNG y coincidir con su extensión.');

            return;
        }
        if ($mime === 'application/pdf') {
            $handle = fopen($path, 'rb');
            try {
                $header = fread($handle, 8);
                fseek($handle, max(0, filesize($path) - 2048));
                $tail = stream_get_contents($handle);
            } finally {
                fclose($handle);
            }
            if (! preg_match('/^%PDF-\d\.\d/', $header) || ! str_contains($tail, '%%EOF')) {
                $fail('El PDF está incompleto o no tiene una estructura básica válida.');
            }

            // La validación profunda y el máximo de páginas requieren el parser del bloque 3.
            return;
        }
        $info = @getimagesize($path);
        if (! $info || ($info[0] * $info[1]) > config('documentos.max_image_pixels') || ($info['mime'] ?? '') !== $mime) {
            $fail('La imagen es inválida o supera el límite de píxeles permitido.');

            return;
        }
        $image = @imagecreatefromstring(file_get_contents($path));
        if ($image === false) {
            $fail('La imagen está dañada y no se puede decodificar.');

            return;
        }
        imagedestroy($image);
    }
}
