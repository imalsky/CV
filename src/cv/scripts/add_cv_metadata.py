from pdfrw import PdfReader, PdfWriter

def main():
    """
    write some metadata
    """
    filepath = "../../../../PDFs/CV_mcdanal.pdf"
    trailer = PdfReader(filepath)
    trailer.Info.Title = """Isaac Malsky's CV"""
    trailer.Info.Author = 'Isaac Malsky'
    trailer.Info.Subject = 'PhD Candidate in Astronomy at the University of Michigan'
    PdfWriter(filepath, trailer=trailer).write()
    
if __name__ == '__main__':
    main()
