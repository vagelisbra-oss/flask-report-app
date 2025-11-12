import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc
from datetime import datetime

# --- 1. App Configuration and Database Setup ---

app = Flask(__name__)
# Add secret key for flashing messages
app.config['SECRET_KEY'] = 'your_advanced_school_system_secret_key' 

# Environment variable configuration for Neon/PostgreSQL
# Uses DATABASE_URL if available, otherwise falls back to SQLite
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///school_system.db')

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- 2. Database Models (Tables) ---

class Section(db.Model):
    __tablename__ = 'sections'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    # Σχέση με μαθητές (ένα τμήμα έχει πολλούς μαθητές)
    students = db.relationship('Student', backref='section', lazy=True)
    
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=False)
    # Σχέση με αναφορές
    reports = db.relationship('Report', backref='student', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    # Σχέση με αναφορές (ένα μάθημα μπορεί να έχει πολλές αναφορές)
    reports = db.relationship('Report', backref='course', lazy=True)

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    teacher_name = db.Column(db.String(100), nullable=False)
    report_text = db.Column(db.Text, nullable=False)
    report_month = db.Column(db.String(7), nullable=False) # Μορφή: YYYY-MM
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ξένα κλειδιά που συνδέουν την αναφορά με συγκεκριμένο μαθητή και μάθημα
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)


# --- 3. Database Initialization ---

def init_db():
    """Δημιουργεί τους πίνακες και προσθέτει αρχικά δεδομένα αν δεν υπάρχουν."""
    with app.app_context():
        try:
            db.create_all()
            print("Database initialized successfully (PostgreSQL or SQLite).")
            
            # Προσθήκη αρχικών δεδομένων αν οι πίνακες είναι κενοί
            if not Section.query.first():
                s1 = Section(name='A1')
                s2 = Section(name='B2')
                db.session.add_all([s1, s2])
                db.session.commit()
                
                db.session.add(Student(name='Μαρία Παπαπέτρου', section_id=s1.id))
                db.session.add(Student(name='Γιάννης Οικονόμου', section_id=s1.id))
                db.session.add(Student(name='Ελένη Καρρά', section_id=s2.id))
                
                db.session.add(Course(name='Μαθηματικά'))
                db.session.add(Course(name='Λογοτεχνία'))
                db.session.add(Course(name='Φυσική'))
                db.session.commit()

        except exc.OperationalError as e:
            print(f"ERROR: Could not connect to the database. Check DATABASE_URL: {e}")

# Κλήση της συνάρτησης αρχικοποίησης
init_db()

# --- 4. Application Routes (ΔΙΑΔΡΟΜΕΣ) ---

# [4.1] Κεντρική Προβολή: Εμφάνιση όλων των δεδομένων και φορμών διαχείρισης
@app.route('/')
def view_reports():
    reports = Report.query.order_by(Report.report_month.desc(), Report.created_at.desc()).all()
    # Ενώνουμε με το Section για να ταξινομήσουμε ανά τμήμα
    students = Student.query.join(Section).order_by(Section.name, Student.name).all()
    courses = Course.query.order_by(Course.name).all()
    sections = Section.query.order_by(Section.name).all()
    
    # Εξαγωγή μοναδικών μηνών για φιλτράρισμα (Μορφή: YYYY-MM)
    months = sorted(list(set(r.report_month for r in reports)), reverse=True)
    
    return render_template(
        'view_reports.html', 
        reports=reports, 
        students=students, 
        courses=courses, 
        sections=sections,
        months=months
    )

