from flask import Flask, render_template, request
from fpdf import FPDF
import base64
import os
import time

app = Flask(__name__)
os.makedirs('pdfs', exist_ok=True)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit', methods=['POST'])
def submit():
    user = request.form.get('user')
    notebook = request.form.get('notebook')
    service_tag = request.form.get('service_tag')
    signature_data = request.form.get('signature') # Base64 Bild

    # PDF generieren
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", size=12)
    
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(0, 10, text="Übergabeprotokoll Hardware", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, text=f"Benutzer: {user}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=f"Notebook-Name: {notebook}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=f"Service Tag: {service_tag}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.cell(0, 10, text="Unterschrift des Benutzers:", new_x="LMARGIN", new_y="NEXT")

    # Unterschrift aus Base64 decodieren und ins PDF einfügen
    if signature_data:
        header, encoded = signature_data.split(",", 1)
        with open("temp_sig.png", "wb") as fh:
            fh.write(base64.b64decode(encoded))
        pdf.image("temp_sig.png", x=10, y=pdf.get_y(), w=80)
        os.remove("temp_sig.png")

    # PDF speichern
    filename = f"pdfs/Uebergabe_{user.replace(' ', '_')}_{int(time.time())}.pdf"
    pdf.output(filename)

    return "Erfolgreich gespeichert! Das Fenster kann geschlossen werden."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
