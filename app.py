from flask import Flask, render_template, request
import pandas as pd
import sqlite3
import os
from sklearn.ensemble import RandomForestClassifier

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

conn = sqlite3.connect('students.db', check_same_thread=False)
cursor = conn.cursor()

#cursor.execute('DROP TABLE IF EXISTS students')

cursor.execute('''
CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT,
    nilai_bab INTEGER,
    uts INTEGER,
    uas INTEGER,
    proyek INTEGER,
    kehadiran INTEGER,
    keaktifan INTEGER,
    nilai_akhir INTEGER,
    status TEXT,
    probability REAL,
    rekomendasi TEXT
)
''')

conn.commit()

training_data = [
    [95, 90, 85],
    [70, 65, 60],
    [88, 85, 80],
    [60, 55, 50],
    [78, 80, 75],
    [98, 95, 93],
    [50, 45, 40],
    [82, 84, 79]
]

training_label = [
    "Baik",
    "Berisiko",
    "Baik",
    "Berisiko",
    "Cukup",
    "Baik",
    "Berisiko",
    "Cukup"
]

model = RandomForestClassifier()
model.fit(training_data, training_label)

def hitung_nilai_akhir(nilai_bab, uts, uas, proyek, keaktifan):
    nilai_akhir = (
        nilai_bab * 0.30 +
        uts * 0.20 +
        uas * 0.25 +
        proyek * 0.15 +
        keaktifan * 0.10
    )
    return round(nilai_akhir)

def buat_rekomendasi(status):
    if status == "Baik":
        return """
        Strategi pembelajaran: berikan pengayaan melalui project based learning, studi kasus, dan tantangan soal tingkat lanjut.
        Peran guru: fasilitator dan mentor.
        Tindak lanjut: libatkan siswa sebagai tutor sebaya untuk membantu teman yang masih kesulitan.
        """

    elif status == "Cukup":
        return """
        Strategi pembelajaran: gunakan diskusi kelompok kecil, latihan bertahap, video pembelajaran singkat, dan kuis formatif.
        Peran guru: membimbing pemahaman konsep yang belum kuat.
        Tindak lanjut: berikan latihan tambahan dan evaluasi ulang pada materi yang belum dikuasai.
        """

    else:
        return """
        Strategi pembelajaran: lakukan remedial, pembelajaran ulang konsep dasar, pendampingan personal, dan tutor sebaya.
        Peran guru: memberikan scaffolding, contoh konkret, dan pemantauan lebih intensif.
        Tindak lanjut: buat asesmen diagnostik ulang untuk mengetahui kesulitan utama siswa.
        """

def proses_siswa(nama, nilai_bab, uts, uas, proyek, kehadiran, keaktifan):
    nilai_akhir = hitung_nilai_akhir(nilai_bab, uts, uas, proyek, keaktifan)

    status = model.predict([[
        kehadiran,
        keaktifan,
        nilai_akhir
    ]])[0]

    probability = max(model.predict_proba([[
        kehadiran,
        keaktifan,
        nilai_akhir
    ]])[0]) * 100

    rekomendasi = buat_rekomendasi(status)

    cursor.execute('''
    INSERT INTO students
    (nama, nilai_bab, uts, uas, proyek, kehadiran, keaktifan, nilai_akhir, status, probability, rekomendasi)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        nama,
        nilai_bab,
        uts,
        uas,
        proyek,
        kehadiran,
        keaktifan,
        nilai_akhir,
        status,
        round(probability, 2),
        rekomendasi
    ))

    conn.commit()

@app.route('/', methods=['GET', 'POST'])
def home():

    if request.method == 'POST':

        if 'file' in request.files:
            file = request.files['file']

            if file.filename != '':
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(filepath)

                if file.filename.endswith('.csv'):
                    df = pd.read_csv(filepath)
                elif file.filename.endswith('.xlsx'):
                    df = pd.read_excel(filepath)
                else:
                    df = None

                if df is not None:
                    for index, row in df.iterrows():
                        proses_siswa(
                            row['nama'],
                            int(row['nilai_bab']),
                            int(row['uts']),
                            int(row['uas']),
                            int(row['proyek']),
                            int(row['kehadiran']),
                            int(row['keaktifan'])
                        )

        elif 'nama' in request.form:
            proses_siswa(
                request.form['nama'],
                int(request.form['nilai_bab']),
                int(request.form['uts']),
                int(request.form['uas']),
                int(request.form['proyek']),
                int(request.form['kehadiran']),
                int(request.form['keaktifan'])
            )

    cursor.execute("SELECT * FROM students")
    data = cursor.fetchall()

    students = []

    for row in data:
        students.append({
            'nama': row[1],
            'nilai_bab': row[2],
            'uts': row[3],
            'uas': row[4],
            'proyek': row[5],
            'kehadiran': row[6],
            'keaktifan': row[7],
            'nilai_akhir': row[8],
            'status': row[9],
            'probability': row[10],
            'rekomendasi': row[11]
        })

    return render_template(
        'index.html',
        students=students,
        labels=[s['nama'] for s in students],
        nilai_data=[int(s['nilai_akhir']) for s in students]
    )
@app.route('/rekomendasi')
def rekomendasi_guru():

    cursor.execute("SELECT * FROM students")
    data = cursor.fetchall()

    baik_students = []
    cukup_students = []
    risiko_students = []

    for row in data:
        siswa = {
            'nama': row[1],
            'nilai_akhir': row[8],
            'status': row[9]
        }

        if row[9] == "Baik":
            baik_students.append(siswa)
        elif row[9] == "Cukup":
            cukup_students.append(siswa)
        else:
            risiko_students.append(siswa)

    return render_template(
        'rekomendasi.html',
        baik_students=baik_students,
        cukup_students=cukup_students,
        risiko_students=risiko_students
    )
if __name__ == '__main__':
    app.run(debug=True)