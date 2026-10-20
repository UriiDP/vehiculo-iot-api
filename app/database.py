import pymysql
import pymysql.cursors
from app.config import settings

class DatabaseConnection:
    """Clase POO encargada de gestionar las conexiones a la base de datos MySQL en Amazon RDS."""
    
    @staticmethod
    def get_connection():
        """
        Crea y retorna una nueva conexión a la base de datos de Amazon RDS.
        Asegúrate de cerrar la conexión en el servicio o llamar a commit()/rollback().
        """
        try:
            connection = pymysql.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False  # Requerido para transacciones atómicas manuales (POST)
            )
            return connection
        except pymysql.MySQLError as e:
            print(f"[Error de Conexión RDS]: No se pudo conectar a la base de datos: {e}")
            raise e