import os
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import exc, UniqueConstraint
from datetime import datetime

# --- 1. App Configuration and Database Setup ---

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_advanced_school_system_secret_key' 

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
    students = db.relationship('Student', backref='section', lazy=True)
    
class Student(db.Model):
    __tablename__ = 'students'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=False)
    reports = db.relationship('Report', backref='student', lazy=True)

class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    reports = db.relationship('Report', backref='course', lazy=True)

class Teacher(db.Model):
    __tablename__ = 'teachers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    reports = db.relationship('Report', backref='teacher', lazy=True) # Συνδέεται απευθείας με Report
    assignments = db.relationship('Assignment', backref='teacher', lazy=True)

class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.Integer, primary_key=True)
    
    section_id = db.Column(db.Integer, db.ForeignKey('sections.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False)
    
    # Σχέσεις για εύκολη πρόσβαση στα ονόματα
    section = db.relationship('Section', backref='assignments', lazy=True)
    course = db.relationship('Course', backref='assignments', lazy=True)
    
    # Περιορισμός: Ένας συνδυασμός Τμήμα-Μάθημα έχει μόνο μία Ανάθεση
    __table_args__ = (UniqueConstraint('section_id', 'course_id', name='_section_course_uc'),)
    
class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    report_text = db.Column(db.Text, nullable=False)
    report_month = db.Column(db.String(7), nullable=False) # Μορφή: YYYY-MM
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Ξένα κλειδιά
    student_id = db.Column(db.Integer, db.ForeignKey('students.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teachers.id'), nullable=False) # ΝΕΟ
    
# --- 3. Database Initialization ---

def init_db():
    with app.app_context():
        try:
            db.create_all()
            print("Database initialized successfully (PostgreSQL or SQLite).")
            
            if not Section.query.first():
                s1 = Section(name='A1')
                s2 = Section(name='B2')
                db.session.add_all([s1, s2])
                db.session.commit()
                
                # Προσθήκη Μαθητών
                db.session.add(Student(name='Μαρία Παπαπέτρου', section_id=s1.id))
                db.session.add(Student(name='Γιάννης Οικονόμου', section_id=s1.id))
                db.session.add(Student(name='Ελένη Καρρά', section_id=s2.id))
                
                # Προσθήκη Μαθημάτων
                c1 = Course(name='Μαθηματικά')
                c2 = Course(name='Λογοτεχνία')
                db.session.add_all([c1, c2, Course(name='Φυσική')])
                db.session.commit()

                # Νέα Προσθήκη: Καθηγητές
                t1 = Teacher(name='Κ. Αθανασίου')
                t2 = Teacher(name='Α. Βασιλείου')
                db.session.add_all([t1, t2])
                db.session.commit()
                
                s1 = Section.query.filter_by(name='A1').first()
                s2 = Section.query.filter_by(name='B2').first()

                # Νέα Προσθήκη: Αναθέσεις (Assignments)
                if not Assignment.query.first():
                    # Ανάθεση: Τμήμα Α1, Μαθηματικά -> Κ. Αθανασίου
                    db.session.add(Assignment(section_id=s1.id, course_id=c1.id, teacher_id=t1.id))
                    # Ανάθεση: Τμήμα Β2, Λογοτεχνία -> Α. Βασιλείου
                    db.session.add(Assignment(section_id=s2.id, course_id=c2.id, teacher_id=t2.id))
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
    students = Student.query.join(Section).order_by(Section.name, Student.name).all()
    courses = Course.query.order_by(Course.name).all()
    sections = Section.query.order_by(Section.name).all()
    teachers = Teacher.query.order_by(Teacher.name).all() # ΝΕΟ
    assignments = Assignment.query.order_by(Assignment.section_id, Assignment.course_id).all() # ΝΕΟ
    
    # Εξαγωγή μοναδικών μηνών για φιλτράρισμα (Μορφή: YYYY-MM)
    months = sorted(list(set(r.report_month for r in reports)), reverse=True)
    
    return render_template(
        'view_reports.html', 
        reports=reports, 
        students=students, 
        courses=courses, 
        sections=sections,
        teachers=teachers, # ΝΕΟ
        assignments=assignments, # ΝΕΟ
        months=months
    )

# [4.2] Προσθήκη ΝΕΑΣ Αναφοράς
@app.route('/add_report', methods=('GET', 'POST'))
def add_report():
    students = Student.query.join(Section).order_by(Section.name, Student.name).all()
    courses = Course.query.order_by(Course.name).all()
    teachers = Teacher.query.order_by(Teacher.name).all() # ΝΕΟ
    
    if request.method == 'POST':
        teacher_id = request.form['teacher_id'] # ΑΛΛΑΓΗ (τώρα στέλνουμε ID)
        student_id = request.form['student_id']
        course_id = request.form['course_id']
        report_text = request.form['report_text']
        report_month = request.form['report_month'] # YYYY-MM
        
        if not all([teacher_id, student_id, course_id, report_text, report_month]):
            flash('Όλα τα πεδία είναι υποχρεωτικά για την υποβολή αναφοράς.', 'error')
            return render_template('add_report.html', students=students, courses=courses, teachers=teachers, now=datetime.utcnow()) # ΝΕΟ
        
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
            teacher_id=teacher_id, # ΑΛΛΑΓΗ
            student_id=student_id, 
            course_id=course_id, 
            report_text=report_text,
            report_month=report_month
        )
        
        try:
            db.session.add(new_report)
            db.session.commit()
            flash(f'Η Αναφορά για τον μήνα {report_month} καταχωρήθηκε επιτυχώς.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Αποτυχία καταχώρησης αναφοράς (Σφάλμα Βάσης): {e}', 'error')
        
        return redirect(url_for('view_reports')) 
    
    return render_template('add_report.html', students=students, courses=courses, teachers=teachers, now=datetime.utcnow()) # ΝΕΟ

# [4.3] Επεξεργασία υπάρχουσας Αναφοράς
@app.route('/edit_report/<int:report_id>', methods=('GET', 'POST'))
def edit_report(report_id):
    report = Report.query.get_or_404(report_id)
    students = Student.query.join(Section).order_by(Section.name, Student.name).all()
    courses = Course.query.order_by(Course.name).all()
    teachers = Teacher.query.order_by(Teacher.name).all() # ΝΕΟ

    if request.method == 'POST':
        report.teacher_id = request.form['teacher_id'] # ΑΛΛΑΓΗ
        report.report_text = request.form['report_text']
        
        db.session.commit()
        flash('Η Αναφορά ενημερώθηκε επιτυχώς.', 'info')
        return redirect(url_for('view_reports'))
        
    return render_template('edit_report.html', report=report, students=students, courses=courses, teachers=teachers) # ΝΕΟ

# [4.4] Διαγραφή Αναφοράς (Δεν αλλάζει)
@app.route('/delete_report/<int:report_id>', methods=('POST',))
def delete_report(report_id):
    report = Report.query.get_or_404(report_id)
    db.session.delete(report)
    db.session.commit()
    flash('Η Αναφορά διαγράφηκε.', 'warning')
    return redirect(url_for('view_reports'))

# [4.5 - 4.8] Διαχείριση Μαθητών/Μαθημάτων/Τμημάτων/Editing (Δεν αλλάζει ουσιαστικά)

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

@app.route('/edit_data', methods=('POST',))
def edit_data():
    entity_type = request.form.get('entity_type')
    entity_id = request.form.get('entity_id')
    new_name = request.form.get('new_name', '').strip()
    new_section_id = request.form.get('new_section_id') 

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
        elif entity_type == 'teacher': # ΝΕΟ: Επεξεργασία Καθηγητή
            item = Teacher.query.get_or_404(entity_id)
            if new_name:
                item.name = new_name
                flash(f'Το όνομα καθηγητή ενημερώθηκε σε "{new_name}".', 'info')
        
        db.session.commit()

    except exc.IntegrityError:
        db.session.rollback()
        flash('Σφάλμα: Η αλλαγή ονόματος θα δημιουργούσε διπλότυπο.', 'error')
    except Exception as e:
        db.session.rollback()
        flash(f'Προέκυψε σφάλμα κατά την ενημέρωση: {e}', 'error')
    
    return redirect(url_for('view_reports'))

# [4.9] Προσθήκη ΝΕΟΥ Καθηγητή (ΝΕΟ)
@app.route('/add_teacher', methods=('POST',))
def add_teacher():
    teacher_name = request.form['teacher_name'].strip()
    if teacher_name:
        if Teacher.query.filter_by(name=teacher_name).first():
            flash(f'Ο Καθηγητής "{teacher_name}" υπάρχει ήδη.', 'error')
        else:
            try:
                new_teacher = Teacher(name=teacher_name)
                db.session.add(new_teacher)
                db.session.commit()
                flash(f'Ο Καθηγητής "{teacher_name}" προστέθηκε επιτυχώς.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Σφάλμα κατά την προσθήκη καθηγητή: {e}', 'error')

    return redirect(url_for('view_reports'))

# [4.10] Ανάθεση Καθηγητή σε Τμήμα/Μάθημα (ΝΕΟ)
@app.route('/assign_teacher', methods=('POST',))
def assign_teacher():
    section_id = request.form['section_id']
    course_id = request.form['course_id']
    teacher_id = request.form['teacher_id']

    if not all([section_id, course_id, teacher_id]):
        flash('Πρέπει να επιλέξετε Τμήμα, Μάθημα και Καθηγητή.', 'error')
        return redirect(url_for('view_reports'))

    try:
        assignment = Assignment.query.filter_by(section_id=section_id, course_id=course_id).first()
        
        if assignment:
            old_teacher_name = assignment.teacher.name
            assignment.teacher_id = teacher_id
            db.session.commit()
            flash(f'Η ανάθεση για το {assignment.section.name}/{assignment.course.name} ενημερώθηκε από {old_teacher_name} στον {assignment.teacher.name}.', 'info')
        else:
            new_assignment = Assignment(section_id=section_id, course_id=course_id, teacher_id=teacher_id)
            db.session.add(new_assignment)
            db.session.commit()
            flash(f'Η ανάθεση {new_assignment.teacher.name} στο Τμήμα {new_assignment.section.name}/{new_assignment.course.name} έγινε επιτυχώς.', 'success')

    except Exception as e:
        db.session.rollback()
        flash(f'Σφάλμα κατά την ανάθεση: {e}', 'error')
        
    return redirect(url_for('view_reports'))

# [4.11] Προβολή Αναφορών για Εκτύπωση (Δεν αλλάζει ουσιαστικά)
@app.route('/print_reports')
def print_reports():
    student_id = request.args.get('student_id')
    month = request.args.get('month')

    if not student_id or not month:
        flash('Πρέπει να επιλέξετε Μαθητή και Μήνα για την εκτύπωση.', 'error')
        return redirect(url_for('view_reports'))

    student = Student.query.get(student_id)
    if not student:
        flash('Ο μαθητής δεν βρέθηκε.', 'error')
        return redirect(url_for('view_reports'))
    
    filtered_reports = Report.query.filter_by(
        student_id=student_id,
        report_month=month
    ).order_by(Report.course_id.asc()).all()
    
    if not filtered_reports:
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
    app.run(debug=True)