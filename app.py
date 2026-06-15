from flask import Flask, render_template, request
import pandas as pd
import sqlite3
import os
import numpy as np
from sklearn.cluster import KMeans

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# =========================
# DATABASE
# =========================

conn = sqlite3.connect(
    "students.db",
    check_same_thread=False
)

cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS students(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nama TEXT,
    rt_ph REAL,
    uhb REAL,
    rpt REAL,
    nilai_akhir REAL,
    status TEXT,
    rekomendasi TEXT
)
""")

conn.commit()

# =========================
# FUNGSI
# =========================

def hitung_nilai_akhir(rt_ph, uhb, rpt):
    return round(
        (rt_ph + uhb + rpt) / 3,
        2
    )


def cari_kolom(df, keyword):

    keyword = keyword.upper()

    for row in range(min(10, len(df))):

        for col in range(df.shape[1]):

            nilai = str(
                df.iloc[row, col]
            ).upper()

            if keyword in nilai:
                return col

    return None


def simpan_siswa(
        nama,
        rt_ph,
        uhb,
        rpt):

    nilai_akhir = hitung_nilai_akhir(
        rt_ph,
        uhb,
        rpt
    )

    cursor.execute("""
    INSERT INTO students(
        nama,
        rt_ph,
        uhb,
        rpt,
        nilai_akhir,
        status,
        rekomendasi
    )
    VALUES(?,?,?,?,?,?,?)
    """,
    (
        nama,
        rt_ph,
        uhb,
        rpt,
        nilai_akhir,
        "Belum Diproses",
        "-"
    ))

    conn.commit()


def proses_kmeans():

    cursor.execute("""
    SELECT
        id,
        rt_ph,
        uhb,
        rpt,
        nilai_akhir
    FROM students
    """)

    data = cursor.fetchall()

    if len(data) < 3:
        return

    X = []

    for row in data:

        X.append([
            row[1],
            row[2],
            row[3],
            row[4]
        ])

    X = np.array(X)

    kmeans = KMeans(
        n_clusters=3,
        random_state=42,
        n_init=10
    )

    labels = kmeans.fit_predict(X)

    centers = kmeans.cluster_centers_

    rata_cluster = [
        np.mean(c)
        for c in centers
    ]

    urutan = np.argsort(rata_cluster)

    rendah = urutan[0]
    sedang = urutan[1]
    tinggi = urutan[2]

    for i, row in enumerate(data):

        cluster = labels[i]

        if cluster == tinggi:

            status = "Tinggi"

            rekomendasi = """
            Pengayaan,
            proyek lanjutan,
            tutor sebaya,
            dan soal HOTS.
            """

        elif cluster == sedang:

            status = "Sedang"

            rekomendasi = """
            Latihan bertahap,
            diskusi kelompok,
            dan penguatan konsep.
            """

        else:

            status = "Rendah"

            rekomendasi = """
            Remedial,
            pendampingan intensif,
            dan pembelajaran ulang.
            """

        cursor.execute("""
        UPDATE students
        SET
        status=?,
        rekomendasi=?
        WHERE id=?
        """,
        (
            status,
            rekomendasi,
            row[0]
        ))

    conn.commit()

# =========================
# ROUTE HOME
# =========================

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        cursor.execute(
            "DELETE FROM students"
        )
        conn.commit()

        file = request.files["file"]

        if file.filename != "":

            filepath = os.path.join(
                app.config["UPLOAD_FOLDER"],
                file.filename
            )

            file.save(filepath)

            df = pd.read_excel(
                filepath,
                header=None
            )

            col_nama = cari_kolom(df, "NAMA")
            col_rtph = cari_kolom(df, "RT PH")
            col_uhb = cari_kolom(df, "UHB")
            col_rpt = cari_kolom(df, "RPT")

            print(
                col_nama,
                col_rtph,
                col_uhb,
                col_rpt
            )

            for i in range(4, len(df)):

                try:

                    nama = df.iloc[i, col_nama]

                    if pd.isna(nama):
                        continue

                    rt_ph = float(
                        df.iloc[i, col_rtph]
                    )

                    uhb = float(
                        df.iloc[i, col_uhb]
                    )

                    rpt = float(
                        df.iloc[i, col_rpt]
                    )

                    simpan_siswa(
                        str(nama),
                        rt_ph,
                        uhb,
                        rpt
                    )

                except:
                    continue

            proses_kmeans()

    cursor.execute(
        "SELECT * FROM students"
    )

    data = cursor.fetchall()

    students = []

    for row in data:

        students.append({

            "nama": row[1],
            "rt_ph": row[2],
            "uhb": row[3],
            "rpt": row[4],
            "nilai_akhir": row[5],
            "status": row[6],
            "rekomendasi": row[7]

        })

    labels = [s["nama"] for s in students]
    nilai_data = [s["nilai_akhir"] for s in students]

    print("LABELS =", labels)
    print("NILAI =", nilai_data)

    return render_template(
        "index.html",
        students=students,
        labels=labels,
        nilai_data=nilai_data
)

# =========================
# REKOMENDASI
# =========================

@app.route("/rekomendasi")
def rekomendasi():

    cursor.execute("SELECT * FROM students")
    rows = cursor.fetchall()

    tinggi_students = []
    sedang_students = []
    rendah_students = []

    for row in rows:

        siswa = {
            "nama": row[1],
            "rt_ph": row[2],
            "pts": row[3],      # UHB/PTS
            "rpt": row[4],
            "nilai_akhir": row[5],
            "status": row[6],
            "rekomendasi": row[7]
        }

        if row[6] == "Tinggi":
            tinggi_students.append(siswa)

        elif row[6] == "Sedang":
            sedang_students.append(siswa)

        elif row[6] == "Rendah":
            rendah_students.append(siswa)

    return render_template(
        "rekomendasi.html",
        tinggi_students=tinggi_students,
        sedang_students=sedang_students,
        rendah_students=rendah_students
    )

if __name__ == "__main__":
    app.run(debug=True)