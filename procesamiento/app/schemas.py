from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class OcrVariant(BaseModel):
    model_config = ConfigDict(extra='forbid')
    modo: Literal['original', 'preprocesado']
    texto: str
    duracion_ms: int = Field(ge=0)
    operaciones: list[str] = Field(default_factory=list)
    texto_pagina_completa: str | None = None
    texto_lectura_inicial: str | None = None
    alcance: Literal['pagina_completa', 'contenido_principal'] = 'pagina_completa'
    exclusiones: list[str] = Field(default_factory=list)


class PageResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    numero: int = Field(ge=1)
    metodo: Literal['digital', 'requiere_ocr', 'ocr', 'sin_transcripcion']
    texto: str
    duracion_ms: int = Field(ge=0)
    observaciones: list[str] = Field(default_factory=list)
    texto_digital: str | None = None
    variantes_ocr: list[OcrVariant] = Field(default_factory=list)


    @model_validator(mode='after')
    def consistent_ocr(self):
        if self.metodo == 'ocr':
            if not self.variantes_ocr or self.texto != self.variantes_ocr[0].texto:
                raise ValueError('El texto principal debe coincidir con la primera variante OCR.')
        elif self.variantes_ocr:
            raise ValueError('Una página sin OCR no debe contener variantes OCR.')
        if self.metodo == 'sin_transcripcion' and (self.texto or self.texto_digital):
            raise ValueError('Una invitación no debe contener transcripción.')
        return self


class ProcessingResult(BaseModel):
    model_config = ConfigDict(extra='forbid')
    estado: Literal['completado', 'requiere_ocr']
    numero_paginas: int = Field(ge=1)
    duracion_total_ms: int = Field(ge=0)
    paginas: list[PageResult]
    texto_completo: str
    invitacion_paginas: int | None = Field(default=None, ge=1)
    componentes_paginas: list[int] | None = None

    @model_validator(mode='after')
    def consistent_pages(self):
        if self.componentes_paginas is not None and (not 1 <= len(self.componentes_paginas) <= 19
                or any(count < 1 for count in self.componentes_paginas)
                or sum(self.componentes_paginas) != self.numero_paginas):
            raise ValueError('Las páginas de los componentes no coinciden con el documento.')
        if [page.numero for page in self.paginas] != list(range(1, self.numero_paginas + 1)):
            raise ValueError('La numeración de páginas no es consistente.')
        needs_ocr = any(page.metodo == 'requiere_ocr' for page in self.paginas)
        if (self.estado == 'requiere_ocr') != needs_ocr:
            raise ValueError('El estado no coincide con los resultados de páginas.')
        if self.texto_completo != '\f'.join(page.texto for page in self.paginas):
            raise ValueError('El texto completo no coincide con las páginas.')
        return self
