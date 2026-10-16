<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('documentos_prueba', function (Blueprint $table) {
            $table->string('tipo_registro', 20)->default('documento');
            $table->json('componentes')->nullable();
            $table->string('invitacion_nombre')->nullable();
            $table->string('ruta_invitacion')->nullable();
            $table->string('hash_invitacion', 64)->nullable();
            $table->unsignedBigInteger('tamano_invitacion')->nullable();
            $table->unsignedInteger('paginas_invitacion')->nullable();
        });
    }

    public function down(): void
    {
        Schema::table('documentos_prueba', function (Blueprint $table) {
            $table->dropColumn(['tipo_registro', 'componentes', 'invitacion_nombre', 'ruta_invitacion', 'hash_invitacion', 'tamano_invitacion', 'paginas_invitacion']);
        });
    }
};
