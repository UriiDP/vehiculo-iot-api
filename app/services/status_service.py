from app.database import DatabaseConnection
import pymysql

class IoTService:
    # --- MÉTODOS DE EJECUCIÓN GENÉRICOS ---
    @staticmethod
    def ejecutar_sp_lectura(sp_name: str, args=()):
        conn = DatabaseConnection.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.callproc(sp_name, args)
                return cursor.fetchall()
        finally:
            conn.close()

    @staticmethod
    def ejecutar_sp_escritura(sp_name: str, args=()):
        conn = DatabaseConnection.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.callproc(sp_name, args)
                res = cursor.fetchone()
            conn.commit()
            return res
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # =========================================================================
    # INTEGRACIÓN DE LOS 21 STORED PROCEDURES
    # =========================================================================

    # 1. VEHÍCULOS (5 SPs)
    @staticmethod
    def sp_crear_vehiculo(nombre, modelo, descripcion, microcontrolador):
        return IoTService.ejecutar_sp_escritura('sp_crear_vehiculo', (nombre, modelo, descripcion, microcontrolador))

    @staticmethod
    def sp_obtener_vehiculos():
        return IoTService.ejecutar_sp_lectura('sp_obtener_vehiculos')

    @staticmethod
    def sp_obtener_vehiculo(id_vehiculo: int):
        res = IoTService.ejecutar_sp_lectura('sp_obtener_vehiculo', (id_vehiculo,))
        return res[0] if res else None

    @staticmethod
    def sp_actualizar_vehiculo(id_vehiculo, nombre, modelo, descripcion, microcontrolador, activo):
        return IoTService.ejecutar_sp_escritura('sp_actualizar_vehiculo', (id_vehiculo, nombre, modelo, descripcion, microcontrolador, activo))

    @staticmethod
    def sp_eliminar_vehiculo(id_vehiculo: int):
        return IoTService.ejecutar_sp_escritura('sp_eliminar_vehiculo', (id_vehiculo,))

    # 2. COMANDOS (4 SPs)
    @staticmethod
    def sp_crear_comando(id_vehiculo, nombre, codigo, descripcion):
        return IoTService.ejecutar_sp_escritura('sp_crear_comando', (id_vehiculo, nombre, codigo, descripcion))

    @staticmethod
    def sp_obtener_comandos_vehiculo(id_vehiculo: int):
        return IoTService.ejecutar_sp_lectura('sp_obtener_comandos_vehiculo', (id_vehiculo,))

    @staticmethod
    def sp_actualizar_comando(id_comando, nombre, codigo, descripcion, activo):
        return IoTService.ejecutar_sp_escritura('sp_actualizar_comando', (id_comando, nombre, codigo, descripcion, activo))

    @staticmethod
    def sp_eliminar_comando(id_comando: int):
        return IoTService.ejecutar_sp_escritura('sp_eliminar_comando', (id_comando,))

    # 3. ESTADO (2 SPs)
    @staticmethod
    def sp_actualizar_estado(id_vehiculo: int, id_comando: int, conectado: bool):
        return IoTService.ejecutar_sp_escritura('sp_actualizar_estado', (id_vehiculo, id_comando, conectado))

    @staticmethod
    def sp_obtener_estado(id_vehiculo: int):
        res = IoTService.ejecutar_sp_lectura('sp_obtener_estado', (id_vehiculo,))
        return res[0] if res else None

    # 4. HISTORIAL (2 SPs + Reglas de negocio)
    @staticmethod
    def sp_registrar_historial(id_vehiculo: int, id_comando: int, origen: str):
        return IoTService.ejecutar_sp_escritura('sp_registrar_historial', (id_vehiculo, id_comando, origen))

    @staticmethod
    def sp_obtener_historial(id_vehiculo: int):
        return IoTService.ejecutar_sp_lectura('sp_obtener_historial', (id_vehiculo,))

    # Regla de Negocio Paso 6: Devuelve como MÁXIMO los 10 registros más recientes
    @staticmethod
    def obtener_historial_limitado(id_vehiculo: int):
        resultados = IoTService.ejecutar_sp_lectura('sp_obtener_historial', (id_vehiculo,))
        return resultados[:10] if resultados else []

    # Regla de Negocio Paso 5: Transacción Atómica de Movimiento Individual
    @staticmethod
    def registrar_movimiento_individual(id_vehiculo: int, id_comando: int, origen: str):
        conn = DatabaseConnection.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.callproc('sp_actualizar_estado', (id_vehiculo, id_comando, True))
                cursor.callproc('sp_registrar_historial', (id_vehiculo, id_comando, origen))
            conn.commit()
            return True
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    # 5. DEMO (4 SPs)
    @staticmethod
    def sp_crear_demo(id_vehiculo, nombre, descripcion):
        return IoTService.ejecutar_sp_escritura('sp_crear_demo', (id_vehiculo, nombre, descripcion))

    @staticmethod
    def sp_obtener_demos(id_vehiculo: int):
        return IoTService.ejecutar_sp_lectura('sp_obtener_demos', (id_vehiculo,))

    @staticmethod
    def sp_actualizar_demo(id_demo, nombre, descripcion, activo):
        return IoTService.ejecutar_sp_escritura('sp_actualizar_demo', (id_demo, nombre, descripcion, activo))

    @staticmethod
    def sp_eliminar_demo(id_demo: int):
        return IoTService.ejecutar_sp_escritura('sp_eliminar_demo', (id_demo,))

    # 6. MOVIMIENTOS DEMO (4 SPs)
    @staticmethod
    def sp_agregar_movimiento_demo(id_demo, id_comando, orden, duracion_ms, pausa_ms):
        return IoTService.ejecutar_sp_escritura('sp_agregar_movimiento_demo', (id_demo, id_comando, orden, duracion_ms, pausa_ms))

    @staticmethod
    def sp_obtener_movimientos_demo(id_demo: int):
        return IoTService.ejecutar_sp_lectura('sp_obtener_movimientos_demo', (id_demo,))

    @staticmethod
    def sp_actualizar_movimiento_demo(id_demo_movimiento, id_comando, orden, duracion_ms, pausa_ms):
        return IoTService.ejecutar_sp_escritura('sp_actualizar_movimiento_demo', (id_demo_movimiento, id_comando, orden, duracion_ms, pausa_ms))

    @staticmethod
    def sp_eliminar_movimiento_demo(id_demo_movimiento: int):
        return IoTService.ejecutar_sp_escritura('sp_eliminar_movimiento_demo', (id_demo_movimiento,))