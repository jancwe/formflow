from flask import Flask, render_template, request, send_from_directory
from fpdf import FPDF
import base64
import os
import time
import uuid
from datetime import date

app = Flask(__name__)
os.makedirs('pdfs', exist_ok=True)

@app.route('/', methods=['GET', 'POST'])
def index():
    data = {}
    if request.method == 'POST':
        data = request.form
    # Aktuelles Datum im Format YYYY-MM-DD für das Datumfeld
    date_today = date.today().isoformat()
    return render_template('index.html', data=data, date_today=date_today)

@app.route('/preview', methods=['POST'])
def preview():
    user = request.form.get('user')
    notebook = request.form.get('notebook')
    service_tag = request.form.get('service_tag')
    handover_date = request.form.get('handover_date')
    signature_data = request.form.get('signature')

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("helvetica", style="B", size=16)
    pdf.cell(0, 10, text="Übergabeprotokoll Hardware", new_x="LMARGIN", new_y="NEXT", align='C')
    pdf.ln(10)
    
    pdf.set_font("helvetica", size=12)
    pdf.cell(0, 10, text=f"Benutzer: {user}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=f"Notebook-Name: {notebook}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=f"Service Tag: {service_tag}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 10, text=f"Übergabedatum: {handover_date}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(10)
    pdf.cell(0, 10, text="Unterschrift des Benutzers:", new_x="LMARGIN", new_y="NEXT")

    if signature_data:
        header, encoded = signature_data.split(",", 1)
        temp_sig_filename = f"temp_sig_{uuid.uuid4().hex}.png"
        with open(temp_sig_filename, "wb") as fh:
            fh.write(base64.b64decode(encoded))
        pdf.image(temp_sig_filename, x=10, y=pdf.get_y(), w=80)
        os.remove(temp_sig_filename)

    file_id = uuid.uuid4().hex
    temp_filename = f"pdfs/temp_{file_id}.pdf"
    pdf.output(temp_filename)

    return render_template('preview.html', 
                           uuid=file_id, 
                           user=user, 
                           notebook=notebook, 
                           service_tag=service_tag, 
                           handover_date=handover_date,
                           signature=signature_data)

@app.route('/pdf/<filename>')
def serve_pdf(filename):
    return send_from_directory('pdfs', filename)

@app.route('/confirm/<file_id>', methods=['POST'])
def confirm(file_id):
    user = request.form.get('user')
    temp_filename = f"pdfs/temp_{file_id}.pdf"
    final_filename = f"pdfs/Uebergabe_{user.replace(' ', '_')}_{int(time.time())}.pdf"
    
    if os.path.exists(temp_filename):
        os.rename(temp_filename, final_filename)
        return render_template('success.html')
    return "Fehler: Temporäre Datei nicht gefunden.", 400

@app.route('/edit/<file_id>', methods=['POST'])
def edit(file_id):
    temp_filename = f"pdfs/temp_{file_id}.pdf"
    if os.path.exists(temp_filename):
        os.remove(temp_filename)
    return render_template('index.html', data=request.form)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
