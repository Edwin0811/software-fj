# Software FJ – Sistema de Gestión de Clientes, Servicios y Reservas

**Curso:** Programación (213023) – UNAD · **Fase 4:** Componente práctico – Prácticas simuladas
**Grupo:** 213023_561 · **Tutor:** Manuel Mejía Muñoz

Aplicación en Python, orientada a objetos y **sin base de datos**, que administra los clientes, servicios y reservas de la empresa ficticia *Software FJ* (reserva de salas, alquiler de equipos y asesorías especializadas). Su objetivo es **no detenerse nunca**: todos los errores se controlan con excepciones y quedan registrados en un archivo de logs.

## Cómo ejecutarlo

```bash
python software_fj.py          # corre la simulación de 23 operaciones
```

También se puede abrir `software_fj.ipynb` en Jupyter / VS Code / Google Colab y ejecutar las celdas en orden.
Al terminar se genera `software_fj.log` con todos los eventos (INFO / WARNING) y errores (ERROR).

## Arquitectura

| Clase | Tipo | Responsabilidad |
|---|---|---|
| `EntidadBase` | Abstracta (ABC) | id único consecutivo (`CLI-001`, `RES-003`…), fecha de creación, `describir()` abstracto |
| `Cliente` | Hereda de `EntidadBase` | Datos personales **privados** con `@property` y validación de nombre, documento, correo y celular |
| `Servicio` | Abstracta | Tarifa, disponibilidad, descuentos, `calcular_costo()` y métodos abstractos `validar_parametros()` y `_costo_base()` |
| `ReservaSala` | Hereda de `Servicio` | Cobro por horas (1–12) con recargo de 15 % para salas de más de 10 personas |
| `AlquilerEquipo` | Hereda de `Servicio` | Cobro por días (1–30) × cantidad + seguro de 5 % |
| `Asesoria` | Hereda de `Servicio` | Cobro por horas (1–8); nivel experto +50 % |
| `Reserva` | Hereda de `EntidadBase` | Une cliente + servicio + duración; estados PENDIENTE / CONFIRMADA / CANCELADA; `confirmar()`, `cancelar()`, `procesar()` |
| `GestorSoftwareFJ` | Clase de control | Listas internas de clientes, servicios y reservas |

### Polimorfismo y sobrecarga
- Cada servicio **sobrescribe** `validar_parametros()`, `_costo_base()` y `describir()`.
- `calcular_costo(duracion, impuesto=None, descuento=None)`: varias formas de llamarlo (con IVA, sin IVA, con descuento puntual).
- `aplicar_descuento()` con `@singledispatchmethod`: acepta un **float** (`0.15`) o un **str** con código promocional (`"UNAD10"`).

### Manejo de excepciones
Jerarquía propia con base `SoftwareFJError` (con código de error):

```
SoftwareFJError
├── ParametroFaltanteError      FJ-001
├── ClienteInvalidoError        FJ-100
├── ServicioInvalidoError       FJ-200
├── ServicioNoDisponibleError   FJ-201
├── CalculoInconsistenteError   FJ-300
├── ReservaInvalidaError        FJ-400
└── OperacionNoPermitidaError   FJ-500
```

| Técnica | Dónde |
|---|---|
| `try / except` | `ejecutar()` captura cada operación de la simulación |
| `try / except / else` | `Reserva.confirmar()` solo confirma si el cálculo no falló |
| `try / except / finally` | `Reserva.procesar()` siempre deja el resultado en el log |
| Encadenamiento `raise … from` | `Reserva.confirmar()` y `GestorSoftwareFJ.crear_servicio()` (el error original queda en `__cause__`) |
| Logging | `logging` → `software_fj.log` |

## Simulación (23 operaciones)
Clientes válidos e inválidos (correo mal escrito, parámetro faltante, documento repetido), servicios bien y mal creados (tarifa negativa, tipo inexistente, argumento extra), descuentos válidos y excesivos, cotizaciones con sobrecarga, reservas exitosas y fallidas (duración fuera de rango, cliente inexistente, servicio deshabilitado, duración no numérica) y cancelaciones no permitidas.

## Referencias
- Van Rossum, G., & Drake Jr, F. L. (2024). *El tutorial de Python*. Python Software Foundation. https://docs.python.org/es/3.12/tutorial/errors.html
- Cuevas Álvarez, A. (2016). *Python 3: curso práctico*. RA-MA Editorial.
