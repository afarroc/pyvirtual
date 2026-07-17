#!/usr/bin/env bash
set -o errexit

echo "=== DJANGO BUILD PROCESS ==="

# Verificar entorno
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  WARNING: No virtual environment detected"
else
    echo "✅ Virtual environment: $VIRTUAL_ENV"
fi

# Set Django settings
export DJANGO_SETTINGS_MODULE=panel.settings

# Install Python dependencies
echo "Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# Apply database migrations in correct order
echo "Applying database migrations..."

echo "Applying Django core migrations..."
python manage.py migrate auth --verbosity=1
python manage.py migrate contenttypes --verbosity=1
python manage.py migrate sessions --verbosity=1

echo "Applying remaining migrations..."
# --fake-initial: aplica el 0001_initial como fake si las tablas ya existen
# con el mismo schema (seguro tras regenerar migraciones contra Postgres).
python manage.py migrate --fake-initial --no-input --verbosity=1

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input --verbosity=1

# Verificar resultado
if [ $? -eq 0 ]; then
    echo "✅ Build completed successfully!"
    echo "Database migrations applied and static files collected."
else
    echo "❌ Build failed!"
    exit 1
fi

echo "=== BUILD COMPLETE ==="
