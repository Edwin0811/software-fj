"""
Sistema Integral de Gestión de Clientes, Servicios y Reservas - Software FJ
--------------------------------------------------------------------------
Curso : Programación (213023) - UNAD - Fase 4: Componente práctico
Autora: Jennyfer Paola Fernández Tierradentro - Grupo 213023_561

El sistema administra clientes, servicios (reserva de salas, alquiler de
equipos y asesorías) y reservas usando solo objetos y listas en memoria,
sin base de datos. El archivo de logs registra los eventos y los errores.

Conceptos aplicados:
- Abstracción ........ EntidadBase y Servicio son clases abstractas (ABC).
- Herencia ........... Cliente, Reserva y los 3 servicios heredan de ellas.
- Polimorfismo ....... cada servicio calcula su costo y se describe distinto.
- Encapsulación ...... atributos privados con @property y setters validados.
- Sobrecarga ......... calcular_costo() con parámetros opcionales y
                       aplicar_descuento() con @singledispatchmethod (por tipo).
- Excepciones ........ jerarquía propia, try/except, try/except/else,
                       try/except/finally y encadenamiento (raise ... from).
"""

import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime
from functools import singledispatchmethod

# ======================================================================
# 1. CONFIGURACIÓN DEL ARCHIVO DE LOGS
# ======================================================================
ARCHIVO_LOG = "software_fj.log"

logger = logging.getLogger("software_fj")          # logger propio del sistema
logger.setLevel(logging.INFO)                       # registra INFO, WARNING y ERROR
if not logger.handlers:                             # evita duplicar handlers si se importa dos veces
    _manejador = logging.FileHandler(ARCHIVO_LOG, encoding="utf-8")
    _manejador.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s", "%Y-%m-%d %H:%M:%S"))
    logger.addHandler(_manejador)


# ======================================================================
# 2. EXCEPCIONES PERSONALIZADAS
# ======================================================================
class SoftwareFJError(Exception):
    """Excepción base de todo el sistema. Todas las demás heredan de esta."""

    def __init__(self, mensaje, codigo="FJ-000"):
        super().__init__(mensaje)          # guarda el mensaje como cualquier Exception
        self.codigo = codigo               # código corto para identificar el error en el log

    def __str__(self):
        return f"[{self.codigo}] {self.args[0]}"


class ParametroFaltanteError(SoftwareFJError):
    """Falta un dato obligatorio para crear un objeto u operar."""

    def __init__(self, parametro):
        super().__init__(f"Falta el parámetro obligatorio '{parametro}'.", "FJ-001")


class ClienteInvalidoError(SoftwareFJError):
    """Los datos personales del cliente no pasan las validaciones."""

    def __init__(self, mensaje):
        super().__init__(mensaje, "FJ-100")


class ServicioInvalidoError(SoftwareFJError):
    """El servicio se intentó crear o usar con parámetros incorrectos."""

    def __init__(self, mensaje):
        super().__init__(mensaje, "FJ-200")


class ServicioNoDisponibleError(SoftwareFJError):
    """El servicio existe pero está deshabilitado en este momento."""

    def __init__(self, nombre):
        super().__init__(f"El servicio '{nombre}' no está disponible.", "FJ-201")


class CalculoInconsistenteError(SoftwareFJError):
    """El costo calculado no tiene sentido (negativo, cero o descuento excesivo)."""

    def __init__(self, mensaje):
        super().__init__(mensaje, "FJ-300")


class ReservaInvalidaError(SoftwareFJError):
    """La reserva no se pudo crear o procesar."""

    def __init__(self, mensaje):
        super().__init__(mensaje, "FJ-400")


class OperacionNoPermitidaError(SoftwareFJError):
    """La operación no es válida para el estado actual del objeto."""

    def __init__(self, mensaje):
        super().__init__(mensaje, "FJ-500")


