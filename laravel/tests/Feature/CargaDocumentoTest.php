<?php

namespace Tests\Feature;

use App\Models\DocumentoPrueba;
use App\Models\EvaluacionOcr;
use App\Models\ExtraccionDocumento;
use App\Models\User;
use Illuminate\Foundation\Testing\RefreshDatabase;
use Illuminate\Http\UploadedFile;
use Illuminate\Support\Facades\Queue;
use Illuminate\Support\Facades\Storage;
use Illuminate\Support\Str;
use PHPUnit\Framework\Attributes\DataProvider;
use Tests\TestCase;

class CargaDocumentoTest extends TestCase
{
    use RefreshDatabase;

    protected function setUp(): void
    {
        parent::setUp();
        Storage::fake('documentos');
        Queue::fake();
    }

    private function operador(): User
    {
        return User::create(['name' => 'Operador de prueba', 'email' => Str::uuid().'@example.test', 'password' => 'clave-de-prueba-segura']);
    }

    public static function imagenes(): array
    {
        return [['png'], ['jpg'], ['jpeg']];
    }

    #[DataProvider('imagenes')]
    public function test_guarda_imagen_real_y_metadatos_sin_exponer_original(string $extension): void
    {
        $image = imagecreatetruecolor(40, 40);
        ob_start();
        $extension === 'png' ? imagepng($image) : imagejpeg($image);
        $bytes = ob_get_clean();
        imagedestroy($image);
        $response = $this->actingAs($this->operador())->postJson('/documentos', [
            'archivo' => UploadedFile::fake()->createWithContent('oficio.'.$extension, $bytes),
            'ruta_privada' => '../../public/malicioso.php', 'estado_procesamiento' => 'completado',
        ]);
        $response->assertCreated()->assertJsonPath('estado', 'pendiente');
        $doc = DocumentoPrueba::firstOrFail();
        $this->assertTrue(Str::isUuid($doc->uuid));
        $this->assertSame(hash('sha256', $bytes), $doc->hash_sha256);
        $this->assertSame(strlen($bytes), $doc->tamano_bytes);
        $this->assertSame(1, $doc->numero_paginas);
        $this->assertStringStartsWith('originales/'.$doc->uuid, $doc->ruta_privada);
        Storage::disk('documentos')->assertExists($doc->ruta_privada);
        $this->assertSame($bytes, Storage::disk('documentos')->get($doc->ruta_privada));
        $response->assertJsonMissingPath('ruta_privada');
        $this->get('/storage/'.$doc->ruta_privada)->assertNotFound();
        $this->get('/documentos')->assertOk()->assertSee('oficio.'.$extension);
    }

    private function pdf(): string
    {
        $pdf = "%PDF-1.4\n";
        $objects = [
            '<< /Type /Catalog /Pages 2 0 R >>',
            '<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
            '<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 300] /Contents 4 0 R >>',
            "<< /Length 0 >>\nstream\n\nendstream",
        ];
        $offsets = [];
        foreach ($objects as $i => $object) {
            $offsets[] = strlen($pdf);
            $pdf .= ($i + 1)." 0 obj\n".$object."\nendobj\n";
        }
        $xref = strlen($pdf);
        $pdf .= "xref\n0 5\n0000000000 65535 f \n";
        foreach ($offsets as $offset) {
            $pdf .= sprintf("%010d 00000 n \n", $offset);
        }

        return $pdf."trailer\n<< /Size 5 /Root 1 0 R >>\nstartxref\n".$xref."\n%%EOF\n";
    }

    public function test_carga_pdf_real_de_una_pagina_sin_inventar_extraccion(): void
    {
        $this->actingAs($this->operador())->postJson('/documentos', [
            'archivo' => UploadedFile::fake()->createWithContent('pagina.pdf', $this->pdf()),
        ])->assertCreated();
        $this->assertNull(DocumentoPrueba::firstOrFail()->numero_paginas);
        $this->assertDatabaseCount('extracciones_documento', 0);
    }

    public function test_rechaza_archivo_ejecutable_renombrado_y_pdf_truncado(): void
    {
        $this->actingAs($this->operador());
        foreach (['<?php echo 1;', "%PDF-1.4\ntruncado"] as $bytes) {
            $this->postJson('/documentos', ['archivo' => UploadedFile::fake()->createWithContent('falso.pdf', $bytes)])
                ->assertUnprocessable()->assertJsonValidationErrors('archivo');
        }
        $this->assertDatabaseCount('documentos_prueba', 0);
        $this->assertCount(0, Storage::disk('documentos')->allFiles());
    }

