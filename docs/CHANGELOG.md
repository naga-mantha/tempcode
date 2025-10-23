# Changelog

## Unreleased

### Added
- Documentation for promoting the Django BI suite to a top-level `django_bi` package,
  including migration and verification steps for downstream teams.

### Changed
- All references to the Django BI suite now point to `django_bi`, ensuring
  URL dispatching, settings, and supporting services (signals, Celery workers)
  import from the shared namespace.
- Local development can opt into SQLite by setting `DATABASE_ENGINE=django.db.backends.sqlite3`,
  which simplifies running migrations and tests in environments without PostgreSQL.

### Migration notes
1. Update `INSTALLED_APPS`, URL includes, Celery task autodiscovery lists, and signal
   import paths to use the dotted path `django_bi`.
2. Run `python manage.py migrate` to apply schema changes after the path update.
3. Execute `python manage.py collectstatic --no-input` so that admin and dashboard assets
   are rebuilt after the relocation.
4. Run the full Django test suite to confirm block registrations still resolve correctly
   from the shared registry.

For developers running locally without PostgreSQL, export
`DATABASE_ENGINE=django.db.backends.sqlite3` (and optionally `DATABASE_NAME`) before
running the commands above.
