import io
from datetime import datetime

def escape_pdf(text):
    if text is None:
        return ""
    text = str(text)
    # Filter out characters outside ascii printable range for pure standard PDF Type1 font
    clean = "".join(c if 32 <= ord(c) <= 126 else " " for c in text)
    return clean.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

class SimplePDFBuilder:
    def __init__(self):
        self.width = 595.28   # A4 width in points
        self.height = 841.89  # A4 height in points
        self.stream_ops = []

    def rect(self, x, y, w, h, fill_rgb=None, stroke_rgb=None, line_width=1):
        if fill_rgb and stroke_rgb:
            self.stream_ops.append(f"{stroke_rgb[0]:.2f} {stroke_rgb[1]:.2f} {stroke_rgb[2]:.2f} RG")
            self.stream_ops.append(f"{fill_rgb[0]:.2f} {fill_rgb[1]:.2f} {fill_rgb[2]:.2f} rg")
            self.stream_ops.append(f"{line_width:.2f} w")
            self.stream_ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re B")
        elif fill_rgb:
            self.stream_ops.append(f"{fill_rgb[0]:.2f} {fill_rgb[1]:.2f} {fill_rgb[2]:.2f} rg")
            self.stream_ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        elif stroke_rgb:
            self.stream_ops.append(f"{stroke_rgb[0]:.2f} {stroke_rgb[1]:.2f} {stroke_rgb[2]:.2f} RG")
            self.stream_ops.append(f"{line_width:.2f} w")
            self.stream_ops.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def line(self, x1, y1, x2, y2, stroke_rgb=(0.2, 0.2, 0.2), line_width=1):
        self.stream_ops.append(f"{stroke_rgb[0]:.2f} {stroke_rgb[1]:.2f} {stroke_rgb[2]:.2f} RG")
        self.stream_ops.append(f"{line_width:.2f} w")
        self.stream_ops.append(f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def text(self, x, y, text_str, font="F1", size=10, rgb=(0.1, 0.1, 0.1)):
        escaped = escape_pdf(text_str)
        self.stream_ops.append(f"BT /{font} {size} Tf {rgb[0]:.2f} {rgb[1]:.2f} {rgb[2]:.2f} rg {x:.2f} {y:.2f} Td ({escaped}) Tj ET")

    def build(self):
        content_stream = "\n".join(self.stream_ops).encode('latin-1')
        stream_len = len(content_stream)

        objects = []
        # obj 1: Catalog
        objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
        # obj 2: Pages
        objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
        # obj 3: Page
        objects.append(
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595.28 841.89] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> >>"
        )
        # obj 4: Content stream
        objects.append(
            f"<< /Length {stream_len} >>\nstream\n".encode('latin-1') +
            content_stream +
            b"\nendstream"
        )
        # obj 5: Regular font
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
        # obj 6: Bold font
        objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

        # Assemble PDF file with correct xref offsets
        buf = io.BytesIO()
        buf.write(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
        
        xref_offsets = []
        for i, obj_bytes in enumerate(objects, start=1):
            offset = buf.tell()
            xref_offsets.append(offset)
            buf.write(f"{i} 0 obj\n".encode('latin-1'))
            buf.write(obj_bytes)
            buf.write(b"\nendobj\n")

        startxref = buf.tell()
        buf.write(f"xref\n0 {len(objects) + 1}\n".encode('latin-1'))
        buf.write(b"0000000000 65535 f \n")
        for offset in xref_offsets:
            buf.write(f"{offset:010d} 00000 n \n".encode('latin-1'))

        buf.write(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{startxref}\n%%EOF\n".encode('latin-1')
        )

        return buf.getvalue()


def generate_scorecard_pdf(booking):
    pdf = SimplePDFBuilder()
    
    student = booking.student
    exam = booking.examination
    course = exam.course
    slot = booking.slot
    examiner = booking.evaluator or slot.examiner

    # Top Brand Banner
    pdf.rect(0, 755, 595.28, 86.89, fill_rgb=(0.08, 0.22, 0.45))
    pdf.text(45, 800, "EXAMINATION MANAGEMENT SYSTEM", font="F2", size=18, rgb=(1.0, 1.0, 1.0))
    pdf.text(45, 775, "OFFICIAL CANDIDATE SCORECARD & EVALUATION REPORT", font="F1", size=11, rgb=(0.85, 0.90, 1.0))

    # Watermark / Document info badge on top right
    pdf.rect(430, 768, 120, 24, fill_rgb=(0.15, 0.32, 0.60))
    pdf.text(440, 775, f"Booking #{booking.id}", font="F2", size=10, rgb=(1.0, 1.0, 1.0))

    # Student & Exam Info Box
    pdf.rect(40, 620, 515.28, 120, fill_rgb=(0.96, 0.97, 0.99), stroke_rgb=(0.8, 0.85, 0.9), line_width=1)
    
    # Left column: Candidate details
    pdf.text(55, 718, "CANDIDATE DETAILS", font="F2", size=10, rgb=(0.1, 0.2, 0.5))
    pdf.text(55, 698, f"Name: {student.name}", font="F1", size=10, rgb=(0.1, 0.1, 0.1))
    pdf.text(55, 680, f"Roll / Student ID: {student.student_id}", font="F2", size=10, rgb=(0.1, 0.1, 0.1))
    pdf.text(55, 662, f"Department: {student.department}", font="F1", size=10, rgb=(0.1, 0.1, 0.1))
    pdf.text(55, 644, f"Contact / Email: {student.user.email}", font="F1", size=9, rgb=(0.3, 0.3, 0.3))

    # Divider line
    pdf.line(297.64, 630, 297.64, 730, stroke_rgb=(0.85, 0.85, 0.85), line_width=1)

    # Right column: Examination details
    pdf.text(315, 718, "EXAMINATION DETAILS", font="F2", size=10, rgb=(0.1, 0.2, 0.5))
    pdf.text(315, 698, f"Course: {course.name} ({course.code})", font="F2", size=10, rgb=(0.1, 0.1, 0.1))
    pdf.text(315, 680, f"Exam: {exam.title} ({exam.exam_type})", font="F1", size=10, rgb=(0.1, 0.1, 0.1))
    eval_date_str = booking.evaluation_date.strftime('%d-%b-%Y') if booking.evaluation_date else slot.slot_date.strftime('%d-%b-%Y')
    pdf.text(315, 662, f"Slot Date: {slot.slot_date.strftime('%d-%b-%Y')} | Eval: {eval_date_str}", font="F1", size=9, rgb=(0.1, 0.1, 0.1))
    pdf.text(315, 644, f"Evaluator: {examiner.name} ({examiner.department})", font="F1", size=9, rgb=(0.3, 0.3, 0.3))

    # Rubrics Section Title
    pdf.text(45, 595, "CRITERIA-BASED EVALUATION BREAKDOWN", font="F2", size=11, rgb=(0.08, 0.22, 0.45))

    # Table Header
    y_cursor = 570
    pdf.rect(40, y_cursor, 515.28, 22, fill_rgb=(0.2, 0.3, 0.5))
    pdf.text(50, y_cursor + 6, "#", font="F2", size=9, rgb=(1.0, 1.0, 1.0))
    pdf.text(75, y_cursor + 6, "Rubric Criterion", font="F2", size=9, rgb=(1.0, 1.0, 1.0))
    pdf.text(280, y_cursor + 6, "Max Marks", font="F2", size=9, rgb=(1.0, 1.0, 1.0))
    pdf.text(360, y_cursor + 6, "Marks Awarded", font="F2", size=9, rgb=(1.0, 1.0, 1.0))
    pdf.text(450, y_cursor + 6, "Remarks", font="F2", size=9, rgb=(1.0, 1.0, 1.0))

    # Rows
    scores = booking.rubric_scores.all()
    total_max = 0.0
    total_awarded = 0.0

    y_cursor -= 24
    row_idx = 1
    for item in scores:
        rubric = item.rubric
        max_m = rubric.max_marks if rubric else 0.0
        awarded_m = item.score
        remarks_txt = item.remarks or "-"
        total_max += max_m
        total_awarded += awarded_m

        # Zebra striping
        fill = (0.97, 0.98, 1.0) if row_idx % 2 == 1 else (1.0, 1.0, 1.0)
        pdf.rect(40, y_cursor, 515.28, 22, fill_rgb=fill, stroke_rgb=(0.88, 0.88, 0.9), line_width=0.5)

        pdf.text(50, y_cursor + 6, str(row_idx), font="F1", size=9, rgb=(0.2, 0.2, 0.2))
        crit_name = (rubric.criterion_name if rubric else "Criterion")[:32]
        pdf.text(75, y_cursor + 6, crit_name, font="F2", size=9, rgb=(0.1, 0.1, 0.1))
        pdf.text(285, y_cursor + 6, f"{max_m:.1f}", font="F1", size=9, rgb=(0.2, 0.2, 0.2))
        pdf.text(365, y_cursor + 6, f"{awarded_m:.1f}", font="F2", size=9, rgb=(0.1, 0.3, 0.7))
        pdf.text(450, y_cursor + 6, str(remarks_txt)[:20], font="F1", size=8, rgb=(0.3, 0.3, 0.3))

        y_cursor -= 22
        row_idx += 1

    # Total Row
    pdf.rect(40, y_cursor, 515.28, 26, fill_rgb=(0.90, 0.93, 0.98), stroke_rgb=(0.2, 0.3, 0.5), line_width=1)
    pdf.text(75, y_cursor + 8, "GRAND TOTAL", font="F2", size=10, rgb=(0.08, 0.22, 0.45))
    pdf.text(285, y_cursor + 8, f"{total_max:.1f}", font="F2", size=10, rgb=(0.08, 0.22, 0.45))
    pdf.text(365, y_cursor + 8, f"{booking.marks_obtained or total_awarded:.1f}", font="F2", size=11, rgb=(0.1, 0.5, 0.1))
    
    pct = booking.percentage or (round((total_awarded / total_max * 100), 2) if total_max > 0 else 0.0)
    grade = "Distinction" if pct >= 75 else ("First Class" if pct >= 60 else ("Pass" if pct >= 40 else "Needs Improvement"))
    pdf.text(450, y_cursor + 8, f"{pct:.1f}% ({grade})", font="F2", size=10, rgb=(0.1, 0.5, 0.1))

    # Evaluation Remarks & Feedback Box
    y_cursor -= 35
    pdf.text(45, y_cursor, "EXAMINER OVERALL REMARKS & COMMENTS", font="F2", size=10, rgb=(0.08, 0.22, 0.45))
    
    y_cursor -= 70
    pdf.rect(40, y_cursor, 515.28, 65, fill_rgb=(0.98, 0.99, 1.0), stroke_rgb=(0.85, 0.85, 0.9), line_width=1)
    overall_remarks = booking.evaluation_remarks or "The student demonstrated satisfactory understanding during the assessment."
    # split text lines
    words = overall_remarks.split()
    line1 = " ".join(words[:14])
    line2 = " ".join(words[14:28])
    line3 = " ".join(words[28:42])
    pdf.text(55, y_cursor + 45, line1, font="F1", size=9, rgb=(0.2, 0.2, 0.2))
    if line2:
        pdf.text(55, y_cursor + 30, line2, font="F1", size=9, rgb=(0.2, 0.2, 0.2))
    if line3:
        pdf.text(55, y_cursor + 15, line3, font="F1", size=9, rgb=(0.2, 0.2, 0.2))

    # Sign-off & Verification
    y_cursor -= 70
    pdf.line(55, y_cursor + 15, 200, y_cursor + 15, stroke_rgb=(0.5, 0.5, 0.5), line_width=1)
    pdf.text(55, y_cursor, f"Evaluator Signature ({examiner.name})", font="F1", size=8, rgb=(0.4, 0.4, 0.4))

    pdf.line(355, y_cursor + 15, 500, y_cursor + 15, stroke_rgb=(0.5, 0.5, 0.5), line_width=1)
    pdf.text(355, y_cursor, "Controller of Examinations (EMS)", font="F1", size=8, rgb=(0.4, 0.4, 0.4))

    # Footer note
    pdf.rect(0, 0, 595.28, 35, fill_rgb=(0.94, 0.95, 0.98))
    pdf.text(45, 13, f"Digitally Verified Electronic Scorecard | Generated on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')} | Status: Official", font="F1", size=8, rgb=(0.4, 0.4, 0.5))

    return pdf.build()

