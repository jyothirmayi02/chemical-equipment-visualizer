import sys
import requests

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QFileDialog,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QDialog,
    QLineEdit,
    QFormLayout,
    QDialogButtonBox,
    QFrame,
    QHeaderView,
)
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

BACKEND_BASE = "http://127.0.0.1:8000/api"


# ---------- Login Dialog (asks for username/password once) ----------
class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.username = ""
        self.password = ""

        self.setWindowTitle("Login to API")
        self.setModal(True)
        self.setMinimumWidth(300)

        layout = QVBoxLayout(self)

        title = QLabel("Admin Login")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        layout.addWidget(title)

        subtitle = QLabel("Enter your Django admin credentials to continue.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        form = QFormLayout()

        self.user_edit = QLineEdit()
        self.user_edit.setPlaceholderText("admin")
        form.addRow("Username:", self.user_edit)

        self.pass_edit = QLineEdit()
        self.pass_edit.setPlaceholderText("Password")
        self.pass_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Password:", self.pass_edit)

        layout.addLayout(form)

        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: #b91c1c;")
        layout.addWidget(self.error_label)

        buttons = QDialogButtonBox()
        self.login_button = buttons.addButton("Login", QDialogButtonBox.AcceptRole)
        self.cancel_button = buttons.addButton("Cancel", QDialogButtonBox.RejectRole)
        layout.addWidget(buttons)

        self.login_button.clicked.connect(self.try_login)
        self.cancel_button.clicked.connect(self.reject)

    def try_login(self):
        username = self.user_edit.text().strip()
        password = self.pass_edit.text().strip()

        if not username or not password:
            self.error_label.setText("Please enter both username and password.")
            return

        # test against /api/hello/
        try:
            resp = requests.get(
                f"{BACKEND_BASE}/hello/", auth=(username, password), timeout=5
            )
        except Exception as e:
            self.error_label.setText("Network error. Is backend running?")
            print("Login network error:", e)
            return

        if resp.status_code == 200:
            self.username = username
            self.password = password
            self.accept()
        else:
            self.error_label.setText("Invalid credentials or not authorized.")


# ---------- Main Desktop Window ----------
class MainWindow(QWidget):
    def __init__(self, api_username, api_password):
        super().__init__()
        self.api_username = api_username
        self.api_password = api_password

        self.setWindowTitle("Chemical Equipment Parameter Visualizer (Desktop)")
        self.setMinimumSize(1100, 700)

        self.dataset = None  # latest dataset JSON
        self.history = []    # last 5 datasets list

        # ---------- Layout ----------
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # Title
        title_label = QLabel("Chemical Equipment Parameter Visualizer")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Segoe UI", 16, QFont.Bold))
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("Desktop Dashboard")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("color: #64748b;")
        main_layout.addWidget(subtitle_label)

        # Horizontal line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Top bar: info + buttons
        top_bar = QHBoxLayout()
        self.info_label = QLabel("Upload a CSV to visualize data")
        top_bar.addWidget(self.info_label)

        self.upload_button = QPushButton("Upload CSV")
        self.upload_button.clicked.connect(self.upload_csv)
        top_bar.addWidget(self.upload_button)

        self.pdf_button = QPushButton("Download PDF Report")
        self.pdf_button.setEnabled(False)
        self.pdf_button.clicked.connect(self.download_pdf)
        top_bar.addWidget(self.pdf_button)

        main_layout.addLayout(top_bar)

        # Section title: current dataset
        current_title = QLabel("Current Dataset")
        current_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        main_layout.addWidget(current_title)

        # Summary label
        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("color: #0f172a;")
        main_layout.addWidget(self.summary_label)

        # Table for preview rows
        self.table = QTableWidget()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.table)

        # Chart area
        chart_title = QLabel("Equipment Type Distribution")
        chart_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        main_layout.addWidget(chart_title)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        main_layout.addWidget(self.canvas)

        # Last 5 datasets section
        history_title = QLabel("Last 5 Uploaded Datasets")
        history_title.setFont(QFont("Segoe UI", 11, QFont.Bold))
        main_layout.addWidget(history_title)

        self.history_table = QTableWidget()
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        main_layout.addWidget(self.history_table)

        # Initial history load
        self.fetch_history()

    # ---------- Helpers ----------
    def _auth(self):
        return (self.api_username, self.api_password)

    # ---------- Upload CSV ----------
    def upload_csv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select CSV", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        self.info_label.setText("Uploading...")
        QApplication.processEvents()

        try:
            with open(file_path, "rb") as f:
                files = {"file": f}
                resp = requests.post(
                    f"{BACKEND_BASE}/upload/", files=files, auth=self._auth()
                )
        except Exception as e:
            self.info_label.setText("Network error while uploading.")
            QMessageBox.critical(self, "Error", f"Network error:\n{e}")
            return

        if resp.status_code not in (200, 201):
            self.info_label.setText("Upload failed.")
            QMessageBox.warning(
                self,
                "Upload Failed",
                f"Status: {resp.status_code}\nResponse:\n{resp.text}",
            )
            return

        self.dataset = resp.json()
        self.info_label.setText(f"Uploaded: {self.dataset.get('name', 'dataset')}")
        self.pdf_button.setEnabled(True)

        # Update current dataset UI
        self.show_summary()
        self.show_table()
        self.show_chart()

        # Refresh last 5 datasets
        self.fetch_history()

    # ---------- Current dataset summary ----------
    def show_summary(self):
        if not self.dataset or "summary" not in self.dataset:
            self.summary_label.setText("")
            return

        s = self.dataset["summary"]
        text = (
            f"Total Count: {s.get('total_count', '-')}   |   "
            f"Avg Flowrate: {s.get('average_flowrate', 0):.2f}   |   "
            f"Avg Pressure: {s.get('average_pressure', 0):.2f}   |   "
            f"Avg Temperature: {s.get('average_temperature', 0):.2f}"
        )
        self.summary_label.setText(text)

    # ---------- Preview table ----------
    def show_table(self):
        rows = self.dataset.get("preview_rows", [])
        if not rows:
            self.table.clear()
            self.table.setRowCount(0)
            self.table.setColumnCount(0)
            return

        columns = list(rows[0].keys())
        self.table.setRowCount(len(rows))
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)

        for i, row in enumerate(rows):
            for j, col in enumerate(columns):
                value = row.get(col, "")
                self.table.setItem(i, j, QTableWidgetItem(str(value)))

    # ---------- Chart ----------
    def show_chart(self):
        self.figure.clear()
        ax = self.figure.add_subplot(111)

        if not self.dataset or "summary" not in self.dataset:
            self.canvas.draw()
            return

        dist = self.dataset["summary"].get("type_distribution", {})
        labels = list(dist.keys())
        counts = list(dist.values())

        ax.bar(labels, counts)
        ax.set_title("Equipment Count by Type")
        ax.set_xlabel("Type")
        ax.set_ylabel("Count")

        self.canvas.draw()

    # ---------- PDF Download ----------
    def download_pdf(self):
        if not self.dataset or "id" not in self.dataset:
            QMessageBox.information(
                self, "No Dataset", "Please upload a dataset before downloading PDF."
            )
            return

        dataset_id = self.dataset["id"]

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save PDF Report",
            f"dataset_{dataset_id}_report.pdf",
            "PDF Files (*.pdf)",
        )
        if not save_path:
            return

        try:
            resp = requests.get(
                f"{BACKEND_BASE}/datasets/{dataset_id}/report/",
                auth=self._auth(),
                stream=True,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Network error while downloading:\n{e}")
            return

        if resp.status_code != 200:
            QMessageBox.warning(
                self,
                "Download Failed",
                f"Status: {resp.status_code}\nResponse:\n{resp.text}",
            )
            return

        try:
            with open(save_path, "wb") as f:
                for chunk in resp.iterContent(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving file:\n{e}")
            return

        QMessageBox.information(
            self, "Success", f"PDF report saved successfully:\n{save_path}"
        )

    # ---------- History (last 5 datasets) ----------
    def fetch_history(self):
        try:
            resp = requests.get(f"{BACKEND_BASE}/datasets/", auth=self._auth())
        except Exception as e:
            print("History fetch error:", e)
            return

        if resp.status_code != 200:
            print("History fetch failed:", resp.status_code, resp.text)
            return

        self.history = resp.json()
        self.show_history()

    def show_history(self):
        data = self.history
        if not data:
            self.history_table.clear()
            self.history_table.setRowCount(0)
            self.history_table.setColumnCount(0)
            return

        columns = ["Name", "Uploaded At", "Total Count"]
        self.history_table.setRowCount(len(data))
        self.history_table.setColumnCount(len(columns))
        self.history_table.setHorizontalHeaderLabels(columns)

        for i, d in enumerate(data):
            name = d.get("name", "")
            uploaded_at = d.get("uploaded_at", "")
            total = "-"
            summary = d.get("summary")
            if isinstance(summary, dict):
                total = summary.get("total_count", "-")

            self.history_table.setItem(i, 0, QTableWidgetItem(str(name)))
            self.history_table.setItem(i, 1, QTableWidgetItem(str(uploaded_at)))
            self.history_table.setItem(i, 2, QTableWidgetItem(str(total)))


if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Simple global stylesheet for nicer look
    app.setStyleSheet("""
    QWidget {
        font-family: "Segoe UI", sans-serif;
        font-size: 11pt;
        background-color: #f3f4f6;
    }
    QTableWidget {
        background-color: #ffffff;
        border: 1px solid #e5e7eb;
        gridline-color: #e5e7eb;
    }
    QHeaderView::section {
        background-color: #e5e7eb;
        padding: 4px;
        border: 1px solid #d1d5db;
        font-weight: 600;
    }
    QPushButton {
        background-color: #4f46e5;
        color: white;
        border-radius: 6px;
        padding: 6px 12px;
    }
    QPushButton:hover {
        background-color: #4338ca;
    }
    QPushButton:disabled {
        background-color: #9ca3af;
    }
    QLineEdit {
        background-color: #ffffff;
        border: 1px solid #d1d5db;
        border-radius: 4px;
        padding: 4px 6px;
    }
    QLabel {
        color: #111827;
    }
    """)

    # Show login dialog first
    login_dialog = LoginDialog()
    if login_dialog.exec_() != QDialog.Accepted:
        sys.exit(0)

    main_win = MainWindow(login_dialog.username, login_dialog.password)
    main_win.show()
    sys.exit(app.exec_())
