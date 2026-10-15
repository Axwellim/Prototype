<?php

namespace Tests\Feature;

use Tests\TestCase;

class ExampleTest extends TestCase
{
    public function test_la_raiz_dirige_al_modulo_protegido(): void
    {
        $this->get('/')->assertRedirect('/documentos');
    }
}
