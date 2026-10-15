<?php

return [
    'processor_url' => env('PROCESSOR_URL', 'http://127.0.0.1:8002'),
    'processor_token' => env('PROCESSOR_API_TOKEN', ''),
    'http_timeout' => (int) env('PROCESSOR_HTTP_TIMEOUT', 170),
    'job_timeout' => (int) env('PROCESSOR_JOB_TIMEOUT', 210),
    'max_response_bytes' => (int) env('PROCESSOR_MAX_RESPONSE_BYTES', 62914560),
    'max_pdf_bytes' => (int) env('DOCUMENTOS_MAX_PDF_BYTES', 41943040),
    'max_reference_chars' => (int) env('DOCUMENTOS_MAX_REFERENCE_CHARS', 200000),
    'max_upload_kb' => (int) env('DOCUMENTOS_MAX_UPLOAD_KB', 20480),
    'max_image_pixels' => (int) env('DOCUMENTOS_MAX_IMAGE_PIXELS', 25000000),
];