# ======================================================================
# 3. CLASE ABSTRACTA GENERAL
# ======================================================================
class EntidadBase(ABC):
    """Representa cualquier entidad del sistema: tiene un id único y fecha de creación."""

    _consecutivos = {}                                   # contador de ids por tipo de entidad

    def __init__(self, prefijo):
        numero = EntidadBase._consecutivos.get(prefijo, 0) + 1
        EntidadBase._consecutivos[prefijo] = numero       # actualiza el consecutivo del prefijo
        self.__id = f"{prefijo}-{numero:03d}"            # ej: CLI-001, SAL-002, RES-010
        self.__creado = datetime.now()

    @property
    def id(self):
        return self.__id                                 # solo lectura: no tiene setter

    @property
    def creado(self):
        return self.__creado

    @abstractmethod
    def describir(self):
        """Cada entidad debe saber describirse (polimorfismo)."""

    def __str__(self):
        return f"{self.id}: {self.describir()}"


# ======================================================================
# 4. CLIENTE (encapsulación y validaciones robustas)
# ======================================================================
class Cliente(EntidadBase):
    PATRON_CORREO = re.compile(r"^[\w.+-]+@[\w-]+(\.[\w-]+)+$")

    def __init__(self, nombre, documento, correo, telefono):
        super().__init__("CLI")
        # Se asigna por medio de los setters para que TODO pase por validación
        self.nombre = nombre
        self.documento = documento
        self.correo = correo
        self.telefono = telefono

    # --- nombre ---
    @property
    def nombre(self):
        return self.__nombre

    @nombre.setter
    def nombre(self, valor):
        if not isinstance(valor, str) or len(valor.strip()) < 3:
            raise ClienteInvalidoError("El nombre debe tener al menos 3 caracteres.")
        if any(c.isdigit() for c in valor):
            raise ClienteInvalidoError(f"El nombre '{valor}' no puede contener números.")
        self.__nombre = valor.strip().title()

    # --- documento ---
    @property
    def documento(self):
        return self.__documento

    @documento.setter
    def documento(self, valor):
        valor = str(valor).strip()
        if not valor.isdigit() or not 6 <= len(valor) <= 10:
            raise ClienteInvalidoError(f"Documento '{valor}' inválido: deben ser 6 a 10 dígitos.")
        self.__documento = valor

    # --- correo ---
    @property
    def correo(self):
        return self.__correo

    @correo.setter
    def correo(self, valor):
        if not isinstance(valor, str) or not Cliente.PATRON_CORREO.match(valor.strip()):
            raise ClienteInvalidoError(f"Correo '{valor}' con formato inválido.")
        self.__correo = valor.strip().lower()

    # --- teléfono ---
    @property
    def telefono(self):
        return self.__telefono

    @telefono.setter
    def telefono(self, valor):
        valor = str(valor).replace(" ", "")
        if not (valor.isdigit() and len(valor) == 10 and valor.startswith("3")):
            raise ClienteInvalidoError(f"Teléfono '{valor}' inválido: celular de 10 dígitos que empiece por 3.")
        self.__telefono = valor

    def describir(self):
        # El documento se muestra enmascarado para proteger el dato personal
        return f"Cliente {self.nombre} (doc. ****{self.documento[-3:]}, {self.correo})"


