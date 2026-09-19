import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from PIL import Image, ImageDraw, ImageFont

def generate_sample_documents():
    data_dir = Path("./sample_data")
    data_dir.mkdir(parents=True, exist_ok=True)

    # 1. Generate sample_clean_exam.pdf (Clean MCQ with inline Answer Key)
    clean_pdf_path = data_dir / "sample_clean_exam.pdf"
    c = canvas.Canvas(str(clean_pdf_path), pagesize=letter)
    
    # Page 1
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "Pragati Bharati Computer Science Assessment 2026")
    c.setFont("Helvetica", 10)
    c.drawString(50, 735, "Total Questions: 3  |  Time: 30 Mins  |  Marks: 30")
    c.line(50, 725, 550, 725)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 690, "1. What is the time complexity of searching in a balanced Binary Search Tree?")
    c.setFont("Helvetica", 10)
    c.drawString(70, 670, "A) O(1)")
    c.drawString(70, 650, "B) O(log n)")
    c.drawString(70, 630, "C) O(n)")
    c.drawString(70, 610, "D) O(n log n)")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 560, "2. Which of the following HTTP status codes indicates 'Unauthorized'?")
    c.setFont("Helvetica", 10)
    c.drawString(70, 540, "A) 200 OK")
    c.drawString(70, 520, "B) 400 Bad Request")
    c.drawString(70, 500, "C) 401 Unauthorized")
    c.drawString(70, 480, "D) 404 Not Found")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 430, "3. In relational databases, ACID property 'I' stands for:")
    c.setFont("Helvetica", 10)
    c.drawString(70, 410, "A) Integrity")
    c.drawString(70, 390, "B) Isolation")
    c.drawString(70, 370, "C) Indexing")
    c.drawString(70, 350, "D) Iteration")

    # Inline Answer Key Section
    c.line(50, 300, 550, 300)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 280, "Answer Key & Solutions")
    c.setFont("Helvetica", 10)
    c.drawString(50, 260, "1. B")
    c.drawString(50, 240, "2. C")
    c.drawString(50, 220, "3. B")

    c.showPage()
    c.save()
    print(f"Created: {clean_pdf_path}")

    # 2. Generate sample_cross_page_split.pdf (Question 2 split across Page 1 & Page 2)
    split_pdf_path = data_dir / "sample_cross_page_split.pdf"
    c = canvas.Canvas(str(split_pdf_path), pagesize=letter)
    
    # Page 1
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "Pragati Bharati Advanced Systems Exam - Cross-Page Test")
    c.line(50, 735, 550, 735)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 700, "1. Which protocol is primarily used for secure web browsing?")
    c.setFont("Helvetica", 10)
    c.drawString(70, 680, "A) HTTP")
    c.drawString(70, 660, "B) HTTPS")
    c.drawString(70, 640, "C) FTP")
    c.drawString(70, 620, "D) SMTP")

    # Question 2 begins near bottom of Page 1
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 120, "2. Consider a distributed message queue like Redis or Celery. When a worker crashes")
    c.drawString(50, 100, "during task execution, which acknowledgment mechanism guarantees at-least-once delivery?")
    c.setFont("Helvetica", 10)
    c.drawString(70, 80, "A) Fire and forget without acknowledgment")
    c.drawString(70, 60, "B) Automatic ack before task start")
    
    c.showPage()  # PAGE BREAK!

    # Page 2: Question 2 options continue!
    c.setFont("Helvetica", 10)
    c.drawString(70, 750, "C) Explicit consumer ACK upon successful task completion")
    c.drawString(70, 730, "D) Decreasing queue timeout to zero")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, 670, "3. What is the default port for PostgreSQL server?")
    c.setFont("Helvetica", 10)
    c.drawString(70, 650, "A) 3306")
    c.drawString(70, 630, "B) 6379")
    c.drawString(70, 610, "C) 5432")
    c.drawString(70, 590, "D) 8080")

    # Answer Key on Page 2
    c.line(50, 530, 550, 530)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 510, "Answer Key")
    c.setFont("Helvetica", 10)
    c.drawString(50, 490, "1. B")
    c.drawString(50, 470, "2. C")
    c.drawString(50, 450, "3. C")

    c.showPage()
    c.save()
    print(f"Created: {split_pdf_path}")

    # 3. Generate sample_answer_key.pdf (Standalone Answer Key document for related docs demo)
    key_pdf_path = data_dir / "sample_answer_key.pdf"
    c = canvas.Canvas(str(key_pdf_path), pagesize=letter)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, 750, "Official Examination Answer Key - Standalone Document")
    c.line(50, 735, 550, 735)

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, 700, "Answer Key & Verification Codes")
    c.setFont("Helvetica", 11)
    c.drawString(50, 670, "Question 1: B (Logarithmic time)")
    c.drawString(50, 640, "Question 2: C (401 Unauthorized status)")
    c.drawString(50, 610, "Question 3: B (Isolation prevents dirty reads)")
    c.showPage()
    c.save()
    print(f"Created: {key_pdf_path}")

    # 4. Generate sample_scanned_exam.png (Image scan simulation)
    img_path = data_dir / "sample_scanned_exam.png"
    img = Image.new("RGB", (800, 600), color=(248, 248, 246))
    d = ImageDraw.Draw(img)
    d.text((40, 30), "PRAGATI BHARATI GENERAL KNOWLEDGE (SCANNED SHEET)", fill=(30, 30, 30))
    d.line([(40, 55), (760, 55)], fill=(120, 120, 120), width=2)
    d.text((40, 90), "1. What is the capital of India?", fill=(20, 20, 20))
    d.text((60, 120), "A) Mumbai", fill=(50, 50, 50))
    d.text((60, 145), "B) New Delhi", fill=(50, 50, 50))
    d.text((60, 170), "C) Kolkata", fill=(50, 50, 50))
    d.text((60, 195), "D) Bengaluru", fill=(50, 50, 50))
    img.save(str(img_path))
    print(f"Created: {img_path}")

    # 5. Generate sample_invalid.txt (Unsupported file for error validation test)
    invalid_path = data_dir / "sample_invalid.txt"
    with open(invalid_path, "w", encoding="utf-8") as f:
        f.write("This is an unhandled plain text file intended to test 400 Bad Request error response.")
    print(f"Created: {invalid_path}")

if __name__ == "__main__":
    generate_sample_documents()
