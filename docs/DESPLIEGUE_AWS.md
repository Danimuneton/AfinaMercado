# Despliegue en AWS Academy (EC2 + Docker Compose)

Guía paso a paso desde Windows (PowerShell). Al final tendrás AfinaMercado funcionando en
`http://<IP_ELASTICA>/`, con Nginx como único punto de entrada.

> Los pasos dentro de la instancia (después del `ssh`) son comandos de Linux, porque EC2 corre Ubuntu.

---

## 1. Iniciar el laboratorio

1. Entra a AWS Academy → tu curso → **Modules** → **Launch AWS Academy Learner Lab**.
2. Clic en **Start Lab** y espera a que el círculo junto a "AWS" se ponga **verde**.
3. Clic en **AWS** para abrir la consola.
4. Arriba a la derecha verifica que la región sea **N. Virginia (us-east-1)**.

> El laboratorio se apaga solo cuando se acaba el tiempo de la sesión. La instancia se detiene,
> pero **la IP elástica no cambia**. Para la sustentación debes volver a iniciar el lab y la instancia.

## 2. Crear la instancia EC2

En la consola: **EC2** → **Instances** → **Launch instances**.

| Opción | Valor |
|---|---|
| Name | `afinamercado` |
| AMI | **Ubuntu Server 24.04 LTS** (x86_64) |
| Instance type | **t3.medium** (2 vCPU, 4 GB RAM). El sistema tiene 10 contenedores; con `t2.micro` (1 GB) se queda sin memoria |
| Key pair | **Create new key pair** → nombre `afinamercado-key`, tipo RSA, formato **.pem** → se descarga el archivo |
| Network settings → Edit | Crear security group `afinamercado-sg` con las reglas de abajo |
| Storage | **20 GiB** gp3 |

Reglas de entrada (*Inbound rules*) del security group:

| Tipo | Puerto | Origen | Para qué |
|---|---|---|---|
| SSH | 22 | **My IP** | Entrar a la instancia (solo desde tu IP) |
| HTTP | 80 | Anywhere (0.0.0.0/0) | Nginx (API Gateway) |

No abras los puertos 5000, 8000, 5432 ni 6379: los microservicios, la base de datos y Redis solo se
ven dentro de la red de Docker. Ese es el sentido de tener un API Gateway.

Clic en **Launch instance**.

## 3. Asignar la IP elástica

1. **EC2** → **Elastic IPs** → **Allocate Elastic IP address** → **Allocate**.
2. Selecciona la IP nueva → **Actions** → **Associate Elastic IP address**.
3. Resource type: **Instance** → elige `afinamercado` → **Associate**.

Anota esa IP. Es la que se entrega en la plataforma institucional. En esta guía aparece como `<IP_ELASTICA>`.

## 4. Conectarte por SSH desde Windows

Mueve la llave a tu carpeta de usuario y restringe sus permisos (Windows exige que solo tú puedas leerla):

```powershell
Move-Item $HOME\Downloads\afinamercado-key.pem $HOME\.ssh\afinamercado-key.pem
icacls $HOME\.ssh\afinamercado-key.pem /inheritance:r
icacls $HOME\.ssh\afinamercado-key.pem /grant:r "$($env:USERNAME):(R)"
ssh -i $HOME\.ssh\afinamercado-key.pem ubuntu@<IP_ELASTICA>
```

Si no existe la carpeta `.ssh`, créala primero con `mkdir $HOME\.ssh`.
La primera vez pregunta *"Are you sure you want to continue connecting?"* → escribe `yes`.

## 5. Instalar Docker en la instancia

