<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('evaluaciones_ocr', function (Blueprint $table) {
            $table->json('metricas')->nullable();
            $table->string('hash_extraccion', 64)->nullable();
            $table->timestampTz('evaluada_at')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('evaluaciones_ocr', fn (Blueprint $table) => $table->dropColumn(['metricas', 'hash_extraccion', 'evaluada_at']));
    }
};
