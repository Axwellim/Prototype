<?php

namespace Tests\Feature;

use App\Jobs\ProcesarDocumento;
use App\Models\DocumentoPrueba;
use App\Models\User;
use App\Services\ProcesadorDocumental;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

class EliminarDocumentoTest extends TestCase
{
    use RefreshDatabase;

    private function documento(string $estado = 'completado'): DocumentoPrueba
    {
        Storage::fake('documentos');
        $uuid = (string) Str::uuid();
        $path = 'originales/'.$uuid.'.pdf';
        Storage::disk('documentos')->put($path, 'original de prueba');

        return DocumentoPrueba::create(['uuid' => $uuid, 'nombre_original' => 'eliminar-sintetico.pdf', 'tipo_archivo' => 'pdf',
            'tamano_bytes' => 18, 'hash_sha256' => str_repeat('a', 64), 'ruta_privada' => $path,
            'numero_paginas' => 1, 'estado_procesamiento' => $estado, 'fecha_carga' => now(), 'solicitud_uuid' => (string) Str::uuid()]);
    }

    public function test_eliminacion_exige_sesion_y_confirmacion(): void
    {
        $doc = $this->documento();
        $url = '/documentos/'.$doc->uuid;
        $this->deleteJson($url, ['confirmacion' => 1])->assertUnauthorized();
        $this->actingAs(User::factory()->create())->deleteJson($url)->assertUnprocessable();
        $this->assertNotNull(DocumentoPrueba::find($doc->id));
    }

    public function test_oculta_documento_y_protege_resultados_sin_borrar_archivos_o_transcripciones(): void
    {
        $doc = $this->documento();
        $doc->extracciones()->create(['numero_pagina' => 1, 'metodo_extraccion' => 'digital', 'texto_extraido' => 'Texto intacto', 'duracion_ms' => 1]);
        $doc->evaluaciones()->create(['numero_pagina' => 1, 'texto_referencia' => 'Referencia intacta']);
        $this->actingAs(User::factory()->create())->delete('/documentos/'.$doc->uuid, ['confirmacion' => 1])->assertRedirect('/documentos');
        $this->assertSoftDeleted('documentos_prueba', ['id' => $doc->id]);
        $this->get('/documentos')->assertOk()->assertDontSee($doc->nombre_original);
        foreach (['revision', 'original', 'pdf', 'texto'] as $action) {
            $this->get('/documentos/'.$doc->uuid.'/'.$action)->assertNotFound();
        }
        $this->getJson('/documentos/estados?uuids[]='.$doc->uuid)->assertOk()->assertJsonCount(0, 'documentos');
        $this->post('/documentos/'.$doc->uuid.'/reintentar')->assertNotFound();
        Storage::disk('documentos')->assertExists($doc->ruta_privada);
        $this->assertDatabaseHas('extracciones_documento', ['documento_id' => $doc->id, 'texto_extraido' => 'Texto intacto']);
        $this->assertDatabaseHas('evaluaciones_ocr', ['documento_id' => $doc->id, 'texto_referencia' => 'Referencia intacta']);
    }

    public function test_documento_procesando_no_se_elimina(): void
    {
        $doc = $this->documento('procesando');
        $this->actingAs(User::factory()->create())->deleteJson('/documentos/'.$doc->uuid, ['confirmacion' => 1])->assertConflict();
        $this->assertNotNull(DocumentoPrueba::find($doc->id));
    }

    public function test_tarea_pendiente_eliminada_no_contacta_procesador(): void
    {
        $doc = $this->documento('pendiente');
        Http::preventStrayRequests();
        Http::fake();
        $this->actingAs(User::factory()->create())->delete('/documentos/'.$doc->uuid, ['confirmacion' => 1])->assertRedirect();
        (new ProcesarDocumento($doc->id, $doc->solicitud_uuid))->handle(app(ProcesadorDocumental::class));
        Http::assertNothingSent();
        $this->assertDatabaseCount('extracciones_documento', 0);
    }
}
