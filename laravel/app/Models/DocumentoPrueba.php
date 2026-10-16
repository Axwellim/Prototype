<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Model;
use Illuminate\Database\Eloquent\Relations\HasMany;
use Illuminate\Database\Eloquent\SoftDeletes;

class DocumentoPrueba extends Model
{
    use SoftDeletes;

    protected $table = 'documentos_prueba';

    protected $fillable = ['uuid', 'nombre_original', 'tipo_archivo', 'tamano_bytes', 'hash_sha256', 'ruta_privada', 'numero_paginas', 'estado_procesamiento', 'fecha_carga', 'solicitud_uuid', 'modo_ocr', 'encolado_at', 'procesamiento_inicio', 'procesamiento_fin', 'intentos', 'duracion_total_ms', 'metodos_extraccion', 'error_procesamiento', 'ruta_pdf', 'hash_pdf', 'tamano_pdf', 'politica_digitalizacion', 'tipo_registro', 'componentes', 'invitacion_nombre', 'ruta_invitacion', 'hash_invitacion', 'tamano_invitacion', 'paginas_invitacion'];

    protected $hidden = ['ruta_privada', 'ruta_pdf', 'ruta_invitacion', 'componentes'];

    protected function casts(): array
    {
        return ['componentes' => 'array', 'fecha_carga' => 'immutable_datetime', 'tamano_bytes' => 'integer', 'numero_paginas' => 'integer', 'encolado_at' => 'immutable_datetime', 'procesamiento_inicio' => 'immutable_datetime', 'procesamiento_fin' => 'immutable_datetime', 'intentos' => 'integer', 'duracion_total_ms' => 'integer'];
    }

    public function getRouteKeyName(): string
    {
        return 'uuid';
    }

    public function extracciones(): HasMany
    {
        return $this->hasMany(ExtraccionDocumento::class, 'documento_id');
    }

    public function evaluaciones(): HasMany
    {
        return $this->hasMany(EvaluacionOcr::class, 'documento_id');
    }
}
