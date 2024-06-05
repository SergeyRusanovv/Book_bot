import fitz


def store_pdf_content(pdf_path):
    with fitz.open(pdf_path) as pdf:
        text = ""
        for page in pdf:
            text += page.get_text()

    print(text)

store_pdf_content("Чистая_архитектура.pdf")
