<?php
// Suite destructiva solo para la base dedicada imantag_documental_test.
$root = dirname(__DIR__).'/laravel';
require $root.'/vendor/autoload.php';
$values = Dotenv\Dotenv::parse(file_get_contents($root.'/.env'));
foreach (['DB_HOST', 'DB_PORT', 'DB_USERNAME', 'DB_PASSWORD'] as $key) {
    $value = $values[$key] ?? '';
    putenv($key.'='.$value); $_ENV[$key] = $_SERVER[$key] = $value;
}
foreach (['APP_ENV' => 'testing', 'DB_CONNECTION' => 'pgsql', 'DB_DATABASE' => 'imantag_documental_test', 'DB_URL' => ''] as $key => $value) {
    putenv($key.'='.$value); $_ENV[$key] = $_SERVER[$key] = $value;
}
$pdo = new PDO('pgsql:host='.getenv('DB_HOST').';port='.getenv('DB_PORT').';dbname=imantag_documental_test', getenv('DB_USERNAME'), getenv('DB_PASSWORD'));
if ($pdo->query('SELECT current_database()')->fetchColumn() !== 'imantag_documental_test') { throw new RuntimeException('Base de pruebas incorrecta'); }
chdir($root);
exit((new PHPUnit\TextUI\Application)->run(['phpunit', '--configuration', $root.'/phpunit.xml']));
