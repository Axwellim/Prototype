<?php

namespace App\Console\Commands;

use Illuminate\Console\Command;
use Illuminate\Support\Facades\DB;

class TrabajarDocumentos extends Command
{
    protected $signature = 'documentos:trabajar {--once : Procesa una tarea y termina} {--stop-when-empty : Termina cuando se vacía la cola}';

    protected $description = 'Ejecuta un único trabajador OCR con exclusión en PostgreSQL';

    public function handle(): int
    {
        if (DB::getDriverName() !== 'pgsql') {
            $this->error('Este trabajador requiere PostgreSQL.');

            return self::FAILURE;
        }
        $http = (int) config('documentos.http_timeout');
        $timeout = (int) config('documentos.job_timeout');
        $retry = (int) config('queue.connections.documentos.retry_after');
        if ($http < 1 || $timeout <= $http + 15 || $retry <= $timeout + 60) {
            $this->error('Configura HTTP timeout + 15 < job timeout y job timeout + 60 < retry_after.');

            return self::FAILURE;
        }
        if (! DB::selectOne('SELECT pg_try_advisory_lock(758198) AS acquired')->acquired) {
            $this->error('Ya existe un trabajador documental activo.');

            return self::FAILURE;
        }
        try {
            $queue = (string) config('queue.connections.documentos.queue', 'ocr');
            $this->info('Trabajador documental activo; cola PostgreSQL '.$queue.'. Ctrl+C para detener.');

            return $this->call('queue:work', ['connection' => 'documentos', '--queue' => $queue, '--sleep' => 2,
                '--tries' => 50, '--timeout' => $timeout, '--memory' => 256,
                '--once' => (bool) $this->option('once'), '--stop-when-empty' => (bool) $this->option('stop-when-empty')]);
        } finally {
            DB::select('SELECT pg_advisory_unlock(758198)');
        }
    }
}
