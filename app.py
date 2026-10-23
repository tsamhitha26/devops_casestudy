"""A small local PDF merger and splitter built with Flask and pypdf."""

from io import BytesIO
import re
import zipfile

from flask import Flask, flash, redirect, render_template, request, send_file, url_for
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.secret_key = "local-pdf-tool-change-this-key"
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB total request size


def read_pdf(upload):
    """Parse an uploaded PDF from memory and give a friendly error if invalid."""
    try:
        upload.stream.seek(0)
        reader = PdfReader(upload.stream, strict=True)
        if reader.is_encrypted:
            raise ValueError(f"{upload.filename} is password-protected. Please unlock it first.")
        # Accessing pages forces pypdf to parse the document before processing.
        if len(reader.pages) == 0:
            raise ValueError(f"{upload.filename} does not contain any pages.")
        return reader
    except (PdfReadError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc).startswith(upload.filename):
            raise
        raise ValueError(f"{upload.filename} is not a readable PDF. Please choose a valid PDF file.") from exc
    except Exception as exc:
        raise ValueError(f"{upload.filename} is not a readable PDF. Please choose a valid PDF file.") from exc


def parse_ranges(value, page_count):
    """Convert text like '1-3, 5' to zero-based inclusive page index groups."""
    groups = []
    if not value.strip():
        raise ValueError("Enter at least one page number or range, for example 1-3, 5-6.")
    for part in value.split(","):
        part = part.strip()
        match = re.fullmatch(r"(\d+)(?:\s*-\s*(\d+))?", part)
        if not match:
            raise ValueError(f"'{part}' is not a valid page number or range. Use a format like 1-3, 5-6.")
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if start < 1 or end < start or end > page_count:
            raise ValueError(f"'{part}' is outside the available page range (1-{page_count}).")
        groups.append((start, end))
    return groups


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/merge", methods=["POST"])
def merge():
    files = [f for f in request.files.getlist("pdf_files") if f and f.filename]
    if len(files) < 2:
        flash("Choose at least two PDF files to merge.", "error")
        return redirect(url_for("index"))
    try:
        writer = PdfWriter()
        for uploaded in files:
            writer.append(read_pdf(uploaded))
        output = BytesIO()
        writer.write(output)
        output.seek(0)
        return send_file(output, mimetype="application/pdf", as_attachment=True, download_name="merged.pdf")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))


@app.route("/split", methods=["POST"])
def split():
    uploaded = request.files.get("pdf_file")
    if not uploaded or not uploaded.filename:
        flash("Choose a PDF file to split.", "error")
        return redirect(url_for("index"))
    try:
        reader = read_pdf(uploaded)
        groups = parse_ranges(request.form.get("page_ranges", ""), len(reader.pages))
        archive = BytesIO()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
            for number, (start, end) in enumerate(groups, start=1):
                writer = PdfWriter()
                for page_index in range(start - 1, end):
                    writer.add_page(reader.pages[page_index])
                pdf_data = BytesIO()
                writer.write(pdf_data)
                zipped.writestr(f"pages_{start}-{end}_{number}.pdf", pdf_data.getvalue())
        archive.seek(0)
        return send_file(archive, mimetype="application/zip", as_attachment=True, download_name="split_pdfs.zip")
    except ValueError as exc:
        flash(str(exc), "error")
        return redirect(url_for("index"))


@app.errorhandler(RequestEntityTooLarge)
def too_large(_error):
    flash("The upload is larger than 25 MB. Please choose smaller PDF files.", "error")
    return redirect(url_for("index"))


if __name__ == "__main__":
    # Debug is off by default; visit http://127.0.0.1:5000 after starting the app.
    app.run(host="0.0.0.0", port=5000, debug=False)
