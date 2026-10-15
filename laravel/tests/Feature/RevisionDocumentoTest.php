<?php

namespace Tests\Feature;

use App\Models\DocumentoPrueba;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use Tests\TestCase;

class RevisionDocumentoTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('documentos');
    }

    private function operador(): User
    {
        return User::create(['name' => 'Revisor de prueba', 'email' => Str::uuid().'@example.test', 'password' => 'clave-larga-de-prueba']);
    }

    private function documento(string $type = 'pdf', string $text = 'Texto automático'): DocumentoPrueba
    {
        if ($type === 'png') {
            $image = imagecreatetruecolor(40, 40);
            ob_start();
            imagepng($image);
            $bytes = ob_get_clean();
            imagedestroy($image);
        } else {
            $bytes = "%PDF-1.4\n";
            $objects = ['<< /Type /Catalog /Pages 2 0 R >>', '<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>',
                '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] >>', '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] >>'];
            $offsets = [];
            foreach ($objects as $index => $object) {
                $offsets[] = strlen($bytes);
                $bytes .= ($index + 1)." 0 obj\n".$object."\nendobj\n";
            }
            $xref = strlen($bytes);
            $bytes .= "xref\n0 5\n0000000000 65535 f \n";
            foreach ($offsets as $offset) {
                $bytes .= sprintf("%010d 00000 n \n", $offset);
            }
            $bytes .= "trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n".$xref."\n%%EOF\n";
        }
        $uuid = (string) Str::uuid();
        $path = 'originales/'.$uuid.'.'.$type;
        Storage::disk('documentos')->put($path, $bytes);
        $doc = DocumentoPrueba::create(['uuid' => $uuid, 'nombre_original' => 'revision.'.$type, 'tipo_archivo' => $type, 'tamano_bytes' => strlen($bytes),
            'hash_sha256' => hash('sha256', $bytes), 'ruta_privada' => $path, 'estado_procesamiento' => 'completado', 'numero_paginas' => $type === 'pdf' ? 2 : 1, 'fecha_carga' => now()]);
        for ($page = 1; $page <= $doc->numero_paginas; $page++) {
            $doc->extracciones()->create(['numero_pagina' => $page, 'metodo_extraccion' => 'digital', 'texto_extraido' => $text.' '.$page,
                'duracion_ms' => 100, 'observaciones' => 'Observación de prueba', 'variantes_ocr' => []]);
        }

        return $doc;
    }

    private function datos(?int $revision = null, string $text = 'Referencia humana'): array
    {
        return ['numero_pagina' => 1, 'texto_referencia' => $text, 'observaciones' => null, 'revision' => $revision];
    }

    public function test_todas_las_rutas_de_revision_exigen_sesion(): void
    {
        $doc = $this->documento();
        foreach (['revision', 'original', 'texto'] as $action) {
            $this->get('/documentos/'.$doc->uuid.'/'.$action)->assertRedirect('/ingresar');
        }
        $this->postJson('/documentos/'.$doc->uuid.'/referencia', $this->datos())->assertUnauthorized();
    }

    public function test_revision_muestra_solo_pagina_seleccionada_y_texto_escapado(): void
    {
        $doc = $this->documento('pdf', '</textarea><script>alert(1)</script>');
        $response = $this->actingAs($this->operador())->get('/documentos/'.$doc->uuid.'/revision?pagina=2')->assertOk();
        $response->assertSee('Página 2 de 2')->assertSee('id="reference-text"', false)->assertSee('readonly', false);
        $response->assertDontSee('</textarea><script>alert(1)</script>', false)->assertSee('&lt;script&gt;', false);
        $this->get('/documentos/'.$doc->uuid.'/revision?pagina=3')->assertNotFound();
        $this->get('/documentos/'.$doc->uuid.'/revision?pagina=abc')->assertNotFound();
    }

    public function test_original_privado_se_sirve_con_tipo_real_y_sin_cache_publica(): void
    {
        $doc = $this->documento('png');
        $response = $this->actingAs($this->operador())->get('/documentos/'.$doc->uuid.'/original')->assertOk()->assertHeader('Content-Type', 'image/png')->assertHeader('X-Content-Type-Options', 'nosniff');
        $this->assertStringContainsString('no-store', $response->headers->get('Cache-Control'));
        $this->assertSame(realpath(Storage::disk('documentos')->path($doc->ruta_privada)), $response->baseResponse->getFile()->getRealPath());
        $this->get('/storage/'.$doc->ruta_privada)->assertNotFound();
    }

    public function test_pdf_admite_rangos_sin_eludir_autenticacion(): void
    {
        $doc = $this->documento();
        $this->actingAs($this->operador())->get('/documentos/'.$doc->uuid.'/original', ['Range' => 'bytes=0-7'])
            ->assertStatus(206)->assertHeader('Content-Range', 'bytes 0-7/'.$doc->tamano_bytes);
    }

    public function test_ruta_alterada_o_hash_incorrecto_no_se_sirven(): void
    {
        $doc = $this->documento();
        $this->actingAs($this->operador());
        $original = $doc->ruta_privada;
        $doc->update(['ruta_privada' => '../../.env']);
        $this->get('/documentos/'.$doc->uuid.'/original')->assertNotFound();
        $doc->update(['ruta_privada' => $original]);
        Storage::disk('documentos')->put($original, 'otro contenido');
        $this->get('/documentos/'.$doc->uuid.'/original')->assertStatus(409);
    }

    public function test_guardado_preserva_espacios_autoria_y_extraccion_automatica(): void
    {
        $doc = $this->documento();
        $user = $this->operador();
        $text = "  Señora María Pérez\nOficio 001-2026  ";
        $this->actingAs($user)->postJson('/documentos/'.$doc->uuid.'/referencia', $this->datos(null, $text))->assertOk()->assertJsonStructure(['revision']);
        $reference = $doc->evaluaciones()->firstOrFail();
        $this->assertSame($text, $reference->texto_referencia);
        $this->assertSame($user->id, $reference->usuario_id);
        $this->assertSame('Texto automático 1', $doc->extracciones()->where('numero_pagina', 1)->first()->texto_extraido);
    }

    public function test_nueva_version_conserva_historial_y_guardado_identico_no_duplica(): void
    {
        $doc = $this->documento();
        $this->actingAs($this->operador());
        $url = '/documentos/'.$doc->uuid.'/referencia';
        $first = $this->postJson($url, $this->datos())->assertOk()->json('revision');
        $second = $this->postJson($url, $this->datos($first, 'Segunda versión'))->assertOk()->json('revision');
        $this->assertNotSame($first, $second);
        $this->assertDatabaseCount('evaluaciones_ocr', 2);
        $this->postJson($url, $this->datos($second, 'Segunda versión'))->assertOk()->assertJsonPath('revision', $second);
        $this->assertDatabaseCount('evaluaciones_ocr', 2);
        $this->assertDatabaseHas('evaluaciones_ocr', ['id' => $first, 'texto_referencia' => 'Referencia humana']);
    }

    public function test_edicion_desactualizada_devuelve_conflicto_y_conserva_la_version_actual(): void
    {
        $doc = $this->documento();
        $this->actingAs($this->operador());
        $url = '/documentos/'.$doc->uuid.'/referencia';
        $this->postJson($url, $this->datos())->assertOk();
        $this->postJson($url, $this->datos(null, 'Edición desactualizada'))->assertStatus(409);
        $this->assertDatabaseCount('evaluaciones_ocr', 1);
        $this->assertSame('Referencia humana', $doc->evaluaciones()->latest('id')->first()->texto_referencia);
    }

    public function test_referencia_vacia_larga_o_pagina_ajena_se_rechazan(): void
    {
        $doc = $this->documento();
        $this->actingAs($this->operador());
        $url = '/documentos/'.$doc->uuid.'/referencia';
        $this->postJson($url, $this->datos(null, '   '))->assertUnprocessable()->assertJsonValidationErrors('texto_referencia');
        config(['documentos.max_reference_chars' => 10]);
        $this->postJson($url, $this->datos(null, str_repeat('a', 11)))->assertUnprocessable();
        $data = $this->datos(null, 'Valida');
        $data['numero_pagina'] = 99;
        $this->postJson($url, $data)->assertNotFound();
        $this->assertDatabaseCount('evaluaciones_ocr', 0);
    }

    public function test_documento_pendiente_no_admite_referencia_ni_preview(): void
    {
        $doc = $this->documento();
        $doc->update(['estado_procesamiento' => 'pendiente']);
        $this->actingAs($this->operador());
        $this->get('/documentos/'.$doc->uuid.'/revision')->assertOk()->assertSee('cuando termine la extracción');
        $this->get('/documentos/'.$doc->uuid.'/original')->assertStatus(409);
        $this->get('/documentos/'.$doc->uuid.'/texto')->assertStatus(409);
        $this->postJson('/documentos/'.$doc->uuid.'/referencia', $this->datos())->assertStatus(409);
        $this->assertDatabaseCount('evaluaciones_ocr', 0);
    }

    public function test_texto_completo_conserva_orden_y_escapa_html(): void
    {
        $doc = $this->documento('pdf', '<b>Original</b>');
        $this->actingAs($this->operador())->get('/documentos/'.$doc->uuid.'/texto')->assertOk()
            ->assertSeeInOrder(['Página 1', 'Página 2'])->assertDontSee('<b>Original</b>', false)->assertSee('&lt;b&gt;Original&lt;/b&gt;', false);
    }

    public function test_historial_y_referencias_globales_preexistentes_se_conservan(): void
    {
        $doc = $this->documento();
        $doc->evaluaciones()->create(['numero_pagina' => null, 'texto_referencia' => 'Referencia de documento']);
        $this->actingAs($this->operador())->postJson('/documentos/'.$doc->uuid.'/referencia', $this->datos())->assertOk();
        $this->assertDatabaseCount('evaluaciones_ocr', 2);
        $this->get('/documentos/'.$doc->uuid.'/revision')->assertOk()->assertSee('Historial de referencias')->assertSee('Referencia humana');
        $this->assertDatabaseHas('evaluaciones_ocr', ['documento_id' => $doc->id, 'numero_pagina' => null, 'texto_referencia' => 'Referencia de documento']);
    }

    public function test_revision_conserva_ocr_completo_y_explica_alcance_de_la_referencia(): void
    {
        $doc = $this->documento();
        $page = $doc->extracciones()->firstOrFail();
        $page->variantes_ocr = [['modo' => 'preprocesado', 'texto' => $page->texto_extraido, 'duracion_ms' => 1, 'operaciones' => [],
            'alcance' => 'contenido_principal', 'texto_pagina_completa' => 'Membrete y sello conservados <script>sin ejecutar</script>',
            'exclusiones' => ['Pie de contacto separado']]];
        $page->save();
        $this->actingAs($this->operador())->get('/documentos/'.$doc->uuid.'/revision')->assertOk()
            ->assertSee('contenido principal del oficio')->assertSee('OCR de página completa')
            ->assertSee('Pie de contacto separado')->assertSee('&lt;script&gt;', false)
            ->assertSee('La referencia debe abarcar las mismas zonas');
    }

    public function test_pagina_recuperada_muestra_su_lectura_inicial_sin_indicar_recorte(): void
    {
        $doc = $this->documento();
        $page = $doc->extracciones()->firstOrFail();
        $page->variantes_ocr = [['modo' => 'preprocesado', 'texto' => $page->texto_extraido, 'duracion_ms' => 1, 'operaciones' => [],
            'alcance' => 'pagina_completa', 'texto_lectura_inicial' => 'Lectura incompleta <script>sin ejecutar</script>', 'exclusiones' => []]];
        $page->save();
        $this->actingAs($this->operador())->get('/documentos/'.$doc->uuid.'/revision')->assertOk()
            ->assertSee('Lectura inicial antes de recuperar zonas sin transcribir')->assertSee('&lt;script&gt;', false)
            ->assertDontSee('Se muestra el contenido principal del oficio.');
    }

    public function test_formulario_sin_javascript_guarda_y_redirige_a_la_pagina(): void
    {
        $doc = $this->documento();
        $data = $this->datos();
        $data['numero_pagina'] = 2;
        $this->actingAs($this->operador())->post('/documentos/'.$doc->uuid.'/referencia', $data)
            ->assertRedirect('/documentos/'.$doc->uuid.'/revision?pagina=2')->assertSessionHas('status');
        $this->assertDatabaseHas('evaluaciones_ocr', ['documento_id' => $doc->id, 'numero_pagina' => 2]);
    }
}