# ======================================================================
# 5. SERVICIO ABSTRACTO Y SERVICIOS ESPECIALIZADOS
# ======================================================================
class Servicio(EntidadBase, ABC):
    IVA = 0.19                                           # impuesto por defecto en Colombia

    def __init__(self, prefijo, nombre, tarifa_base):
        super().__init__(prefijo)
        if not nombre or not str(nombre).strip():
            raise ServicioInvalidoError("El servicio debe tener nombre.")
        if not isinstance(tarifa_base, (int, float)) or isinstance(tarifa_base, bool) or tarifa_base <= 0:
            raise ServicioInvalidoError(f"Tarifa base inválida para '{nombre}': {tarifa_base!r}.")
        self._nombre = str(nombre).strip()
        self._tarifa_base = float(tarifa_base)
        self.__disponible = True
        self._descuento = 0.0                            # porcentaje de descuento vigente (0 a 0.5)

    @property
    def nombre(self):
        return self._nombre

    @property
    def disponible(self):
        return self.__disponible

    def deshabilitar(self):
        self.__disponible = False
        logger.warning("Servicio %s (%s) deshabilitado.", self.id, self.nombre)

    def habilitar(self):
        self.__disponible = True
        logger.info("Servicio %s (%s) habilitado.", self.id, self.nombre)

    # ---------- métodos abstractos (polimorfismo) ----------
    @abstractmethod
    def validar_parametros(self, duracion):
        """Lanza ServicioInvalidoError si la duración no aplica a este servicio."""

    @abstractmethod
    def _costo_base(self, duracion):
        """Costo sin impuestos ni descuentos; cada servicio lo calcula distinto."""

    # ---------- sobrecarga por parámetros opcionales ----------
    def calcular_costo(self, duracion, impuesto=None, descuento=None):
        """
        Variantes de uso:
          calcular_costo(3)                  -> con IVA y el descuento vigente
          calcular_costo(3, impuesto=0)      -> sin impuesto
          calcular_costo(3, descuento=0.10)  -> con un descuento puntual
        """
        self.validar_parametros(duracion)
        impuesto = Servicio.IVA if impuesto is None else impuesto
        descuento = self._descuento if descuento is None else descuento
        if not 0 <= descuento <= 0.5:
            raise CalculoInconsistenteError(f"Descuento de {descuento:.0%} fuera del rango permitido (0% a 50%).")
        if impuesto < 0:
            raise CalculoInconsistenteError("El impuesto no puede ser negativo.")
        subtotal = self._costo_base(duracion) * (1 - descuento)
        total = round(subtotal * (1 + impuesto), 2)
        if total <= 0:
            raise CalculoInconsistenteError(f"Costo calculado inconsistente: {total}.")
        return total

    # ---------- sobrecarga por tipo de argumento ----------
    @singledispatchmethod
    def aplicar_descuento(self, valor):
        raise CalculoInconsistenteError(f"Tipo de descuento no soportado: {type(valor).__name__}.")

    @aplicar_descuento.register
    def _(self, valor: float):
        """Descuento como porcentaje: aplicar_descuento(0.15)."""
        if not 0 <= valor <= 0.5:
            raise CalculoInconsistenteError(f"Descuento {valor:.0%} fuera de rango (máximo 50%).")
        self._descuento = valor
        logger.info("Descuento de %.0f%% aplicado a %s.", valor * 100, self.id)

    @aplicar_descuento.register
    def _(self, valor: str):
        """Descuento como código promocional: aplicar_descuento('UNAD10')."""
        codigos = {"UNAD10": 0.10, "FJ20": 0.20}
        if valor.upper() not in codigos:
            raise CalculoInconsistenteError(f"Código promocional '{valor}' no existe.")
        self.aplicar_descuento(codigos[valor.upper()])  # reutiliza la versión float

    def _validar_numero(self, valor, minimo, maximo, unidad):
        """Ayuda común: la duración debe ser un entero dentro del rango del servicio."""
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise ServicioInvalidoError(f"La duración debe ser un número entero de {unidad}, no {valor!r}.")
        if not minimo <= valor <= maximo:
            raise ServicioInvalidoError(f"{self.nombre}: la duración debe estar entre {minimo} y {maximo} {unidad}.")


