from app.validation import validate

def test_valid_row(settings):
    p=settings.pipelines[0]
    valid,errors,dupes=validate([{"customer_id":"1","name":"A","email":"a@b.com","balance":"10","signup_date":"2026-08-01"}],p)
    assert len(valid)==1 and errors==[] and dupes==0

def test_invalid_and_duplicate(settings):
    p=settings.pipelines[0]
    rows=[
      {"customer_id":"1","name":"","email":"bad","balance":"-1","signup_date":"x"},
      {"customer_id":"1","name":"A","email":"a@b.com","balance":"2","signup_date":"2026-08-01"},
    ]
    valid,errors,dupes=validate(rows,p)
    codes={e["error_code"] for e in errors}
    assert {"required","invalid_type","below_minimum","duplicate_row"}<=codes
    assert dupes==1 and valid==[]

def test_missing_column(settings):
    valid,errors,dupes=validate([{"customer_id":"1"}],settings.pipelines[0])
    assert valid==[] and any(e["error_code"]=="missing_column" for e in errors)
