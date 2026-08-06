from __future__ import annotations
import hashlib, re, shutil
from pathlib import Path
from uuid import uuid4
from .database import add_errors, add_file, accepted_fingerprint, finish_file
from .validation import ParseError, load_records, validate

class Engine:
    def __init__(self, settings):
        self.settings = settings

    def match_pipeline(self, filename):
        for pipeline in self.settings.pipelines:
            if re.match(pipeline.filename_pattern, filename):
                return pipeline
        return None

    @staticmethod
    def fingerprint(path):
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def unique(folder, filename):
        target = folder / filename
        return target if not target.exists() else folder / f"{target.stem}_{uuid4().hex[:8]}{target.suffix}"

    def move(self, path, folder):
        target = self.unique(folder, path.name)
        shutil.move(str(path), str(target))
        return target

    def process(self, path: Path):
        fp = self.fingerprint(path)
        pipeline = self.match_pipeline(path.name)
        file_id = add_file(
            self.settings.database_path, path.name,
            pipeline.id if pipeline else None, fp, str(path)
        )
        if pipeline is None:
            target = self.move(path, self.settings.quarantine_dir)
            errors = [{
                "row_number": None, "field_name": None,
                "error_code": "no_pipeline",
                "message": "No configured pipeline matches this filename",
                "raw_value": path.name,
            }]
            add_errors(self.settings.database_path, file_id, errors)
            finish_file(self.settings.database_path, file_id,
                status="quarantined", error_count=1,
                message=errors[0]["message"], final_path=str(target))
            return {"file_id": file_id, "status": "quarantined", "message": errors[0]["message"]}

        if accepted_fingerprint(self.settings.database_path, fp):
            target = self.move(path, self.settings.quarantine_dir)
            errors = [{
                "row_number": None, "field_name": None,
                "error_code": "duplicate_file",
                "message": "Exact duplicate of a previously accepted file",
                "raw_value": fp,
            }]
            add_errors(self.settings.database_path, file_id, errors)
            finish_file(self.settings.database_path, file_id,
                status="duplicate", error_count=1,
                message=errors[0]["message"], final_path=str(target))
            return {"file_id": file_id, "status": "duplicate", "message": errors[0]["message"]}

        try:
            file_format, records = load_records(path)
            valid, errors, duplicate_rows = validate(records, pipeline)
        except ParseError as exc:
            target = self.move(path, self.settings.quarantine_dir)
            errors = [{
                "row_number": None, "field_name": None,
                "error_code": "parse_error",
                "message": f"Parse error: {exc}",
                "raw_value": None,
            }]
            add_errors(self.settings.database_path, file_id, errors)
            finish_file(self.settings.database_path, file_id,
                status="quarantined", error_count=1,
                message=errors[0]["message"], final_path=str(target))
            return {"file_id": file_id, "status": "quarantined", "message": errors[0]["message"]}

        invalid_rows = len({e["row_number"] for e in errors if e.get("row_number") is not None})
        status = "quarantined" if errors else "accepted"
        target = self.move(path, self.settings.quarantine_dir if errors else self.settings.processed_dir)
        message = f"{len(errors)} validation error(s) found" if errors else "File accepted"
        add_errors(self.settings.database_path, file_id, errors)
        finish_file(self.settings.database_path, file_id,
            status=status, file_format=file_format, row_count=len(records),
            valid_rows=len(valid), invalid_rows=invalid_rows,
            duplicate_rows=duplicate_rows, error_count=len(errors),
            message=message, final_path=str(target))
        return {
            "file_id": file_id, "status": status, "message": message,
            "row_count": len(records), "valid_rows": len(valid),
            "invalid_rows": invalid_rows, "duplicate_rows": duplicate_rows,
            "error_count": len(errors),
        }
