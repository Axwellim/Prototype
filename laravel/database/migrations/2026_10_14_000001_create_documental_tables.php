<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::create('documentos_prueba', function (Blueprint $table) {
            $table->id();
            $table->uuid('uuid')->unique();
            $table->string('nombre_original');
            $table->string('tipo_archivo', 10);
            $table->unsignedBigInteger('tamano_bytes');
            $table->char('hash_sha256', 64)->index();
            $table->string('ruta_privada')->unique();
            $table->unsignedInteger('numero_paginas')->nullable();
            $table->string('estado_procesamiento', 20)->default('pendiente')->index();
            $table->timestampTz('fecha_carga')->index();
            $table->timestampsTz();
        });
        Schema::create('extracciones_documento', function (Blueprint $table) {
            $table->id();
            $table->foreignId('documento_id')->constrained('documentos_prueba')->restrictOnDelete();
            $table->unsignedInteger('numero_pagina');
            $table->string('metodo_extraccion', 20);
            $table->longText('texto_extraido');
            $table->unsignedBigInteger('duracion_ms');
            $table->text('observaciones')->nullable();
            $table->timestampsTz();
            $table->unique(['documento_id', 'numero_pagina']);
        });
        Schema::create('evaluaciones_ocr', function (Blueprint $table) {
            $table->id();
            $table->foreignId('documento_id')->constrained('documentos_prueba')->restrictOnDelete();
            $table->unsignedInteger('numero_pagina')->nullable();
            $table->longText('texto_referencia')->nullable();
            $table->text('observaciones')->nullable();
            $table->timestampsTz();
            $table->index(['documento_id', 'numero_pagina']);
        });
    }

    public function down(): void
    {
        Schema::dropIfExists('evaluaciones_ocr');
        Schema::dropIfExists('extracciones_documento');
        Schema::dropIfExists('documentos_prueba');
    }
};