    public function test_rechaza_extension_incompatible_tamano_y_demasiados_pixeles(): void
    {
        $this->actingAs($this->operador());
        $this->postJson('/documentos', ['archivo' => UploadedFile::fake()->image('imagen.pdf')])->assertUnprocessable();
        config(['documentos.max_upload_kb' => 1]);
        $this->postJson('/documentos', ['archivo' => UploadedFile::fake()->create('grande.pdf', 2, 'application/pdf')])->assertUnprocessable();
        config(['documentos.max_upload_kb' => 20480, 'documentos.max_image_pixels' => 10]);
        $this->postJson('/documentos', ['archivo' => UploadedFile::fake()->image('grande.png', 20, 20)])->assertUnprocessable();
        $this->assertDatabaseCount('documentos_prueba', 0);
    }

    public function test_limpia_solo_el_nuevo_archivo_si_falla_la_base(): void
    {
        Storage::disk('documentos')->put('existente.txt', 'conservar');
        DocumentoPrueba::creating(function () {
            throw new \RuntimeException('Fallo simulado de escritura');
        });
        try {
            $this->actingAs($this->operador())->postJson('/documentos', [
                'archivo' => UploadedFile::fake()->createWithContent('pagina.pdf', $this->pdf()),
            ])->assertStatus(503);
            $this->assertSame(['existente.txt'], Storage::disk('documentos')->allFiles());
            $this->assertDatabaseCount('documentos_prueba', 0);
        } finally {
            DocumentoPrueba::flushEventListeners();
        }
    }

    public function test_rutas_del_modulo_exigen_autenticacion(): void
    {
        $this->get('/documentos')->assertRedirect('/ingresar');
        $this->postJson('/documentos')->assertUnauthorized();
        $this->get('/ingresar')->assertOk()->assertSee('Correo electrónico');
    }

    public function test_login_regenera_sesion_y_logout_revoca_acceso(): void
    {
        $user = $this->operador();
        $this->post('/ingresar', ['email' => $user->email, 'password' => 'incorrecta'])->assertSessionHasErrors('email');
        $this->post('/ingresar', ['email' => $user->email, 'password' => 'clave-de-prueba-segura'])->assertRedirect('/documentos');
        $this->assertAuthenticatedAs($user);
        $this->get('/documentos')->assertOk();
        $this->post('/salir')->assertRedirect('/ingresar');
        $this->assertGuest();
        $this->get('/documentos')->assertRedirect('/ingresar');
    }

    public function test_limita_intentos_de_login(): void
    {
        for ($i = 0; $i < 5; $i++) {
            $this->postJson('/ingresar', ['email' => 'nadie@example.test', 'password' => 'incorrecta'])->assertUnprocessable();
        }
        $this->postJson('/ingresar', ['email' => 'nadie@example.test', 'password' => 'incorrecta'])->assertStatus(429);
    }

    public function test_relaciones_conservan_extraccion_y_referencia_separadas(): void
    {
        $doc = DocumentoPrueba::create([
            'uuid' => Str::uuid(), 'nombre_original' => 'prueba.pdf', 'tipo_archivo' => 'pdf',
            'tamano_bytes' => 10, 'hash_sha256' => str_repeat('a', 64), 'ruta_privada' => 'originales/prueba.pdf',
            'estado_procesamiento' => 'pendiente', 'fecha_carga' => now(),
        ]);
        $extraction = $doc->extracciones()->create(['numero_pagina' => 1, 'metodo_extraccion' => 'digital', 'texto_extraido' => 'original', 'duracion_ms' => 1]);
        $evaluation = $doc->evaluaciones()->create(['numero_pagina' => 1, 'texto_referencia' => 'corregido']);
        $evaluation->update(['texto_referencia' => 'otra referencia']);
        $this->assertSame('original', $extraction->fresh()->texto_extraido);
        $this->assertSame($doc->id, ExtraccionDocumento::first()->documento->id);
        $this->assertSame($doc->id, EvaluacionOcr::first()->documento->id);
    }
}
