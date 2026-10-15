<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('documentos_prueba', fn (Blueprint $table) => $table->softDeletesTz());
    }

    public function down(): void
    {
        Schema::table('documentos_prueba', fn (Blueprint $table) => $table->dropSoftDeletes());
    }
};
