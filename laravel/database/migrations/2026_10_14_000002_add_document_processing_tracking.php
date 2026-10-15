<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('documentos_prueba', function (Blueprint $table) {
            $table->uuid('solicitud_uuid')->nullable()->unique();
            $table->string('modo_ocr', 20)->default('original');
            $table->unsignedInteger('intentos')->default(0);
            $table->timestampTz('encolado_at')->nullable();
            $table->timestampTz('procesamiento_inicio')->nullable();
            $table->timestampTz('procesamiento_fin')->nullable();
            $table->unsignedBigInteger('duracion_total_ms')->nullable();
            $table->string('metodos_extraccion', 40)->nullable();
            $table->text('error_procesamiento')->nullable();
        });
        Schema::table('extracciones_documento', function (Blueprint $table) {
            $table->longText('texto_digital')->nullable();
            $table->json('variantes_ocr')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('extracciones_documento', fn (Blueprint $table) => $table->dropColumn(['texto_digital', 'variantes_ocr']));
        Schema::table('documentos_prueba', function (Blueprint $table) {
            $table->dropUnique(['solicitud_uuid']);
            $table->dropColumn(['solicitud_uuid', 'modo_ocr', 'intentos', 'encolado_at', 'procesamiento_inicio', 'procesamiento_fin', 'duracion_total_ms', 'metodos_extraccion', 'error_procesamiento']);
        });
    }
};
