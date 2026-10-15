<?php

namespace Tests\Feature;

use App\Exceptions\ProcesamientoFallido;
use App\Jobs\ProcesarDocumento;
use App\Models\DocumentoPrueba;
use App\Models\ExtraccionDocumento;
use App\Models\User;
use App\Services\ColaDocumental;
use App\Services\ProcesadorDocumental;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Bus;
use Illuminate\Support\Facades\DB;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

class ColaDocumentalTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('documentos');
        Http::preventStrayRequests();
        config(['documentos.processor_token' => str_repeat('t', 64), 'documentos.processor_url' => 'http://127.0.0.1:8002']);
    }

    private function operador(): User
    {
        return User::create(['name' => 'Operador', 'email' => Str::uuid().'@example.test', 'password' => 'contraseña-de-prueba']);
    }

    private function documento(): DocumentoPrueba
    {
        $file = UploadedFile::fake()->image('ejemplo.png', 40, 40);
        $bytes = file_get_contents($file->getRealPath());
        $uuid = (string) Str::uuid();
        $path = 'originales/'.$uuid.'.png';
        Storage::disk('documentos')->put($path, $bytes);

        return DocumentoPrueba::create(['uuid' => $uuid, 'nombre_original' => 'ejemplo.png', 'tipo_archivo' => 'png',
            'tamano_bytes' => strlen($bytes), 'hash_sha256' => hash('sha256', $bytes), 'ruta_privada' => $path,
            'estado_procesamiento' => 'pendiente', 'fecha_carga' => now(), 'solicitud_uuid' => Str::uuid(), 'modo_ocr' => 'comparar']);
    }

    private function ejecutar(ProcesarDocumento $job): void
    {
        try {
            $job->handle(app(ProcesadorDocumental::class));
        } catch (ProcesamientoFallido) { /* Error controlado, comprobado mediante su estado persistente. */
        }
    }

    private function resultado(): array
    {
        $variants = [['modo' => 'original', 'texto' => 'Texto original', 'duracion_ms' => 20, 'operaciones' => []],
            ['modo' => 'preprocesado', 'texto' => 'Texto con filtro', 'duracion_ms' => 25, 'operaciones' => ['gris']]];

        return ['estado' => 'completado', 'numero_paginas' => 1, 'duracion_total_ms' => 60, 'texto_completo' => 'Texto original',
            'paginas' => [['numero' => 1, 'metodo' => 'ocr', 'texto' => 'Texto original', 'duracion_ms' => 50, 'observaciones' => ['Revisar sello'],
                'texto_digital' => 'encabezado parcial', 'variantes_ocr' => $variants]]];
    }

    private function paquete(?array $result = null): string
    {
        $path = tempnam(sys_get_temp_dir(), 'imantag-test-');
        $zip = new \ZipArchive;
        $zip->open($path, \ZipArchive::CREATE | \ZipArchive::OVERWRITE);
        $zip->addFromString('resultado.json', json_encode($result ?? $this->resultado()));
        $zip->addFromString('documento.pdf', "%PDF-1.4\nPDF sintetico de transporte\n%%EOF\n");
        $zip->close();
        $bytes = file_get_contents($path);
        unlink($path);

        return $bytes;
    }

    public function test_la_carga_encola_sin_contactar_python(): void
    {
        $this->actingAs($this->operador())->postJson('/documentos', ['archivo' => UploadedFile::fake()->image('doc.png'), 'modo_ocr' => 'comparar'])->assertCreated();
        $doc = DocumentoPrueba::firstOrFail();
        $this->assertSame('pendiente', $doc->estado_procesamiento);
        $this->assertSame('automatico', $doc->modo_ocr);
        $this->assertTrue(Str::isUuid($doc->solicitud_uuid));
        $this->assertDatabaseHas('jobs', ['queue' => 'ocr', 'attempts' => 0]);
        $payload = json_decode(DB::table('jobs')->first()->payload, true);
        $this->assertStringNotContainsString(str_repeat('t', 64), json_encode($payload));
        Http::assertNothingSent();
    }

    public function test_si_falla_encolado_se_revierte_registro_y_archivo_nuevos(): void
    {
        Bus::shouldReceive('dispatch')->once()->andThrow(new \RuntimeException('Cola no disponible'));
        $this->actingAs($this->operador())->postJson('/documentos', ['archivo' => UploadedFile::fake()->image('doc.png')])->assertStatus(503);
        $this->assertDatabaseCount('documentos_prueba', 0);
        $this->assertDatabaseCount('jobs', 0);
        $this->assertCount(0, Storage::disk('documentos')->allFiles());
    }

    public function test_job_guarda_variantes_capa_digital_y_estado_sin_tocar_referencia(): void
    {
        $doc = $this->documento();
        $doc->evaluaciones()->create(['numero_pagina' => 1, 'texto_referencia' => 'Referencia humana']);
        Http::fake(['*' => Http::response($this->paquete(), 200, ['Content-Type' => 'application/zip'])]);
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $doc->refresh();
        $this->assertSame('completado', $doc->estado_procesamiento);
        $this->assertSame(1, $doc->intentos);
        $this->assertSame(60, $doc->duracion_total_ms);
        $this->assertSame('ocr', $doc->metodos_extraccion);
        $extraction = $doc->extracciones()->firstOrFail();
        $this->assertSame('Texto original', $extraction->texto_extraido);
        $this->assertCount(2, $extraction->variantes_ocr);
        $this->assertSame('encabezado parcial', $extraction->texto_digital);
        $this->assertSame('Referencia humana', $doc->evaluaciones()->first()->texto_referencia);
        Storage::disk('documentos')->assertExists($doc->ruta_privada);
        $this->assertNotNull($doc->ruta_pdf);
        Storage::disk('documentos')->assertExists($doc->ruta_pdf);
        $this->assertSame($doc->hash_pdf, hash('sha256', Storage::disk('documentos')->get($doc->ruta_pdf)));
        Http::assertSent(fn ($request) => $request->hasHeader('X-Processor-Token', str_repeat('t', 64)) && str_ends_with($request->url(), '/procesar?modo=comparar&normalizar=true'));
    }

    public function test_job_duplicado_no_repite_http_ni_extracciones(): void
    {
        $doc = $this->documento();
        Http::fake(['*' => Http::response($this->paquete(), 200, ['Content-Type' => 'application/zip'])]);
        $job = new ProcesarDocumento($doc->id, $doc->solicitud_uuid);
        $job->handle(app(ProcesadorDocumental::class));
        $job->handle(app(ProcesadorDocumental::class));
        Http::assertSentCount(1);
        $this->assertDatabaseCount('extracciones_documento', 1);
    }

    public function test_pdf_resultante_privado_con_hash_y_rangos(): void
    {
        $doc = $this->documento();
        Http::fake(['*' => Http::response($this->paquete())]);
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $doc->refresh();
        $url = '/documentos/'.$doc->uuid.'/pdf';
        $this->get($url)->assertRedirect('/ingresar');
        $this->actingAs($this->operador())->get($url)->assertOk()->assertHeader('Content-Type', 'application/pdf');
        $this->withHeader('Range', 'bytes=0-7')->get($url)->assertStatus(206);
        Storage::disk('documentos')->put($doc->ruta_pdf, 'alterado');
        $this->get($url)->assertConflict();
        $doc->ruta_pdf = '../fuera.pdf';
        $doc->save();
        $this->get($url)->assertNotFound();
    }

    public function test_sin_pdf_no_hay_documento_completado_ni_transcripcion_parcial(): void
    {
        $doc = $this->documento();
        Http::fake(['*' => Http::response($this->resultado())]);
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $this->assertSame('error', $doc->fresh()->estado_procesamiento);
        $this->assertNull($doc->fresh()->ruta_pdf);
        $this->assertDatabaseCount('extracciones_documento', 0);
        $this->assertCount(1, Storage::disk('documentos')->allFiles());
    }

    public function test_fallo_de_persistencia_limpia_solo_pdf_nuevo_y_conserva_original(): void
    {
        $doc = $this->documento();
        Http::fake(['*' => Http::response($this->paquete())]);
        ExtraccionDocumento::saving(function () {
            throw new \RuntimeException('Fallo de persistencia simulado');
        });
        try {
            $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        } finally {
            ExtraccionDocumento::flushEventListeners();
        }
        $this->assertSame('error', $doc->fresh()->estado_procesamiento);
        $this->assertDatabaseCount('extracciones_documento', 0);
        Storage::disk('documentos')->assertExists($doc->ruta_privada);
        $this->assertCount(1, Storage::disk('documentos')->allFiles());
    }

    public function test_pdf_excedido_se_rechaza_antes_de_guardar(): void
    {
        $doc = $this->documento();
        Http::fake(['*' => Http::response($this->paquete())]);
        config(['documentos.max_pdf_bytes' => 10]);
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $this->assertSame('error', $doc->fresh()->estado_procesamiento);
        $this->assertDatabaseCount('extracciones_documento', 0);
        $this->assertCount(1, Storage::disk('documentos')->allFiles());
    }

    public function test_error_remoto_es_publico_y_reintentable(): void
    {
        $doc = $this->documento();
        Http::fake(['*' => Http::response(['detail' => ['codigo' => 'idioma_no_disponible']], 503)]);
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $this->assertSame('error', $doc->fresh()->estado_procesamiento);
        $this->assertStringContainsString('idioma', $doc->fresh()->error_procesamiento);
        $this->assertDatabaseCount('extracciones_documento', 0);
        $old = $doc->solicitud_uuid;
        $this->actingAs($this->operador())->post('/documentos/'.$doc->uuid.'/reintentar')->assertRedirect('/documentos');
        $this->assertSame('pendiente', $doc->fresh()->estado_procesamiento);
        $this->assertNotSame($old, $doc->fresh()->solicitud_uuid);
        $this->assertDatabaseCount('jobs', 1);
        // Una tarea o fallo del intento anterior no puede cambiar el nuevo estado.
        (new ProcesarDocumento($doc->id, $old))->failed(new \RuntimeException('viejo'));
        $this->assertSame('pendiente', $doc->fresh()->estado_procesamiento);
        $this->post('/documentos/'.$doc->uuid.'/reintentar')->assertSessionHasErrors('archivo');
        $this->assertDatabaseCount('jobs', 1);
    }

    public function test_respuesta_inconsistente_no_guarda_resultados_parciales(): void
    {
        $doc = $this->documento();
        $data = $this->resultado();
        $data['numero_paginas'] = 2;
        Http::fake(['*' => Http::response($this->paquete($data), 200, ['Content-Type' => 'application/zip'])]);
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $this->assertSame('error', $doc->fresh()->estado_procesamiento);
        $this->assertDatabaseCount('extracciones_documento', 0);
    }

    public function test_archivo_alterado_no_se_envia_al_procesador(): void
    {
        $doc = $this->documento();
        Storage::disk('documentos')->put($doc->ruta_privada, 'archivo alterado');
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $this->assertSame('error', $doc->fresh()->estado_procesamiento);
        Http::assertNothingSent();
    }

    public function test_no_se_acepta_url_externa_para_enviar_documentos(): void
    {
        $doc = $this->documento();
        config(['documentos.processor_url' => 'http://example.test']);
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $this->assertSame('error', $doc->fresh()->estado_procesamiento);
        Http::assertNothingSent();
    }

    public function test_documento_previo_sin_tarea_se_puede_encolar_una_vez(): void
    {
        $doc = $this->documento();
        $doc->update(['solicitud_uuid' => null]);
        $cola = app(ColaDocumental::class);
        $this->assertTrue($cola->reintentar($doc));
        $this->assertFalse($cola->reintentar($doc));
        $this->assertDatabaseCount('jobs', 1);
    }

    public function test_estados_exigen_sesion_y_no_exponen_archivos_ni_claves(): void
    {
        $doc = $this->documento();
        $url = '/documentos/estados?'.http_build_query(['uuids' => [$doc->uuid]]);
        $this->getJson($url)->assertUnauthorized();
        $response = $this->actingAs($this->operador())->getJson($url)->assertOk()->assertJsonPath('documentos.0.estado', 'pendiente');
        $response->assertJsonMissingPath('documentos.0.ruta_privada')->assertJsonMissingPath('documentos.0.hash_sha256');
        $this->getJson('/documentos/estados?uuids[]=incorrecto')->assertUnprocessable();
    }

    public function test_job_interrumpido_no_se_reprocesa_a_ciegas(): void
    {
        $doc = $this->documento();
        $doc->update(['estado_procesamiento' => 'procesando', 'procesamiento_inicio' => now()->subMinutes(10)]);
        $this->ejecutar(new ProcesarDocumento($doc->id, $doc->solicitud_uuid));
        $this->assertSame('error', $doc->fresh()->estado_procesamiento);
        Http::assertNothingSent();
    }

    public function test_fallo_tardio_no_cambia_documento_completado(): void
    {
        $doc = $this->documento();
        $doc->update(['estado_procesamiento' => 'completado']);
        (new ProcesarDocumento($doc->id, $doc->solicitud_uuid))->failed(new \RuntimeException('Ack perdido'));
        $this->assertSame('completado', $doc->fresh()->estado_procesamiento);
    }
}
