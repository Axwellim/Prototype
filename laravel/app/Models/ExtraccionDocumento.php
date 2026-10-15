<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class ExtraccionDocumento extends Model
{
    protected $table = 'extracciones_documento';

    protected $fillable = ['documento_id', 'numero_pagina', 'metodo_extraccion', 'texto_extraido', 'duracion_ms', 'observaciones', 'texto_digital', 'variantes_ocr'];

    protected function casts(): array
    {
        return ['variantes_ocr' => 'array'];
    }

    public function documento(): BelongsTo
    {
        return $this->belongsTo(DocumentoPrueba::class, 'documento_id');
    }
}
