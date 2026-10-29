from pypdf import PdfReader

def extract_pages(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith('.txt'):
        return [(None, uploaded_file.read().decode('utf-8', errors='ignore'))]

    if name.endswith('.pdf'):
        reader = PdfReader(uploaded_file)
        return [
            (page_number, page.extract_text() or "")
            for page_number, page in enumerate(reader.pages, start=1)
        ]

    raise ValueError("Unsupported file format. Please upload a .txt or .pdf file.")


def extract_text(uploaded_file):
    return "\n".join(text for _page_number, text in extract_pages(uploaded_file))


