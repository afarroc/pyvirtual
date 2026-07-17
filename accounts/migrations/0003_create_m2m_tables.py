# Repara tablas intermedias M2M faltantes en la BD (accounts_user_groups,
# accounts_user_user_permissions) que no existian pese a 0001_initial aplicada.
# Se crean con DDL explicito (MySQL/MariaDB) solo si no existen.
#
# Nota: accounts_user usa collation utf8mb4_unicode_ci mientras auth_group /
# auth_permission usan utf8mb4_uca1400_ai_ci. Para evitar errno 150 en las FKs,
# la tabla M2M se crea con utf8mb4_unicode_ci (igual a accounts_user) y las
# columnas que referencian a auth_* se declaran con COLLATE utf8mb4_uca1400_ai_ci.

from django.db import migrations


def create_m2m_tables(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS accounts_user_groups (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                group_id INT NOT NULL COLLATE utf8mb4_uca1400_ai_ci,
                CONSTRAINT accounts_user_groups_user_id_fk
                    FOREIGN KEY (user_id) REFERENCES accounts_user (id)
                    ON DELETE CASCADE,
                CONSTRAINT accounts_user_groups_group_id_fk
                    FOREIGN KEY (group_id) REFERENCES auth_group (id)
                    ON DELETE CASCADE,
                UNIQUE KEY accounts_user_groups_user_id_group_id_uniq (user_id, group_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS accounts_user_user_permissions (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                permission_id INT NOT NULL COLLATE utf8mb4_uca1400_ai_ci,
                CONSTRAINT accounts_user_user_permissions_user_id_fk
                    FOREIGN KEY (user_id) REFERENCES accounts_user (id)
                    ON DELETE CASCADE,
                CONSTRAINT accounts_user_user_permissions_permission_id_fk
                    FOREIGN KEY (permission_id) REFERENCES auth_permission (id)
                    ON DELETE CASCADE,
                UNIQUE KEY accounts_user_user_permissions_user_id_permission_id_uniq (user_id, permission_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        """)


def drop_m2m_tables(apps, schema_editor):
    with schema_editor.connection.cursor() as c:
        c.execute("DROP TABLE IF EXISTS accounts_user_user_permissions")
        c.execute("DROP TABLE IF EXISTS accounts_user_groups")


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_ensure_m2m_tables'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(create_m2m_tables, drop_m2m_tables),
    ]
