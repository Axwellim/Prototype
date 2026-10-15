<?php

namespace Tests\Feature;

use App\Models\DocumentoPrueba;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Http;
use Illuminate\Support\Str;
use Tests\TestCase;

class CalidadDocumentoTest extends TestCase
{
    use RefreshDatabase;

    private function fixture(): array
    {
        config(['documentos.processor_url' => 'http://127.0.0.1:8002', 'documentos.processor_token' => str_repeat('x', 40)]);
        Http::preventStrayRequests();
        $user = User::factory()->create();
        $doc = DocumentoPrueba::create(['uuid' => (string) Str::uuid(), 'nombre_original' => 'sintetico.pdf', 'tipo_archivo' => 'pdf',
            'tamano_bytes' => 10, 'hash_sha256' => str_repeat('a', 64), 'ruta_privada' => 'prueba', 'estado_procesamiento' => 'completado',
            'numero_paginas' => 1, 'fecha_carga' => now()]);
        $page = $doc->extracciones()->create(['numero_pagina' => 1, 'metodo_extraccion' => 'digital', 'texto_extraido' => 'hola munda', 'duracion_ms' => 1, 'variantes_ocr' => []]);
        $ref = $doc->evaluaciones()->create(['numero_pagina' => 1, 'texto_referencia' => 'hola mundo', 'usuario_id' => $user->id]);
        $payload = ['numero_pagina' => 1, 'revision' => $ref->id, 'confirmacion' => '1'];

        return [$user, $doc, $page, $ref, $payload];
    }

    private function metricResult(): array
    {
        $counts = ['tasa' => .1, 'sustituciones' => 1, 'eliminaciones' => 0, 'inserciones' => 0, 'unidades_referencia' => 10];

        return ['motor' => 'jiwer', 'version' => '4.0.0', 'politica' => 'nfc-espacios-v1', 'variantes' => ['principal' => ['cer' => $counts, 'wer' => array_replace($counts, ['tasa' => .5, 'unidades_referencia' => 2])]]];
    }

    public function test_persistencia_por_version_sin_alterar_textos_y_oculta_al_cambiar_referencia(): void
    {
        [$user, $doc, $page, $ref, $data] = $this->fixture();
        Http::fake(['*/evaluar' => Http::response($this->metricResult())]);
        $this->actingAs($user)->post('/documentos/'.$doc->uuid.'/calidad', $data)->assertRedirect();
        $this->assertSame(.5, $ref->fresh()->metricas['variantes']['principal']['wer']['tasa']);
        $this->assertSame('hola munda', $page->fresh()->texto_extraido);
        $this->assertSame('hola mundo', $ref->fresh()->texto_referencia);
        Http::assertSent(fn ($request) => $request['referencia'] === 'hola mundo' && $request['variantes'] === ['principal' => 'hola munda']);
        $this->get('/documentos/'.$doc->uuid.'/revision')->assertOk()->assertSee('50.00 %');
        $doc->evaluaciones()->create(['numero_pagina' => 1, 'texto_referencia' => 'Nueva versión', 'usuario_id' => $user->id]);
        $this->get('/documentos/'.$doc->uuid.'/revision')->assertOk()->assertDontSee('id="quality-results"', false);
        $this->assertNotNull($ref->fresh()->metricas);
    }

    public function test_exige_sesion_confirmacion_version_actual_y_autor(): void
    {
        [$user, $doc, $page, $ref, $data] = $this->fixture();
        $url = '/documentos/'.$doc->uuid.'/calidad';
        $this->postJson($url, $data)->assertUnauthorized();
        $this->actingAs($user)->postJson($url, array_replace($data, ['confirmacion' => false]))->assertUnprocessable();
        $this->postJson($url, array_replace($data, ['revision' => $ref->id + 1]))->assertConflict();
        $ref->usuario_id = null;
        $ref->save();
        $this->postJson($url, $data)->assertUnprocessable();
        Http::assertNothingSent();
    }

    public function test_compara_variantes_y_oculta_resultados_si_cambia_la_extraccion(): void
    {
        [$user, $doc, $page, $ref, $data] = $this->fixture();
        $page->variantes_ocr = [['modo' => 'original', 'texto' => 'hola munda', 'duracion_ms' => 1, 'operaciones' => []],
            ['modo' => 'preprocesado', 'texto' => 'hola mundo', 'duracion_ms' => 1, 'operaciones' => []]];
        $page->save();
        $result = $this->metricResult();
        $result['variantes']['original'] = $result['variantes']['principal'];
        $result['variantes']['preprocesado'] = $result['variantes']['principal'];
        foreach (['wer', 'cer'] as $metric) {
            $result['variantes']['preprocesado'][$metric]['tasa'] = 0;
            $result['variantes']['preprocesado'][$metric]['sustituciones'] = 0;
        }
        Http::fake(['*/evaluar' => Http::response($result)]);
        $this->actingAs($user)->post('/documentos/'.$doc->uuid.'/calidad', $data)->assertRedirect();
        $this->get('/documentos/'.$doc->uuid.'/revision')->assertOk()->assertSee('OCR con preprocesamiento')->assertSee('0.00 %');
        $page->texto_extraido = 'Extracción modificada';
        $page->save();
        $this->get('/documentos/'.$doc->uuid.'/revision')->assertOk()->assertDontSee('id="quality-results"', false);
        $this->assertNotNull($ref->fresh()->metricas);
    }

    public function test_fallo_servicio_y_respuesta_invalida_no_guardan_metricas(): void
    {
        [$user, $doc, $page, $ref, $data] = $this->fixture();
        Http::fake(['*/evaluar' => Http::sequence()->push([], 503)->push(['motor' => 'otro'])]);
        $this->actingAs($user)->postJson('/documentos/'.$doc->uuid.'/calidad', $data)->assertStatus(503);
        $this->postJson('/documentos/'.$doc->uuid.'/calidad', $data)->assertStatus(502);
        $this->assertNull($ref->fresh()->metricas);
    }

    public function test_cambio_durante_calculo_rechaza_resultado_y_limite_no_trunca(): void
    {
        [$user, $doc, $page, $ref, $data] = $this->fixture();
        Http::fake(function () use ($doc, $user) {
            $doc->evaluaciones()->create(['numero_pagina' => 1, 'texto_referencia' => 'Nueva revisión', 'usuario_id' => $user->id]);

            return Http::response($this->metricResult());
        });
        $this->actingAs($user)->postJson('/documentos/'.$doc->uuid.'/calidad', $data)->assertConflict();
        $this->assertNull($ref->fresh()->metricas);
        $latest = $doc->evaluaciones()->latest('id')->first();
        $latest->texto_referencia = str_repeat('a', 10001);
        $latest->save();
        $this->postJson('/documentos/'.$doc->uuid.'/calidad', array_replace($data, ['revision' => $latest->id]))->assertUnprocessable();
        $this->assertSame(10001, mb_strlen($latest->fresh()->texto_referencia));
    }
}
