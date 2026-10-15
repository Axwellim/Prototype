<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\BelongsTo;

class EvaluacionOcr extends Model
{
    protected $table = 'evaluaciones_ocr';

    protected function casts(): array
    {
        return ['metricas' => 'array', 'evaluada_at' => 'datetime'];
    }

    protected $fillable = ['documento_id', 'numero_pagina', 'texto_referencia', 'observaciones', 'usuario_id'];

    public function usuario(): BelongsTo
    {
        return $this->belongsTo(User::class, 'usuario_id');
    }

    public function documento(): BelongsTo
    {
        return $this->belongsTo(DocumentoPrueba::class, 'documento_id');
    }
}
