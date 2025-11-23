import React, { useState, useEffect } from "react";
import axios from "axios";
import { Bar } from "react-chartjs-2";
import "./App.css";

import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
} from "chart.js";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

const backendUrl = "http://127.0.0.1:8000/api";

function App() {
  // Login/auth state
  const [loginUsername, setLoginUsername] = useState("");
  const [loginPassword, setLoginPassword] = useState("");
  const [auth, setAuth] = useState(null); // { username, password }
  const [loginError, setLoginError] = useState("");

  // App state
  const [file, setFile] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const axiosAuthConfig = auth
    ? {
        auth: {
          username: auth.username,
          password: auth.password,
        },
      }
    : {};

  // ---------- LOGIN ----------
  const handleLogin = async (e) => {
    e.preventDefault();
    setLoginError("");
    setError("");

    if (!loginUsername || !loginPassword) {
      setLoginError("Please enter username and password.");
      return;
    }

    // Only allow 'admin' user to log in
    if (loginUsername !== "admin") {
      setLoginError("Only 'admin' user is allowed to access this dashboard.");
      return;
    }

    try {
      // Test credentials against /hello/
      await axios.get(`${backendUrl}/hello/`, {
        auth: {
          username: loginUsername,
          password: loginPassword,
        },
      });

      // If successful, store auth
      setAuth({ username: loginUsername, password: loginPassword });
      setLoginError("");
      setDataset(null);
      setHistory([]);
    } catch (err) {
      console.error("Login error:", err);
      setLoginError("Invalid credentials or backend not running.");
      setAuth(null);
    }
  };

  // ---------- LOGOUT ----------
  const handleLogout = () => {
    setAuth(null);
    setDataset(null);
    setHistory([]);
    setFile(null);
    setError("");
    setLoginUsername("");
    setLoginPassword("");
  };

  // ---------- FILE UPLOAD ----------
  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
  };

  const handleUpload = async () => {
    setError("");
    if (!auth) {
      setError("Please login first.");
      return;
    }
    if (!file) {
      setError("Please select a CSV file first.");
      return;
    }

    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await axios.post(`${backendUrl}/upload/`, formData, {
        ...axiosAuthConfig,
        headers: {
          "Content-Type": "multipart/form-data",
        },
      });

      console.log("Upload response:", res.data);
      setDataset(res.data);
      fetchHistory();
    } catch (err) {
      console.error("Upload error:", err);
      setDataset(null);
      setError(
        err.response?.data?.error ||
          err.response?.data?.detail ||
          "Upload failed. Check backend & CSV columns."
      );
    } finally {
      setIsLoading(false);
    }
  };

  // ---------- HISTORY ----------
  const fetchHistory = async () => {
    if (!auth) return;
    try {
      const res = await axios.get(`${backendUrl}/datasets/`, axiosAuthConfig);
      console.log("History response:", res.data);
      setHistory(res.data);
    } catch (err) {
      console.error("History error:", err);
    }
  };

  useEffect(() => {
    if (auth) {
      fetchHistory();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [auth]);

  // ---------- HELPERS ----------
  const getChartData = () => {
    if (!dataset || !dataset.summary) return null;
    const dist = dataset.summary.type_distribution || {};
    const labels = Object.keys(dist);
    const counts = Object.values(dist);

    return {
      labels,
      datasets: [
        {
          label: "Equipment Count by Type",
          data: counts,
        },
      ],
    };
  };

  const renderSummary = () => {
    if (!dataset || !dataset.summary) return <p>No dataset loaded yet.</p>;
    const s = dataset.summary;
    return (
      <div className="summary-grid">
        <div className="summary-card">
          <div className="summary-label">Total Equipment</div>
          <div className="summary-value">{s.total_count ?? "-"}</div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Avg Flowrate</div>
          <div className="summary-value">
            {s.average_flowrate !== undefined
              ? s.average_flowrate.toFixed(2)
              : "-"}
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Avg Pressure</div>
          <div className="summary-value">
            {s.average_pressure !== undefined
              ? s.average_pressure.toFixed(2)
              : "-"}
          </div>
        </div>
        <div className="summary-card">
          <div className="summary-label">Avg Temperature</div>
          <div className="summary-value">
            {s.average_temperature !== undefined
              ? s.average_temperature.toFixed(2)
              : "-"}
          </div>
        </div>
      </div>
    );
  };

  const renderTable = () => {
    if (!dataset || !dataset.preview_rows || dataset.preview_rows.length === 0) {
      return <p>No preview data available.</p>;
    }

    const columns = Object.keys(dataset.preview_rows[0] || {});

    return (
      <table>
        <thead>
          <tr>
            {columns.map((col) => (
              <th key={col}>{col}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {dataset.preview_rows.map((row, idx) => (
            <tr key={idx}>
              {columns.map((col) => (
                <td key={col}>{row[col]}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    );
  };

  // ---------- PDF DOWNLOAD ----------
  const downloadPDF = async () => {
    if (!dataset || !dataset.id) {
      setError("No dataset available to download PDF.");
      return;
    }

    try {
      const response = await axios.get(
        `${backendUrl}/datasets/${dataset.id}/report/`,
        {
          ...axiosAuthConfig,
          responseType: "blob", // so we receive a file
        }
      );

      const blob = new Blob([response.data], { type: "application/pdf" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dataset_${dataset.id}_report.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("PDF download error:", err);
      setError("Failed to download PDF report.");
    }
  };

  const chartData = getChartData();

  // ---------- RENDER: LOGIN PAGE ----------
  if (!auth) {
    return (
      <div className="login-root">
        <div className="login-card">
          <h1 className="login-title">Admin Login</h1>
          <p className="login-subtitle">
            Only the <strong>admin</strong> user can access the dashboard.
          </p>

          {loginError && <div className="error-box">{loginError}</div>}

          <form className="login-form" onSubmit={handleLogin}>
            <div>
              <label>Username</label>
              <input
                type="text"
                value={loginUsername}
                onChange={(e) => setLoginUsername(e.target.value)}
                placeholder="admin"
              />
            </div>
            <div>
              <label>Password</label>
              <input
                type="password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                placeholder="Your password"
              />
            </div>
            <button type="submit" className="primary-btn login-btn">
              Login
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ---------- RENDER: MAIN APP ----------
  return (
    <div className="app-root">
      <div className="app-card">
        <header className="app-header">
          <div>
            <h1 className="app-title">
              Chemical Equipment Parameter Visualizer
            </h1>
            <p className="app-subtitle">
              Logged in as <strong>{auth.username}</strong>
            </p>
          </div>
          <button className="secondary-btn" onClick={handleLogout}>
            Logout
          </button>
        </header>

        {error && <div className="error-box">{error}</div>}

        {/* Upload section */}
        <div className="section">
          <h2 className="section-title">Upload CSV File</h2>

          <div className="file-upload-container">
            <label className="file-upload-label">
              <div className="file-upload-content">
                <i className="fas fa-file-csv" />
                <div className="file-upload-text">
                  <div className="file-name">
                    {file ? file.name : "Choose a file or drag it here"}
                  </div>
                  <div className="file-hint">
                    Supported formats: .csv (Max 10MB)
                  </div>
                </div>
              </div>
              <input
                type="file"
                accept=".csv"
                onChange={handleFileChange}
                className="file-input"
                id="file-upload"
              />
            </label>

            <div className="upload-actions">
              <button
                className="primary-btn"
                onClick={handleUpload}
                disabled={!file || isLoading}
              >
                {isLoading ? "Uploading..." : "Upload & Analyze"}
              </button>

              {file && (
                <button
                  className="secondary-btn"
                  onClick={() => {
                    setFile(null);
                    const input = document.getElementById("file-upload");
                    if (input) input.value = "";
                  }}
                >
                  Clear
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Hint when no dataset yet */}
        {!dataset && (
          <p className="text-sm text-gray-500">
            Upload a CSV file to view charts, summary and data preview.
          </p>
        )}

        {/* Only show these AFTER dataset is loaded */}
        {dataset && (
          <>
            {/* Chart */}
            <div className="section">
              <div className="section-title">Equipment Type Distribution</div>
              <div className="chart-container">
                <Bar data={chartData} />
              </div>
            </div>

            {/* Preview table */}
            <div className="section">
              <div className="section-title">Preview (First 10 Rows)</div>
              {renderTable()}
            </div>

            {/* Summary */}
            <div className="section">
              <div className="section-title">Summary</div>
              {renderSummary()}
            </div>

            {/* PDF Download */}
            <div className="section">
              <div className="section-title">Report</div>
              <button className="primary-btn" onClick={downloadPDF}>
                Download PDF Report
              </button>
            </div>

            {/* Last 5 datasets */}
            <div className="section">
              <div className="section-title">Last 5 Datasets</div>
              <ul className="history-list">
                {history.map((d) => (
                  <li key={d.id}>
                    <span className="history-name">{d.name}</span>
                    <span className="history-date">
                      {new Date(d.uploaded_at).toLocaleString()}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

export default App;
