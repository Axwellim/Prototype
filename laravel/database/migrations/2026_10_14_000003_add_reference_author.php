<?php

use Illuminate\Database\Migrations\Migration;
use Illuminate\Database\Schema\Blueprint;
use Illuminate\Support\Facades\Schema;

return new class extends Migration
{
    public function up(): void
    {
        Schema::table('evaluaciones_ocr', function (Blueprint $table) {
            $table->foreignId('usuario_id')->nullable()->constrained('users')->nullOnDelete();
            $table->index(['documento_id', 'numero_pagina', 'id'], 'evaluaciones_pagina_version');
        });
    }

    public function down(): void
    {
        Schema::table('evaluaciones_ocr', function (Blueprint $table) {
            $table->dropIndex('evaluaciones_pagina_version');
            $table->dropConstrainedForeignId('usuario_id');
        });
    }
};
