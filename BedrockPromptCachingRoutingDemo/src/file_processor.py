import os
import PyPDF2
import docx
import tempfile

class FileProcessor:
    """Class to handle file uploads and text extraction"""
    
    SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.py', '.md', '.json', '.html', '.css', '.js'}
    
    @staticmethod
    def extract_text_from_pdf(file):
        """Extract text from a PDF file"""
        pdf_text = ""
        try:
            # File is already a BytesIO object from bedrock_prompt_routing.py
            pdf_reader = PyPDF2.PdfReader(file)
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                pdf_text += page.extract_text() + "\n\n"
            return pdf_text
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return ""

    @staticmethod
    def extract_text_from_docx(file):
        """Extract text from a DOCX file"""
        try:
            # Save the uploaded file to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
                tmp.write(file.getvalue())
                tmp_path = tmp.name
            
            # Open the temporary file with python-docx
            doc = docx.Document(tmp_path)
            text = [paragraph.text for paragraph in doc.paragraphs]
            
            # Clean up the temporary file
            os.unlink(tmp_path)
            
            return "\n\n".join(text)
        except Exception as e:
            print(f"Error extracting text from DOCX: {str(e)}")
            return ""

    @staticmethod
    def extract_text_from_txt(file):
        """Extract text from a TXT file"""
        try:
            # Handle different file object types
            if hasattr(file, 'getvalue'):
                # Standard file object from Gradio
                return file.getvalue().decode('utf-8')
            elif hasattr(file, 'read'):
                # File-like object with read method
                return file.read().decode('utf-8')
            elif isinstance(file, str):
                # Already a string
                return file
            else:
                # Try to convert to string
                return str(file)
        except Exception as e:
            print(f"Error extracting text from TXT: {str(e)}")
            return ""

    @classmethod
    def process_uploaded_file(cls, uploaded_file):
        """Process an uploaded file and extract text"""
        if uploaded_file is None:
            return ""
        
        # Get file extension safely
        if hasattr(uploaded_file, 'name'):
            file_name = uploaded_file.name
        else:
            # If it's a path string
            file_name = str(uploaded_file)
            
        # Extract extension
        file_ext = os.path.splitext(file_name)[1].lower()
        
        # Process based on extension
        if file_ext == '.pdf':
            return cls.extract_text_from_pdf(uploaded_file)
        elif file_ext == '.docx':
            return cls.extract_text_from_docx(uploaded_file)
        elif file_ext == '.txt' or file_ext == '.py' or file_ext == '.md' or file_ext == '.json':
            return cls.extract_text_from_txt(uploaded_file)
        else:
            print(f"Unsupported file type: {file_ext}")
            # Try to extract as text anyway for common text-based formats
            try:
                return cls.extract_text_from_txt(uploaded_file)
            except:
                return ""

    @classmethod
    def is_supported_file(cls, filename):
        """Check if the file type is supported"""
        ext = os.path.splitext(filename)[1].lower()
        return ext in cls.SUPPORTED_EXTENSIONS