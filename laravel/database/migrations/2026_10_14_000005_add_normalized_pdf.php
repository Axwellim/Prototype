<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('documentos_prueba', function (Blueprint $table) {
            $table->string('ruta_pdf')->nullable()->unique();
            $table->string('hash_pdf', 64)->nullable();
            $table->unsignedBigInteger('tamano_pdf')->nullable();
            $table->string('politica_digitalizacion', 60)->nullable();
            $table->string('modo_ocr')->default('automatico')->change();
        });
    }

    public function down(): void
    {
        Schema::table('documentos_prueba', function (Blueprint $table) {
            $table->dropUnique(['ruta_pdf']);
            $table->dropColumn(['ruta_pdf', 'hash_pdf', 'tamano_pdf', 'politica_digitalizacion']);
            $table->string('modo_ocr')->default('original')->change();
        });
    }
};
