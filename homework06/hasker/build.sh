# Project settings
PROJECT_NAME=hasker
PROJECT_FOLDER=$(pwd)

# Email settings
EMAIL_HOST=$EMAIL_HOST
EMAIL_PORT=$EMAIL_PORT
EMAIL_HOST_USER=$EMAIL_HOST_USER
EMAIL_HOST_PASSWORD=$EMAIL_HOST_PASSWORD

if [ "$EMAIL_HOST" == "" ]; then
    EMAIL_HOST="smtp.yandex.ru"
fi

if [ "$EMAIL_PORT" == "" ]; then
    EMAIL_PORT=465
fi

if [ "$EMAIL_HOST_USER" == "" ]; then
    EMAIL_HOST_USER="hasker"
fi

if [ "$EMAIL_HOST_PASSWORD" == "" ]; then
    EMAIL_HOST_PASSWORD="secret"
fi

# Postgres settings
DB_NAME=$PROJECT_NAME
DB_USER=$1
DB_PASSWORD=$2

if [ "$DB_USER" == "" ] || [ "$DB_PASSWORD" == "" ]; then
    echo "Usage: build.sh <db_user> <db_password>"
    echo
    exit 1
fi

PACKAGES=('postgresql' 'python' 'python-pip' 'nginx')

# Update and install required packages
apt-get -qq update

for pkg in "${PACKAGES[@]}"
do
    echo "Installing '$pkg'..."
    apt-get -qq -y install $pkg
    if [ $? -ne 0 ]; then
        echo "Error installing system packages '$pkg'"
        exit 1
    fi
done

# Install required packages from pip
pip install -r requirements/production.txt
echo "All required packages are installed"

# Create database
echo "Starting postgresql..."
service postgresql start
su postgres -c "psql -c \"CREATE USER ${DB_USER} PASSWORD '${DB_PASSWORD}'\""
su postgres -c "psql -c \"CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}\""

# Django configure
echo "Generating Django secret key..."
SECRET_KEY=`openssl rand -base64 48`
if [ $? -ne 0 ]; then
    echo "Error: Can't create secret key"
    exit 1
fi

cat > config/settings/settings.ini << EOF
[settings]
SECRET_KEY=${SECRET_KEY}
EMAIL_HOST=${EMAIL_HOST}
EMAIL_PORT=${EMAIL_PORT}
EMAIL_HOST_USER=${EMAIL_HOST_USER}
EMAIL_HOST_PASSWORD=${EMAIL_HOST_PASSWORD}
EMAIL_USE_SSL=True
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
EOF

python manage.py collectstatic
python manage.py makemigrations
python manage.py migrate

# Configure uwsgi
mkdir -p /run/uwsgi
mkdir -p /usr/local/etc

cat > /usr/local/etc/uwsgi.ini << EOF
[uwsgi]
project = $PROJECT_NAME
chdir = $PROJECT_FOLDER
module = config.wsgi:application

master = true
processes = 1

socket = /run/uwsgi/%(project).sock
chmod-socket = 666
vacuum = true

die-on-term = true
env=DJANGO_SETTINGS_MODULE=config.settings.production
EOF

# Configure nginx
cat > /etc/nginx/conf.d/${PROJECT_NAME}.conf << EOF
server {
    listen 8000;
    server_name localhost 127.0.0.1;

    location /static/ {
        root /var/www;
    }

    location /media/ {
        root /var/www;
    }

    location / {
        include uwsgi_params;
        uwsgi_pass unix:/run/uwsgi/${PROJECT_NAME}.sock;
    }
}
EOF

uwsgi --ini /usr/local/etc/uwsgi.ini &
service nginx start