class ReservaSala(Servicio):
    """Alquiler de salas por horas. Más de 10 personas tiene recargo de logística."""

    def __init__(self, nombre, tarifa_hora, capacidad):
        super().__init__("SAL", nombre, tarifa_hora)
        if not isinstance(capacidad, int) or capacidad <= 0:
            raise ServicioInvalidoError(f"Capacidad inválida para la sala '{nombre}'.")
        self.capacidad = capacidad

    def validar_parametros(self, duracion):
        self._validar_numero(duracion, 1, 12, "horas")

    def _costo_base(self, duracion):
        recargo = 1.15 if self.capacidad > 10 else 1.0
        return self._tarifa_base * duracion * recargo

    def describir(self):
        return f"Sala '{self.nombre}' para {self.capacidad} personas - ${self._tarifa_base:,.0f}/hora"


class AlquilerEquipo(Servicio):
    """Alquiler de equipos por días, con un seguro del 5% sobre el valor."""

    def __init__(self, nombre, tarifa_dia, cantidad):
        super().__init__("EQP", nombre, tarifa_dia)
        if not isinstance(cantidad, int) or cantidad <= 0:
            raise ServicioInvalidoError(f"Cantidad de equipos inválida para '{nombre}'.")
        self.cantidad = cantidad

    def validar_parametros(self, duracion):
        self._validar_numero(duracion, 1, 30, "días")

    def _costo_base(self, duracion):
        return self._tarifa_base * duracion * self.cantidad * 1.05

    def describir(self):
        return f"Alquiler de {self.cantidad} x '{self.nombre}' - ${self._tarifa_base:,.0f}/día + seguro 5%"


class Asesoria(Servicio):
    """Asesoría especializada por horas; el nivel experto cuesta 50% más."""

    NIVELES = {"basica": 1.0, "experta": 1.5}

    def __init__(self, nombre, tarifa_hora, nivel="basica"):
        super().__init__("ASE", nombre, tarifa_hora)
        if nivel not in Asesoria.NIVELES:
            raise ServicioInvalidoError(f"Nivel de asesoría '{nivel}' no existe (use basica o experta).")
        self.nivel = nivel

    def validar_parametros(self, duracion):
        self._validar_numero(duracion, 1, 8, "horas")

    def _costo_base(self, duracion):
        return self._tarifa_base * duracion * Asesoria.NIVELES[self.nivel]

    def describir(self):
        return f"Asesoría {self.nivel} en '{self.nombre}' - ${self._tarifa_base:,.0f}/hora"


# ======================================================================
# 6. RESERVA (integra cliente + servicio + duración + estado)
# ======================================================================
class Reserva(EntidadBase):
    PENDIENTE, CONFIRMADA, CANCELADA = "PENDIENTE", "CONFIRMADA", "CANCELADA"

    def __init__(self, cliente, servicio, duracion):
        super().__init__("RES")
        if not isinstance(cliente, Cliente):
            raise ReservaInvalidaError("La reserva necesita un cliente registrado.")
        if not isinstance(servicio, Servicio):
            raise ReservaInvalidaError("La reserva necesita un servicio válido.")
        self.cliente = cliente
        self.servicio = servicio
        self.duracion = duracion
        self.__estado = Reserva.PENDIENTE
        self.costo = None

    @property
    def estado(self):
        return self.__estado

    def confirmar(self):
        """try / except / else: solo se confirma si el cálculo no falló."""
        if self.__estado != Reserva.PENDIENTE:
            raise OperacionNoPermitidaError(f"La reserva {self.id} está {self.__estado} y no se puede confirmar.")
        try:
            if not self.servicio.disponible:
                raise ServicioNoDisponibleError(self.servicio.nombre)
            costo = self.servicio.calcular_costo(self.duracion)
        except (ServicioInvalidoError, ServicioNoDisponibleError, CalculoInconsistenteError) as error:
            # Encadenamiento: el error original queda guardado en __cause__
            raise ReservaInvalidaError(f"No se pudo confirmar {self.id}: {error}") from error
        else:
            self.costo = costo
            self.__estado = Reserva.CONFIRMADA
            logger.info("Reserva %s CONFIRMADA por $%s.", self.id, f"{costo:,.2f}")
            return costo

    def cancelar(self):
        if self.__estado == Reserva.CANCELADA:
            raise OperacionNoPermitidaError(f"La reserva {self.id} ya estaba cancelada.")
        self.__estado = Reserva.CANCELADA
        logger.info("Reserva %s CANCELADA.", self.id)

    def procesar(self):
        """try / except / finally: el finally deja rastro en el log pase lo que pase."""
        resultado = False
        try:
            self.confirmar()
            resultado = True
        except ReservaInvalidaError:
            self.__estado = Reserva.CANCELADA       # una reserva que no se pudo confirmar queda anulada
            raise                                   # se re-lanza para que la maneje el gestor
        finally:
            logger.info("Procesamiento de %s terminado. Exitoso=%s, estado=%s.", self.id, resultado, self.__estado)
        return resultado

    def describir(self):
        costo = f"${self.costo:,.2f}" if self.costo is not None else "sin calcular"
        return f"{self.cliente.nombre} -> {self.servicio.nombre} x{self.duracion} [{self.estado}] {costo}"


