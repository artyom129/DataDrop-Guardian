<a id="english"></a>

<div align="center">

**🇬🇧 English** · [🇷🇺 Русский](#russian)

</div>

# DataDrop Guardian

A local-first background service that watches an incoming folder, validates CSV and JSON files, detects duplicate files and duplicate rows, quarantines bad data, routes accepted files, and keeps a full audit trail.

## Why it is useful

Businesses often receive scheduled exports from CRM systems, suppliers, SFTP folders, or internal tools. One malformed date, missing column, duplicated file, or repeated record can silently break downstream automation.

DataDrop Guardian turns the intake folder into a controlled pipeline:

```text
incoming/
   ↓
SHA-256 duplicate check
   ↓
schema + row validation
   ↓
accepted → processed/
invalid  → quarantine/
   ↓
dashboard + SQLite history + Excel report
```

## Features

- Background folder monitoring
- CSV and JSON support
- Configurable pipelines in `config.toml`
- Required columns and fields
- Integer, decimal, date, email, and text validation
- Minimum-value checks
- Duplicate-file detection with SHA-256
- Duplicate-row detection using business keys
- Processed and quarantine routing
- Row-level error history
- Manual upload from the website
- Built-in demo buttons for valid, invalid, and duplicate files
- Retry workflow for quarantined files
- SQLite audit history
- CSV and formatted Excel exports
- REST API and Swagger
- Docker
- Automated tests

## Run

```bash
python -m venv .venv
```

Windows:

```bat
.venv\Scripts\activate
pip install -r requirements.txt
python seed_demo.py
python run.py
```

Open:

```text
http://127.0.0.1:8000
```

## Test from the site

Use the three buttons on the dashboard:

- Create valid file
- Create invalid file
- Create duplicate file

Each button creates a real file and processes it through the same validation engine.

## Tests

```bash
pytest -q
```

## Portfolio context

Personal demonstration project. No client data is included.

---

<a id="russian"></a>

<div align="center">

[🇬🇧 English](#english) · **🇷🇺 Русский**

</div>

# DataDrop Guardian — Русская версия

Фоновый сервис для проверки входящих CSV и JSON файлов.

Он автоматически:

1. следит за папкой `data/incoming`;
2. выбирает схему проверки;
3. проверяет колонки и значения;
4. ищет дубликаты файлов и строк;
5. переносит хорошие файлы в `data/processed`;
6. отправляет плохие файлы в `data/quarantine`;
7. сохраняет историю и ошибки в SQLite;
8. показывает статистику в веб-панели;
9. формирует CSV и Excel отчёты.

На главной странице есть кнопки создания корректного, ошибочного и дублирующего файла.
