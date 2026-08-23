from pypdf import PdfReader

def extract_text(uploaded_file):
    name = uploaded_file.name.lower()

    if name.endswith('.txt'):
        return uploaded_file.read().decode('utf-8', errors='ignore')

    if name.endswith('.pdf'):
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)

    raise ValueError("Unsupported file format. Please upload a .txt or .pdf file.")


