<?php

namespace Tests\Feature;

use App\Jobs\ProcesarDocumento;
use App\Models\DocumentoPrueba;
use App\Models\User;
use App\Services\ProcesadorDocumental;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Tests\TestCase;
use ZipArchive;

class CargaCompuestaTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('documentos');
        Queue::fake();
        $this->actingAs(User::factory()->create());
        config(['documentos.processor_token' => str_repeat('x', 40)]);
        Http::preventStrayRequests();
    }

    private function pdf(string $name): UploadedFile
    {
        return UploadedFile::fake()->createWithContent($name, "%PDF-1.4\nDocumento sintetico\n%%EOF\n");
    }

    private function package(bool $invitationOnly): string
    {
        $text = $invitationOnly ? '' : 'Texto del documento';
        $data = ['estado' => 'completado', 'numero_paginas' => 1, 'duracion_total_ms' => 10,
            'texto_completo' => $text, 'invitacion_paginas' => $invitationOnly ? null : 1,
            'paginas' => [['numero' => 1, 'metodo' => $invitationOnly ? 'sin_transcripcion' : 'digital',
                'texto' => $text, 'duracion_ms' => 1, 'observaciones' => [], 'texto_digital' => null, 'variantes_ocr' => []]]];
        $tmp = tempnam(sys_get_temp_dir(), 'imantag-test-');
        $zip = new ZipArchive;
        $zip->open($tmp, ZipArchive::OVERWRITE);
        $zip->addFromString('resultado.json', json_encode($data));
        $zip->addFromString('documento.pdf', "%PDF-1.4\nDocumento\n%%EOF\n");
        if (! $invitationOnly) {
            $zip->addFromString('invitacion.pdf', "%PDF-1.4\nInvitacion\n%%EOF\n");
        }
        $zip->close();
        $bytes = file_get_contents($tmp);
        unlink($tmp);

        return $bytes;
    }

    public function test_documento_compuesto_conserva_orden_originales_e_invitacion(): void
    {
        $this->postJson('/documentos', ['archivos' => [UploadedFile::fake()->image('primera.png'), $this->pdf('segunda.pdf')],
            'invitacion' => $this->pdf('evento.pdf'), 'confirmacion_segundo' => 1])->assertCreated();
        $doc = DocumentoPrueba::firstOrFail();
        $this->assertSame('zip', $doc->tipo_archivo);
        $this->assertSame(['primera.png', 'segunda.pdf', 'evento.pdf'], array_column($doc->componentes, 'nombre'));
        $this->assertSame('evento.pdf', $doc->invitacion_nombre);
        $zip = new ZipArchive;
        $zip->open(Storage::disk('documentos')->path($doc->ruta_privada));
        $manifest = json_decode($zip->getFromName('manifest.json'), true);
        $this->assertCount(2, $manifest['documentos']);
        $this->assertSame('p002.pdf', $manifest['invitacion']['archivo']);
        $zip->close();
        Queue::assertPushed(ProcesarDocumento::class);
        Http::assertNothingSent();
    }

    public function test_rechaza_dos_pdf_y_segundo_componente_sin_confirmacion(): void
    {
        $this->postJson('/documentos', ['archivos' => [$this->pdf('uno.pdf'), $this->pdf('dos.pdf')]])->assertUnprocessable()->assertJsonValidationErrors('archivos');
        $this->postJson('/documentos', ['archivos' => [$this->pdf('uno.pdf')], 'invitacion' => $this->pdf('evento.pdf')])->assertUnprocessable()->assertJsonValidationErrors('confirmacion_segundo');
        $this->assertDatabaseCount('documentos_prueba', 0);
    }

    public function test_invitacion_independiente_no_crea_transcripcion_y_se_puede_consultar(): void
    {
        $this->postJson('/documentos', ['invitacion' => UploadedFile::fake()->image('invitacion.png')])->assertCreated();
        $doc = DocumentoPrueba::firstOrFail();
        $this->assertSame('invitacion', $doc->tipo_registro);
        Http::fake(['*' => Http::response($this->package(true), 200)]);
        (new ProcesarDocumento($doc->id, $doc->solicitud_uuid))->handle(app(ProcesadorDocumental::class));
        $doc->refresh();
        $this->assertSame('completado', $doc->estado_procesamiento);
        $this->assertSame(0, $doc->extracciones()->count());
        Http::assertSent(fn ($request) => str_ends_with($request->url(), '&transcribir=false'));
        $this->get(route('documentos.revision', $doc))->assertOk()->assertSee('sin transcripción');
        $this->get(route('documentos.pdf', $doc))->assertOk();
        $this->get(route('documentos.texto', $doc))->assertStatus(409);
    }

    public function test_job_asocia_invitacion_sin_incluir_su_texto_en_el_documento(): void
    {
        $this->postJson('/documentos', ['archivos' => [$this->pdf('oficio.pdf')], 'invitacion' => $this->pdf('evento.pdf'), 'confirmacion_segundo' => 1])->assertCreated();
        $doc = DocumentoPrueba::firstOrFail();
        Http::fake(['*' => Http::response($this->package(false), 200)]);
        (new ProcesarDocumento($doc->id, $doc->solicitud_uuid))->handle(app(ProcesadorDocumental::class));
        $doc->refresh();
        $this->assertSame('completado', $doc->estado_procesamiento);
        $this->assertSame('Texto del documento', $doc->extracciones()->firstOrFail()->texto_extraido);
        Storage::disk('documentos')->assertExists($doc->ruta_invitacion);
        $this->get(route('documentos.invitacion', $doc))->assertOk();
        $this->get(route('documentos.revision', $doc))->assertOk()->assertSee('evento.pdf', false);
        $this->get(route('documentos.original', $doc))->assertOk();
        $this->post(route('logout'));
        $this->get(route('documentos.invitacion', $doc))->assertRedirect(route('login'));
    }

    public function test_rechaza_multiples_invitaciones_y_zip_enviado_por_navegador(): void
    {
        $this->postJson('/documentos', ['invitacion' => [$this->pdf('uno.pdf'), $this->pdf('dos.pdf')]])->assertUnprocessable();
        $this->postJson('/documentos', ['archivos' => [UploadedFile::fake()->createWithContent('archivo.zip', 'PK0000')]])->assertUnprocessable();
    }

    public function test_revision_respeta_el_orden_y_permite_consultar_todas_las_paginas(): void
    {
        $this->postJson('/documentos', ['archivos' => [UploadedFile::fake()->image('imagen.png'), $this->pdf('principal.pdf')]])->assertCreated();
        $doc = DocumentoPrueba::firstOrFail();
        $components = $doc->componentes;
        $components[0]['paginas'] = 1;
        $components[1]['paginas'] = 2;
        $doc->update(['componentes' => $components, 'estado_procesamiento' => 'completado', 'numero_paginas' => 3]);
        foreach ([1 => 'Texto de la imagen', 2 => 'Texto del PDF primera', 3 => 'Texto del PDF segunda'] as $number => $text) {
            $doc->extracciones()->create(['numero_pagina' => $number, 'metodo_extraccion' => 'digital', 'texto_extraido' => $text, 'duracion_ms' => 1]);
        }
        $this->get(route('documentos.revision', $doc))->assertOk()->assertSee('Texto de la imagen')->assertSee('Texto completo del documento');
        $this->get(route('documentos.revision', ['documento' => $doc, 'pagina' => 2]))->assertOk()->assertSee('Texto del PDF primera')->assertSee('principal.pdf');
        $this->get(route('documentos.revision', ['documento' => $doc, 'pagina' => 1]))->assertOk()->assertSee('Texto de la imagen')->assertSee('imagen.png');
        $this->get(route('documentos.revision', ['documento' => $doc, 'pagina' => 3]))->assertOk()->assertSee('Texto del PDF segunda')->assertViewHas('origen', fn ($item) => $item['inicio'] === 2 && $item['fin'] === 3);
    }

    public function test_cargas_previas_tambien_abren_la_primera_pagina_del_conjunto(): void
    {
        $this->postJson('/documentos', ['archivos' => [UploadedFile::fake()->image('primera.png'), $this->pdf('principal.pdf')]])->assertCreated();
        $doc = DocumentoPrueba::firstOrFail();
        $doc->update(['estado_procesamiento' => 'completado', 'numero_paginas' => 2]);
        foreach ([1 => 'Texto de la imagen', 2 => 'Texto del PDF'] as $number => $text) {
            $doc->extracciones()->create(['numero_pagina' => $number, 'metodo_extraccion' => 'digital', 'texto_extraido' => $text, 'duracion_ms' => 1]);
        }
        $this->get(route('documentos.revision', $doc))->assertOk()->assertSee('Texto de la imagen')->assertSee('primera.png');
    }
}
