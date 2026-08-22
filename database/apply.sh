#!/usr/bin/env bash
# Aplica migraciones y/o seeds en orden numerico.
# Uso: apply.sh [migrations|seeds|all]   (por defecto: all)
#
# Todo el SQL es idempotente, asi que este script se puede volver a correr
# cuantas veces haga falta. Cada archivo va en su propia transaccion: si uno
# falla, se aborta ese archivo entero y el script termina con error.
set -euo pipefail

TARGET="${1:-all}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PSQL=(psql --username "${POSTGRES_USER:-postgres}" --dbname "${POSTGRES_DB:-postgres}"
      --host "${PGHOST:-postgres}" --port "${PGPORT:-5432}"
      --no-psqlrc --quiet --single-transaction
      --set ON_ERROR_STOP=1)

run_dir() {
    local dir="$1" label="$2" found=0
    for file in "$dir"/*.sql; do
        [ -e "$file" ] || continue
        found=1
        echo "  → ${label}/$(basename "$file")"
        "${PSQL[@]}" --file "$file"
    done
    [ "$found" -eq 1 ] || echo "  (sin archivos en ${label}/)"
}

case "$TARGET" in
    migrations) echo "Aplicando migraciones…"; run_dir "$DIR/migrations" migrations ;;
    seeds)      echo "Aplicando seeds…";       run_dir "$DIR/seeds" seeds ;;
    all)        echo "Aplicando migraciones…"; run_dir "$DIR/migrations" migrations
                echo "Aplicando seeds…";       run_dir "$DIR/seeds" seeds ;;
    *)          echo "Uso: apply.sh [migrations|seeds|all]" >&2; exit 2 ;;
esac

echo "Listo."
