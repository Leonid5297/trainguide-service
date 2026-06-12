-- Создание пользователей
CREATE USER tragdb WITH PASSWORD 'tragdb';
CREATE USER wrkdb WITH PASSWORD 'wrkdb';
CREATE USER analyticsdb WITH PASSWORD 'analyticsdb';
CREATE USER notifdb WITH PASSWORD 'notifdb';
CREATE USER exportdb WITH PASSWORD 'exportdb';
CREATE USER advisordb WITH PASSWORD 'advisordb';
CREATE USER scheduledb WITH PASSWORD 'scheduledb';

-- Создание баз данных
CREATE DATABASE tragdb OWNER tragdb;
CREATE DATABASE wrkdb OWNER wrkdb;
CREATE DATABASE analyticsdb OWNER analyticsdb;
CREATE DATABASE notifdb OWNER notifdb;
CREATE DATABASE exportdb OWNER exportdb;
CREATE DATABASE advisordb OWNER advisordb;
CREATE DATABASE scheduledb OWNER scheduledb;

-- Привилегии
GRANT ALL PRIVILEGES ON DATABASE tragdb TO tragdb;
GRANT ALL PRIVILEGES ON DATABASE wrkdb TO wrkdb;
GRANT ALL PRIVILEGES ON DATABASE analyticsdb TO analyticsdb;
GRANT ALL PRIVILEGES ON DATABASE notifdb TO notifdb;
GRANT ALL PRIVILEGES ON DATABASE exportdb TO exportdb;
GRANT ALL PRIVILEGES ON DATABASE advisordb TO advisordb;
GRANT ALL PRIVILEGES ON DATABASE scheduledb TO scheduledb;
