-- Database per service: cada microservicio es dueño de su propia base de datos.
-- (Este script solo se ejecuta la primera vez que se crea el volumen de PostgreSQL.)
CREATE DATABASE catalogo_db;
CREATE DATABASE carrito_db;
CREATE DATABASE ordenes_db;
CREATE DATABASE pagos_db;
