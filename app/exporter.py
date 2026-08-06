from io import BytesIO, StringIO
import csv, xlsxwriter

FIELDS = ["id","filename","pipeline_id","status","file_format","row_count",
          "valid_rows","invalid_rows","duplicate_rows","error_count",
          "message","created_at","completed_at","final_path"]

def csv_bytes(rows):
    out = StringIO()
    writer = csv.DictWriter(out, fieldnames=FIELDS, extrasaction="ignore")
    writer.writeheader(); writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")

def xlsx_bytes(rows):
    stream = BytesIO()
    wb = xlsxwriter.Workbook(stream, {"in_memory": True})
    ws = wb.add_worksheet("File Audit")
    summary = wb.add_worksheet("Summary")
    header = wb.add_format({"bold":True,"font_color":"#fff","bg_color":"#172033","border":1})
    good = wb.add_format({"bg_color":"#e8f7ee","font_color":"#157347"})
    bad = wb.add_format({"bg_color":"#fde8e7","font_color":"#b42318"})
    warn = wb.add_format({"bg_color":"#fff3dc","font_color":"#9a5700"})
    title = wb.add_format({"bold":True,"font_size":18})
    metric = wb.add_format({"bold":True,"font_size":20})
    for c, f in enumerate(FIELDS):
        ws.write(0,c,f.replace("_"," ").title(),header)
    for r, row in enumerate(rows, start=1):
        for c,f in enumerate(FIELDS):
            ws.write(r,c,"" if row.get(f) is None else row.get(f))
        fmt = good if row["status"]=="accepted" else warn if row["status"]=="duplicate" else bad
        ws.set_row(r,None,fmt)
    ws.freeze_panes(1,0); ws.autofilter(0,0,max(len(rows),1),len(FIELDS)-1)
    ws.set_column(0,0,7); ws.set_column(1,4,20); ws.set_column(5,9,13)
    ws.set_column(10,10,40); ws.set_column(11,13,25)
    summary.write("A1","DataDrop Guardian Report",title)
    metrics = [
        ("Total files",len(rows)),
        ("Accepted",sum(x["status"]=="accepted" for x in rows)),
        ("Quarantined",sum(x["status"]=="quarantined" for x in rows)),
        ("Duplicates",sum(x["status"]=="duplicate" for x in rows)),
        ("Rows inspected",sum(int(x.get("row_count") or 0) for x in rows)),
    ]
    for i,(label,value) in enumerate(metrics,start=3):
        summary.write(i,0,label,header); summary.write(i,1,value,metric)
    summary.set_column("A:A",24); summary.set_column("B:B",18)
    wb.close()
    return stream.getvalue()
