import os
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy

# --- 1. Ρυθμίσεις Εφαρμογής και Βάσης Δεδομένων ---

app = Flask(__name__)

# Ελέγχει αν υπάρχει η μεταβλητή περιβάλλοντος 'DATABASE_URL' (το URL της Neon).
# Αν δεν υπάρχει (τοπική δοκιμή), χρησιμοποιεί τοπικό SQLite (reports.db).
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///reports.db')

# Αν το URL είναι το 'postgres://...' (π.χ. από παλιά config), το διορθώνουμε σε 'postgresql://...'
# Αυτό είναι απαραίτητο για το SQLAlchemy.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 2. Ορισμός Μοντέλου (Πίνακα) για το SQLAlchemy ---

class Report(db.Model):
    # __tablename__ = 'reports' # Προαιρετικό, αλλά καλό
    id = db.Column(db.Integer, primary_key=True)
    reporter_name = db.Column(db.Text, nullable=False)
    report_text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=db.func.now())

    def __repr__(self):
        return f'<Report {self.id}>'

# 3. Αρχικοποίηση: Δημιουργία των Πινάκων (Table) αν δεν υπάρχουν
# Αυτή η συνάρτηση εκτελείται μία φορά για να δημιουργήσει τη δομή στη Neon
def init_db():
    with app.app_context():
        # Δημιουργεί όλους τους πίνακες που ορίζονται ως Models (Report)
        db.create_all()

# Καλούμε την αρχικοποίηση:
init_db()

# ----------------- 4. ΔΙΑΔΡΟΜΕΣ (ROUTES) ΤΗΣ ΕΦΑΡΜΟΓΗΣ -----------------

# [4.1] ΠΡΟΣΘΗΚΗ ΝΕΑΣ ΑΝΑΦΟΡΑΣ (Route: /add)
@app.route('/add', methods=('GET', 'POST'))
def add_report():
    if request.method == 'POST':
        # Λήψη δεδομένων από τη φόρμα
        name = request.form['reporter_name']
        text = request.form['report_text']

        # Δημιουργία νέου αντικειμένου Report και αποθήκευση
        new_report = Report(reporter_name=name, report_text=text)
        db.session.add(new_report)
        db.session.commit()
        
        return redirect(url_for('view_reports')) 

    # Αν η μέθοδος είναι GET, εμφανίζει τη φόρμα
    return render_template('add_report.html') 

# [4.2] ΠΡΟΒΟΛΗ ΟΛΩΝ ΤΩΝ ΑΝΑΦΟΡΩΝ (Route: / ή /view)
@app.route('/')
@app.route('/view')
def view_reports():
    # Λήψη όλων των αναφορών, με τη νεότερη πρώτη
    reports = Report.query.order_by(Report.created_at.desc()).all()
    
    # Αποστολή των δεδομένων στο HTML template
    return render_template('view_reports.html', reports=reports)

# [4.3] ΕΠΕΞΕΡΓΑΣΙΑ ΑΝΑΦΟΡΑΣ (Route: /edit/<id>)
@app.route('/edit/<int:report_id>', methods=('GET', 'POST'))
def edit_report(report_id):
    # Βρίσκει την αναφορά
    report = Report.query.get_or_404(report_id)
    
    if request.method == 'POST':
        # ΕΝΤΟΛΗ UPDATE: Αλλαγή των δεδομένων στη βάση
        report.reporter_name = request.form['reporter_name']
        report.report_text = request.form['report_text']
        
        db.session.commit()
        return redirect(url_for('view_reports')) # Επιστροφή στη λίστα
        
    # Αν η μέθοδος είναι GET, εμφανίζει τη φόρμα με τα υπάρχοντα δεδομένα
    return render_template('edit_report.html', report=report)

# ----------------- 5. Εκτέλεση Εφαρμογής -----------------
if __name__ == '__main__':
    # Τρέχει τοπικά, για δοκιμές
    app.run(debug=True)