# [4.2] Προσθήκη ΝΕΑΣ Αναφοράς
@app.route('/add_report', methods=('GET', 'POST'))
def add_report():
  students = Student.query.join(Section).order_by(Section.name, Student.name).all()
  courses = Course.query.order_by(Course.name).all()
  
  if request.method == 'POST':
    teacher_name = request.form['teacher_name']
    student_id = request.form['student_id']
    course_id = request.form['course_id']
    report_text = request.form['report_text']
    report_month = request.form['report_month'] # YYYY-MM
    
    if not all([teacher_name, student_id, course_id, report_text, report_month]):
      flash('Όλα τα πεδία είναι υποχρεωτικά για την υποβολή αναφοράς.', 'error')
      # Περνάμε το now και στο POST redirect για να αποφύγουμε σφάλμα σε περίπτωση αποτυχίας
      return render_template('add_report.html', students=students, courses=courses, now=datetime.utcnow())
    
    # Έλεγχος για διπλότυπη αναφορά (ίδιος μαθητής/μάθημα/μήνας)
    existing_report = Report.query.filter_by(
      student_id=student_id, 
      course_id=course_id, 
      report_month=report_month
    ).first()

    if existing_report:
      flash(f'Υπάρχει ήδη αναφορά για τον μαθητή αυτό, το μάθημα και τον μήνα {report_month}. Μπορείτε να την επεξεργαστείτε.', 'warning')
      return redirect(url_for('view_reports'))
    
    new_report = Report(
      teacher_name=teacher_name, 
      student_id=student_id, 
      course_id=course_id, 
      report_text=report_text,
      report_month=report_month
    )
    
    # Χειρισμός πιθανού σφάλματος βάσης δεδομένων κατά το commit
    try:
      db.session.add(new_report)
      db.session.commit()
      flash(f'Η Αναφορά για τον μήνα {report_month} καταχωρήθηκε επιτυχώς.', 'success')
    except Exception as e:
      db.session.rollback()
      flash(f'Αποτυχία καταχώρησης αναφοράς (Σφάλμα Βάσης): {e}', 'error')
    
    return redirect(url_for('view_reports')) 
  
  # GET request: ΠΕΡΝΑΜΕ ΤΟ now ΓΙΑ ΝΑ ΠΡΟ-ΣΥΜΠΛΗΡΩΘΕΙ Ο ΜΗΝΑΣ ΣΤΗ ΦΟΡΜΑ
  return render_template('add_report.html', students=students, courses=courses, now=datetime.utcnow())

# [4.3] Επεξεργασία υπάρχουσας Αναφοράς
@app.route('/edit_report/<int:report_id>', methods=('GET', 'POST'))
def edit_report(report_id):
    report = Report.query.get_or_404(report_id)
    students = Student.query.join(Section).order_by(Section.name, Student.name).all()
    courses = Course.query.order_by(Course.name).all()

    if request.method == 'POST':
        # Τα πεδία μήνα, μαθητή και μαθήματος είναι disabled στο HTML, 
        # οπότε ενημερώνουμε μόνο όνομα καθηγητή και κείμενο αναφοράς.
        report.teacher_name = request.form['teacher_name']
        report.report_text = request.form['report_text']
        
        db.session.commit()
        flash('Η Αναφορά ενημερώθηκε επιτυχώς.', 'info')
        return redirect(url_for('view_reports'))
        
    return render_template('edit_report.html', report=report, students=students, courses=courses)

# [4.4] Διαγραφή Αναφοράς
@app.route('/delete_report/<int:report_id>', methods=('POST',))
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash('Η Αναφορά διαγράφηκε.', 'warning')
    return redirect(url_for('view_reports'))

# [4.5] Προσθήκη ΝΕΟΥ Μαθητή (Ανάθεση σε Τμήμα)
@app.route('/add_student', methods=('POST',))
def add_student():
    student_name = request.form['student_name'].strip()
    section_id = request.form['section_id']

    if not student_name or not section_id:
        flash('Το όνομα μαθητή και το τμήμα είναι υποχρεωτικά.', 'error')
        return redirect(url_for('view_reports'))

    try:
        new_student = Student(name=student_name, section_id=section_id)
        db.session.add(new_student)
        db.session.commit()
        flash(f'Ο Μαθητής "{student_name}" προστέθηκε επιτυχώς.', 'success')
    except Exception as e:
        flash(f'Σφάλμα κατά την προσθήκη μαθητή: {e}', 'error')
        db.session.rollback()
        
    return redirect(url_for('view_reports'))

# [4.6] Προσθήκη ΝΕΟΥ Μαθήματος
@app.route('/add_course', methods=('POST',))
def add_course():
    course_name = request.form['course_name'].strip()
    if course_name:
        if Course.query.filter_by(name=course_name).first():
            flash(f'Το Μάθημα "{course_name}" υπάρχει ήδη.', 'error')
        else:
            new_course = Course(name=course_name)
            db.session.add(new_course)
            db.session.commit()
            flash(f'Το Μάθημα "{course_name}" προστέθηκε επιτυχώς.', 'success')
    return redirect(url_for('view_reports'))

