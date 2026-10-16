<?php

use App\Http\Controllers\CalidadDocumentoController;
use App\Http\Controllers\DocumentoController;
use App\Http\Controllers\RevisionDocumentoController;
use App\Http\Controllers\SesionController;
use Illuminate\Support\Facades\Route;

Route::redirect('/', '/documentos');
Route::middleware('guest')->group(function () {
    Route::get('/ingresar', [SesionController::class, 'create'])->name('login');
    Route::post('/ingresar', [SesionController::class, 'store'])->middleware('throttle:5,1')->name('login.store');
});
Route::middleware('auth')->group(function () {
    Route::post('/documentos/{documento}/calidad', [CalidadDocumentoController::class, 'store'])->middleware('throttle:10,1')->name('documentos.calidad');
    Route::post('/salir', [SesionController::class, 'destroy'])->name('logout');
    Route::get('/documentos/estados', [DocumentoController::class, 'estados'])->name('documentos.estados');
    Route::post('/documentos/{documento}/reintentar', [DocumentoController::class, 'reintentar'])->middleware('throttle:20,1')->name('documentos.reintentar');
    Route::get('/documentos/{documento}/revision', [RevisionDocumentoController::class, 'show'])->name('documentos.revision');
    Route::get('/documentos/{documento}/original', [RevisionDocumentoController::class, 'original'])->name('documentos.original');
    Route::get('/documentos/{documento}/invitacion', [RevisionDocumentoController::class, 'invitacion'])->name('documentos.invitacion');
    Route::get('/documentos/{documento}/pdf', [RevisionDocumentoController::class, 'pdf'])->name('documentos.pdf');
    Route::get('/documentos/{documento}/texto', [RevisionDocumentoController::class, 'texto'])->name('documentos.texto');
    Route::post('/documentos/{documento}/referencia', [RevisionDocumentoController::class, 'guardar'])->middleware('throttle:60,1')->name('documentos.referencia');
    Route::get('/documentos', [DocumentoController::class, 'index'])->name('documentos.index');
    Route::post('/documentos', [DocumentoController::class, 'store'])->middleware('throttle:20,1')->name('documentos.store');
    Route::delete('/documentos/{documento}', [DocumentoController::class, 'destroy'])->middleware('throttle:20,1')->name('documentos.destroy');
});