# ======================================================================
# 7. GESTOR DEL SISTEMA (listas internas, sin base de datos)
# ======================================================================
class GestorSoftwareFJ:
    TIPOS_SERVICIO = {"sala": ReservaSala, "equipo": AlquilerEquipo, "asesoria": Asesoria}
    CAMPOS = {
        "sala": ("nombre", "tarifa_hora", "capacidad"),
        "equipo": ("nombre", "tarifa_dia", "cantidad"),
        "asesoria": ("nombre", "tarifa_hora"),
    }

    def __init__(self):
        self.clientes = []
        self.servicios = []
        self.reservas = []

    # ---------------- clientes ----------------
    def registrar_cliente(self, **datos):
        for campo in ("nombre", "documento", "correo", "telefono"):
            if campo not in datos:
                raise ParametroFaltanteError(campo)
        if self.buscar_cliente(str(datos["documento"]), lanzar=False):
            raise ClienteInvalidoError(f"Ya existe un cliente con documento {datos['documento']}.")
        cliente = Cliente(**datos)
        self.clientes.append(cliente)
        logger.info("Cliente registrado: %s", cliente)
        return cliente

    def buscar_cliente(self, documento, lanzar=True):
        for c in self.clientes:
            if c.documento == str(documento):
                return c
        if lanzar:
            raise ReservaInvalidaError(f"No hay ningún cliente con documento {documento}.")
        return None

    # ---------------- servicios ----------------
    def crear_servicio(self, tipo, **datos):
        if tipo not in self.TIPOS_SERVICIO:
            raise ServicioInvalidoError(f"Tipo de servicio '{tipo}' no existe.")
        for campo in self.CAMPOS[tipo]:
            if campo not in datos:
                raise ParametroFaltanteError(campo)
        try:
            servicio = self.TIPOS_SERVICIO[tipo](**datos)
        except TypeError as error:
            # Un argumento de más o mal escrito: se traduce a un error propio, encadenado
            raise ServicioInvalidoError(f"Datos no válidos para '{tipo}': {error}") from error
        self.servicios.append(servicio)
        logger.info("Servicio creado: %s", servicio)
        return servicio

    def buscar_servicio(self, id_servicio):
        for s in self.servicios:
            if s.id == id_servicio:
                return s
        raise ReservaInvalidaError(f"El servicio {id_servicio} no existe.")

    # ---------------- reservas ----------------
    def crear_reserva(self, documento, id_servicio, duracion):
        cliente = self.buscar_cliente(documento)
        servicio = self.buscar_servicio(id_servicio)
        reserva = Reserva(cliente, servicio, duracion)
        self.reservas.append(reserva)                  # queda en el historial aunque falle
        reserva.procesar()
        return reserva

    def resumen(self):
        confirmadas = [r for r in self.reservas if r.estado == Reserva.CONFIRMADA]
        total = sum(r.costo for r in confirmadas)
        return (f"Clientes: {len(self.clientes)} | Servicios: {len(self.servicios)} | "
                f"Reservas: {len(self.reservas)} ({len(confirmadas)} confirmadas) | "
                f"Ingresos confirmados: ${total:,.2f}")