# [4.7] Προσθήκη ΝΕΟΥ Τμήματος
@app.route('/add_section', methods=('POST',))
def add_section():
    section_name = request.form['section_name'].strip().upper()
    if section_name:
        if Section.query.filter_by(name=section_name).first():
            flash(f'Το Τμήμα "{section_name}" υπάρχει ήδη.', 'error')
        else:
            new_section = Section(name=section_name)
            db.session.add(new_section)
            db.session.commit()
            flash(f'Το Τμήμα "{section_name}" προστέθηκε επιτυχώς.', 'success')
    return redirect(url_for('view_reports'))


# [4.8] Επεξεργασία δεδομένων (Inline Editing)
@app.route('/edit_data', methods=('POST',))
def edit_data():
    entity_type = request.form.get('entity_type')
    entity_id = request.form.get('entity_id')
    new_name = request.form.get('new_name', '').strip()
    new_section_id = request.form.get('new_section_id') # Μόνο για Μαθητή

    if not entity_id:
        flash('Δεν βρέθηκε ID οντότητας.', 'error')
        return redirect(url_for('view_reports'))

    try:
        if entity_type == 'student':
            item = Student.query.get_or_404(entity_id)
            if new_name:
                item.name = new_name
                flash(f'Το όνομα μαθητή ενημερώθηκε σε "{new_name}".', 'info')
            if new_section_id and int(new_section_id) != item.section_id:
                item.section_id = int(new_section_id)
                flash(f'Ο μαθητής μεταφέρθηκε σε νέο τμήμα.', 'info')

        elif entity_type == 'course':
            item = Course.query.get_or_404(entity_id)
            if new_name:
                item.name = new_name
                flash(f'Το όνομα μαθήματος ενημερώθηκε σε "{new_name}".', 'info')

        elif entity_type == 'section':
            item = Section.query.get_or_404(entity_id)
            if new_name:
                item.name = new_name.upper()
                flash(f'Το όνομα τμήματος ενημερώθηκε σε "{item.name}".', 'info')
        
        db.session.commit()

    except exc.IntegrityError:
        db.session.rollback()
        flash('Σφάλμα: Η αλλαγή ονόματος θα δημιουργούσε διπλότυπο.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Προέκυψε σφάλμα κατά την ενημέρωση: {e}', 'error')
    
    return redirect(url_for('view_reports'))

# [4.9] Προβολή Αναφορών για Εκτύπωση (Συνολική Προβολή)
@app.route('/print_reports')
def print_reports():
    # Λήψη παραμέτρων από το URL (π.χ. /print_reports?student_id=1&month=2024-11)
    student_id = request.args.get('student_id')
    month = request.args.get('month')

    if not student_id or not month:
        flash('Πρέπει να επιλέξετε Μαθητή και Μήνα για την εκτύπωση.', 'error')
        return redirect(url_for('view_reports'))

    # 1. ΕΛΕΓΧΟΣ ΜΑΘΗΤΗ (ΠΡΩΤΑ)
    student = Student.query.get(student_id)
    if not student:
        flash('Ο μαθητής δεν βρέθηκε.', 'error')
        return redirect(url_for('view_reports'))
    
    # 2. Αναζήτηση όλων των αναφορών για τον συγκεκριμένο μαθητή και μήνα
    filtered_reports = Report.query.filter_by(
        student_id=student_id,
        report_month=month
    ).order_by(Report.course_id.asc()).all()
    
    if not filtered_reports:
        # Τώρα είναι ασφαλές να χρησιμοποιήσουμε το student.name
        flash(f'Δεν βρέθηκαν αναφορές για τον {student.name} τον μήνα {month}.', 'warning')
        return redirect(url_for('view_reports'))

    return render_template(
        'print_reports.html', 
        student=student, 
        month=month, 
        reports=filtered_reports
    )

# --- 5. Application Execution ---
if __name__ == '__main__':
    # Τρέχει τοπικά για testing
    app.run(debug=True)