Ya dentro de la instancia (el prompt dice `ubuntu@ip-...`):

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker ubuntu
exit
```

Vuelve a conectarte con el mismo `ssh` del paso 4 (para que tome el grupo `docker`) y verifica:

```bash
docker --version
docker compose version
```

## 6. Descargar el proyecto y configurarlo

```bash
git clone https://github.com/Danimuneton/AfinaMercado.git
cd AfinaMercado
cp .env.example .env
```

Genera claves aleatorias (cópialas, las vas a pegar en el `.env`):

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"   # DJANGO_SECRET_KEY
python3 -c "import secrets; print(secrets.token_urlsafe(24))"   # POSTGRES_PASSWORD
python3 -c "import secrets; print(secrets.token_urlsafe(32))"   # SERVICE_TOKEN
```

Edita el archivo con `nano .env` y cambia estas líneas (reemplaza `<IP_ELASTICA>`):

```
NGINX_PORT=80
DJANGO_SECRET_KEY=<clave 1>
DJANGO_ALLOWED_HOSTS=<IP_ELASTICA>,localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://<IP_ELASTICA>
DJANGO_SUPERUSER_PASSWORD=<una clave para el admin>
POSTGRES_PASSWORD=<clave 2>
SERVICE_TOKEN=<clave 3>
PUBLIC_BASE_URL=http://<IP_ELASTICA>
```

Guarda con `Ctrl+O`, `Enter`, y sal con `Ctrl+X`.

## 7. Levantar todo el ecosistema

```bash
docker compose up -d --build
```

La primera vez tarda entre 3 y 6 minutos. Revisa que todo quede arriba:

```bash
docker compose ps
```

Todos los servicios deben decir `Up`, y los que tienen healthcheck `(healthy)`. Si alguno falla:

```bash
docker compose logs --tail=50 <nombre_del_servicio>
```

## 8. Verificar desde tu PC (PowerShell)

```powershell
# Interfaz web (Django)
Start-Process "http://<IP_ELASTICA>/"

# Índice del API Gateway
Invoke-RestMethod -Uri "http://<IP_ELASTICA>/api/v2/"

# Microservicio de Catálogo (Flask) - API pública para el aliado
Invoke-RestMethod -Uri "http://<IP_ELASTICA>/api/v2/catalogo/publico/instrumentos"

# Microservicio de Pagos (Flask)
Invoke-RestMethod -Uri "http://<IP_ELASTICA>/api/v2/pagos/" -Method Post -ContentType "application/json" -Body '{"orden_id":1,"monto":150000,"metodo":"tarjeta"}'

# API legacy del monolito (Django)
Invoke-RestMethod -Uri "http://<IP_ELASTICA>/api/v1/instrumentos/"
```

Para ver la tarea asíncrona en acción, haz una compra en la web y mira el log del worker:

```bash
docker compose logs -f notificaciones_worker
```

## 9. Actualizar después de nuevos commits

```bash
cd ~/AfinaMercado
git pull
docker compose up -d --build
```

## 10. Antes de la sustentación

1. Inicia el Learner Lab (**Start Lab**).
2. **EC2** → **Instances** → selecciona `afinamercado` → **Instance state** → **Start instance**.
3. Espera 1–2 minutos. Los contenedores arrancan solos (`restart: unless-stopped`).
4. Abre `http://<IP_ELASTICA>/` para confirmar.

## Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| `Bad Request (400)` en la web | Falta la IP en `DJANGO_ALLOWED_HOSTS` del `.env`. Corrígela y ejecuta `docker compose up -d` |
| `CSRF verification failed` al enviar formularios | Falta `http://<IP_ELASTICA>` en `DJANGO_CSRF_TRUSTED_ORIGINS` |
| `{"error":"servicio_no_disponible"...}` | Ese microservicio está caído o arrancando: `docker compose ps` y `docker compose logs <servicio>` |
| `password authentication failed` en los logs | Cambiaste `POSTGRES_PASSWORD` después de crear el volumen. Borra el volumen (se pierden los datos): `docker compose down -v` y vuelve a levantar |
| La página no carga | Revisa que el security group tenga el puerto 80 abierto y que la instancia esté *Running* |
| Se cerró la sesión SSH | Normal. Los contenedores siguen corriendo en la instancia |
