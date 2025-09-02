#!/bin/sh

set -e

echo "DB info:"
echo "Host: ${KC_DB_URL_HOST}"
echo "User: ${KC_DB_USERNAME}"
echo "DB: ${KC_DB_URL_DATABASE}"

psql -d "${KC_DB_URL_DATABASE}" -h "${KC_DB_URL_HOST}" -U "${KC_DB_USERNAME}" -f - <<SQL
    DELETE FROM credential WHERE user_id IN (SELECT id FROM user_entity WHERE username = 'admin');
    DELETE FROM user_role_mapping WHERE user_id IN (SELECT id FROM user_entity WHERE username = 'admin');
    DELETE FROM user_entity WHERE username = 'admin';
SQL