# ======================================================================
# 8. SIMULACIÓN DE OPERACIONES (válidas e inválidas)
# ======================================================================
def ejecutar(numero, descripcion, operacion, estadisticas):
    """Ejecuta una operación sin dejar que el programa se detenga nunca."""
    print(f"\n[{numero:02d}] {descripcion}")
    try:
        resultado = operacion()
    except SoftwareFJError as error:
        estadisticas["fallidas"] += 1
        causa = f" | causa original: {error.__cause__}" if error.__cause__ else ""
        print(f"     ✗ ERROR CONTROLADO {error}{causa}")
        logger.error("Operación %02d '%s' falló: %s%s", numero, descripcion, error, causa)
    except Exception as error:                          # red de seguridad para errores no previstos
        estadisticas["fallidas"] += 1
        print(f"     ✗ ERROR INESPERADO ({type(error).__name__}): {error}")
        logger.exception("Error inesperado en la operación %02d", numero)
    else:
        estadisticas["exitosas"] += 1
        print(f"     ✓ OK -> {resultado}")
    finally:
        estadisticas["total"] += 1


def main():
    logger.info("=" * 70)
    logger.info("Inicio de la simulación Software FJ")
    gestor = GestorSoftwareFJ()
    est = {"total": 0, "exitosas": 0, "fallidas": 0}

    print("=" * 72)
    print("  SOFTWARE FJ - Simulación de clientes, servicios y reservas")
    print("=" * 72)

    # ---- Clientes ----
    ejecutar(1, "Registrar cliente válido (Ana María Rojas)",
             lambda: gestor.registrar_cliente(nombre="ana maría rojas", documento="1052334871",
                                              correo="ana.rojas@correo.com", telefono="3104567890"), est)
    ejecutar(2, "Registrar cliente válido (Carlos Pérez)",
             lambda: gestor.registrar_cliente(nombre="Carlos Pérez", documento="80123456",
                                              correo="carlos.perez@empresa.co", telefono="3201112233"), est)
    ejecutar(3, "Registrar cliente con correo inválido",
             lambda: gestor.registrar_cliente(nombre="Luis Gómez", documento="1012345678",
                                              correo="luis.gomez@@correo", telefono="3001234567"), est)
    ejecutar(4, "Registrar cliente sin teléfono (parámetro faltante)",
             lambda: gestor.registrar_cliente(nombre="Marta Díaz", documento="1098765432",
                                              correo="marta@correo.com"), est)
    ejecutar(5, "Registrar cliente con documento repetido",
             lambda: gestor.registrar_cliente(nombre="Ana Rojas", documento="1052334871",
                                              correo="otra@correo.com", telefono="3109998877"), est)

    # ---- Servicios ----
    ejecutar(6, "Crear servicio: Sala de juntas (12 personas)",
             lambda: gestor.crear_servicio("sala", nombre="Sala de Juntas", tarifa_hora=80000, capacidad=12), est)
    ejecutar(7, "Crear servicio: Alquiler de 3 portátiles",
             lambda: gestor.crear_servicio("equipo", nombre="Portátil i7", tarifa_dia=45000, cantidad=3), est)
    ejecutar(8, "Crear servicio: Asesoría experta en ciberseguridad",
             lambda: gestor.crear_servicio("asesoria", nombre="Ciberseguridad", tarifa_hora=120000, nivel="experta"), est)
    ejecutar(9, "Crear servicio con tarifa negativa",
             lambda: gestor.crear_servicio("sala", nombre="Auditorio", tarifa_hora=-5000, capacidad=50), est)
    ejecutar(10, "Crear servicio de tipo inexistente",
             lambda: gestor.crear_servicio("transporte", nombre="Van", tarifa=30000), est)
    ejecutar(11, "Crear servicio con un dato que no corresponde (encadenamiento TypeError)",
             lambda: gestor.crear_servicio("equipo", nombre="Proyector", tarifa_dia=30000, cantidad=1, color="rojo"), est)

    # ---- Descuentos (sobrecarga por tipo) ----
    ejecutar(12, "Aplicar código promocional 'UNAD10' a la asesoría",
             lambda: (gestor.buscar_servicio("ASE-001").aplicar_descuento("UNAD10"), "descuento 10% aplicado")[1], est)
    ejecutar(13, "Aplicar descuento de 80% (excesivo)",
             lambda: gestor.buscar_servicio("SAL-001").aplicar_descuento(0.80), est)

    # ---- Costos (sobrecarga por parámetros opcionales) ----
    ejecutar(14, "Cotizar portátiles 2 días: con IVA, sin IVA y con 15% de descuento",
             lambda: {"con_iva": gestor.buscar_servicio("EQP-001").calcular_costo(2),
                      "sin_iva": gestor.buscar_servicio("EQP-001").calcular_costo(2, impuesto=0),
                      "desc_15": gestor.buscar_servicio("EQP-001").calcular_costo(2, descuento=0.15)}, est)

    # ---- Reservas ----
    ejecutar(15, "Reserva exitosa: Ana - Sala de juntas 3 horas",
             lambda: gestor.crear_reserva("1052334871", "SAL-001", 3), est)
    ejecutar(16, "Reserva exitosa: Carlos - Asesoría 2 horas (con descuento UNAD10)",
             lambda: gestor.crear_reserva("80123456", "ASE-001", 2), est)
    ejecutar(17, "Reserva fallida: duración fuera de rango (40 días de portátiles)",
             lambda: gestor.crear_reserva("80123456", "EQP-001", 40), est)
    ejecutar(18, "Reserva fallida: cliente inexistente",
             lambda: gestor.crear_reserva("99999999", "SAL-001", 2), est)

    def reservar_servicio_deshabilitado():
        gestor.buscar_servicio("EQP-001").deshabilitar()
        return gestor.crear_reserva("1052334871", "EQP-001", 2)
    ejecutar(19, "Reserva fallida: servicio no disponible (portátiles deshabilitados)",
             reservar_servicio_deshabilitado, est)
    ejecutar(20, "Reserva fallida: duración no numérica ('tres')",
             lambda: gestor.crear_reserva("1052334871", "ASE-001", "tres"), est)

    # ---- Cancelaciones ----
    ejecutar(21, "Cancelar la reserva RES-001",
             lambda: (gestor.reservas[0].cancelar(), gestor.reservas[0])[1], est)
    ejecutar(22, "Cancelar otra vez RES-001 (operación no permitida)",
             lambda: gestor.reservas[0].cancelar(), est)
    ejecutar(23, "Confirmar una reserva ya cancelada (operación no permitida)",
             lambda: gestor.reservas[0].confirmar(), est)

    # ---- Resumen ----
    print("\n" + "=" * 72)
    print("  RESUMEN DE LA SIMULACIÓN")
    print("=" * 72)
    print(f"  Operaciones: {est['total']} | Exitosas: {est['exitosas']} | Fallidas controladas: {est['fallidas']}")
    print("  " + gestor.resumen())
    print("\n  Reservas registradas:")
    for r in gestor.reservas:
        print("   -", r)
    print(f"\n  El programa nunca se detuvo. Detalle de eventos y errores en '{ARCHIVO_LOG}'.")
    logger.info("Fin de la simulación. %s", gestor.resumen())


if __name__ == "__main__":
    main()
