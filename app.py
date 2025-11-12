import sqlite3
from flask import Flask, render_template, request, redirect, url_for

# 1. Ρυθμίσεις Εφαρμογής και Βάσης Δεδομένων
app = Flask(__name__)
DATABASE = 'reports.db' # Το όνομα του αρχείου SQLite

# 2. Σύνδεση με τη Βάση Δεδομένων (SQLite)
def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    # Αυτό επιτρέπει την πρόσβαση στις στήλες με το όνομά τους (π.χ. report['id'])
    conn.row_factory = sqlite3.Row 
    return conn

# 3. Αρχικοποίηση: Δημιουργία του Πίνακα (Table) αν δεν υπάρχει
def init_db():
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            reporter_name TEXT NOT NULL,
            report_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

init_db() # Εκτελείται όταν ξεκινάει η εφαρμογή

# ----------------- 4. ΔΙΑΔΡΟΜΕΣ (ROUTES) ΤΗΣ ΕΦΑΡΜΟΓΗΣ -----------------

# [4.1] ΠΡΟΣΘΗΚΗ ΝΕΑΣ ΑΝΑΦΟΡΑΣ (Route: /add)
@app.route('/add', methods=('GET', 'POST'))
def add_report():
    if request.method == 'POST':
        # Λήψη δεδομένων από τη φόρμα
        name = request.form['reporter_name']
        text = request.form['report_text']

        # Αποθήκευση στη βάση (SQL INSERT)
        conn = get_db_connection()
        conn.execute('INSERT INTO reports (reporter_name, report_text) VALUES (?, ?)',
                     (name, text))
        conn.commit()
        conn.close()
        return redirect(url_for('view_reports')) 

    # Αν η μέθοδος είναι GET, εμφανίζει τη φόρμα
    return render_template('add_report.html') 

# [4.2] ΠΡΟΒΟΛΗ ΟΛΩΝ ΤΩΝ ΑΝΑΦΟΡΩΝ (Route: / ή /view)
@app.route('/')
@app.route('/view')
def view_reports():
    conn = get_db_connection()
    # Λήψη όλων των αναφορών, με τη νεότερη πρώτη
    reports = conn.execute('SELECT * FROM reports ORDER BY created_at DESC').fetchall()
    conn.close()
    
    # Αποστολή των δεδομένων στο HTML template
    return render_template('view_reports.html', reports=reports)

# [4.3] ΕΠΕΞΕΡΓΑΣΙΑ ΑΝΑΦΟΡΑΣ (Route: /edit/<id>)
@app.route('/edit/<int:report_id>', methods=('GET', 'POST'))
def edit_report(report_id):
    conn = get_db_connection()
    # Βρίσκει την αναφορά
    report = conn.execute('SELECT * FROM reports WHERE id = ?', (report_id,)).fetchone()
    
    if report is None:
        conn.close()
        return "Αναφορά δεν βρέθηκε", 404
        
    if request.method == 'POST':
        # ΕΝΤΟΛΗ UPDATE: Αλλαγή των δεδομένων στη βάση
        new_name = request.form['reporter_name']
        new_text = request.form['report_text']
        
        conn.execute('UPDATE reports SET reporter_name = ?, report_text = ? WHERE id = ?',
                     (new_name, new_text, report_id))
        conn.commit()
        conn.close()
        return redirect(url_for('view_reports')) # Επιστροφή στη λίστα
        
    conn.close()
    # Αν η μέθοδος είναι GET, εμφανίζει τη φόρμα με τα υπάρχοντα δεδομένα
    return render_template('edit_report.html', report=report)

# ----------------- 5. Εκτέλεση Εφαρμογής -----------------
if __name__ == '__main__':
    # Τρέχει τοπικά, για δοκιμές
    app.run(debug=True)