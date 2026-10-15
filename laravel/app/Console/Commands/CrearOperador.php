<?php

namespace App\Console\Commands;

use App\Models\User;
use Illuminate\Console\Command;
use Illuminate\Support\Facades\Validator;

class CrearOperador extends Command
{
    protected $signature = 'documentos:crear-operador';

    protected $description = 'Crea un operador local sin registro público';

    public function handle(): int
    {
        $name = $this->ask('Nombre del operador');
        $email = $this->ask('Correo del operador');
        $password = $this->secret('Contraseña (mínimo 12 caracteres)');
        $confirmation = $this->secret('Repite la contraseña');
        $validator = Validator::make(
            ['name' => $name, 'email' => $email, 'password' => $password, 'password_confirmation' => $confirmation],
            ['name' => 'required|string|max:255', 'email' => 'required|email|max:255|unique:users,email', 'password' => 'required|string|min:12|max:128|confirmed']
        );
        if ($validator->fails()) {
            $this->error('Verifica nombre, correo único y contraseña de al menos 12 caracteres, repetida correctamente.');

            return self::FAILURE;
        }
        User::create(['name' => $name, 'email' => $email, 'password' => $password]);
        $this->info('Operador creado. Ya puedes ingresar desde el navegador.');

        return self::SUCCESS;
    }
}
