from import_export import resources

from users.models import User


class UserResource(resources.ModelResource):
    class Meta:
        model = User
        import_id_fields = ['rut']
        fields = [
            'rut', 'cargo',
            'first_name', 'last_name',
            'email', 'username',
            'company', 'role', 'status',
        ]
        skip_unchanged = True
        report_skipped = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Maps username → plain-text password for password hashing in before_save_instance.
        # Keyed by username because that's the first field set on the instance by import_obj.
        self._pending_passwords: dict[str, str] = {}

    def before_import_row(self, row, row_number=None, **kwargs):
        nombre  = (row.pop('nombre', '') or '').strip()
        rut_raw = (row.get('rut') or '').strip()
        empresa = (row.pop('empresa', '') or '').strip().lower()

        valid_slugs = {c[0] for c in User.Company.choices}
        if empresa not in valid_slugs:
            raise ValueError(
                f"Fila {row_number}: empresa debe ser una de {sorted(valid_slugs)}, got '{empresa}'"
            )

        parts = nombre.split(None, 1)
        row['first_name'] = parts[0] if parts else ''
        row['last_name']  = parts[1] if len(parts) > 1 else ''

        rut_clean = rut_raw.replace('-', '').replace('.', '')
        row['email']              = f'{rut_clean}@{empresa}.internal'
        row['username']           = rut_clean
        row['company'] = empresa
        row['role']    = User.Role.TECHNICIAN
        row['status']  = User.Status.INACTIVE
        row['rut']     = rut_raw or None

        # Store password by username so before_save_instance can retrieve it.
        self._pending_passwords[rut_clean] = rut_clean

    def before_save_instance(self, instance, new, **kwargs):
        """Set hashed password for new users imported from CSV/XLSX."""
        pwd = self._pending_passwords.pop(instance.username, None)
        if pwd and not instance.has_usable_password():
            instance.set_password(pwd)
