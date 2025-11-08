import React, { useState } from "react";
import HealthStatus from "./components/HealthStatus";

function App() {
  const [term, setTerm] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  // Use environment variables for API endpoints with fallback to localhost
  const API_SEARCH_URL = import.meta.env.VITE_API_SEARCH_URL || "http://localhost:8000/search-trials";
  const API_DISPLAY_URL = import.meta.env.VITE_API_DISPLAY_URL || "http://localhost:8002/display";

  const handleSearch = async () => {
    if (!/^[a-zA-Z0-9\\s]+$/.test(term)) {
      setError("❌ Please enter only letters and numbers.");
      setResults(null);
      return;
    }

    setError("");
    setResults(null);
    setLoading(true);

    try {
      const res = await fetch(API_SEARCH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term }),
      });

      const data = await res.json();

      if (data.message && data.message.includes("No results")) {
        setError(data.message);
        setResults(null);
      } else {
        const recv = await fetch(API_DISPLAY_URL);
        const recvData = await recv.json();
        setResults(recvData);
      }
    } catch (err) {
      setError("⚠️ Error fetching data. Please try again.");
      console.error("API Error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        fontFamily: "Arial, sans-serif",
        background: "linear-gradient(to bottom, #f8f9fa, #e9ecef)",
        minHeight: "100vh",
        padding: "20px",
      }}
    >
      {/* Health Status Component - Fixed in top right */}
      <HealthStatus />

      {/* ─────────────── Header ─────────────── */}
      <header style={{ textAlign: "center", marginBottom: "30px" }}>
        <h1 style={{ color: "#333", margin: 0 }}>🔎 Clinical Trial Search</h1>
        <p style={{ color: "#666", fontSize: "14px" }}>
          Find active clinical trials by entering a search term below.
        </p>
      </header>

      {/* ─────────────── Search Box ─────────────── */}
      <div
        style={{
          maxWidth: "600px",
          margin: "0 auto 30px",
          background: "white",
          padding: "20px",
          borderRadius: "8px",
          boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
        }}
      >
        <input
          type="text"
          placeholder="Enter search term (e.g., diabetes, cancer)"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          onKeyPress={(e) => e.key === "Enter" && handleSearch()}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "16px",
            border: "1px solid #ddd",
            borderRadius: "4px",
            marginBottom: "10px",
            boxSizing: "border-box",
          }}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            width: "100%",
            padding: "12px",
            fontSize: "16px",
            backgroundColor: loading ? "#ccc" : "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: "bold",
          }}
        >
          {loading ? "Searching..." : "Search Trials"}
        </button>
      </div>

      {/* ─────────────── Error Message ─────────────── */}
      {error && (
        <div
          style={{
            maxWidth: "600px",
            margin: "0 auto 20px",
            padding: "15px",
            background: "#f8d7da",
            color: "#721c24",
            border: "1px solid #f5c6cb",
            borderRadius: "4px",
            textAlign: "center",
          }}
        >
          {error}
        </div>
      )}

      {/* ─────────────── Loading Spinner ─────────────── */}
      {loading && (
        <div style={{ textAlign: "center", fontSize: "18px", color: "#666" }}>
          <div
            style={{
              display: "inline-block",
              width: "40px",
              height: "40px",
              border: "4px solid #f3f3f3",
              borderTop: "4px solid #007bff",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
            }}
          />
          <p>Fetching studies...</p>
        </div>
      )}

      {/* ─────────────── Results Display ─────────────── */}
      {results && results.studies && (
        <div style={{ maxWidth: "900px", margin: "0 auto" }}>
          <h2 style={{ textAlign: "center", color: "#333" }}>
            Found {results.studies.length} Clinical Trial(s)
          </h2>
          {results.studies.map((study, idx) => (
            <div
              key={idx}
              style={{
                background: "white",
                padding: "20px",
                marginBottom: "20px",
                borderRadius: "8px",
                boxShadow: "0 2px 8px rgba(0,0,0,0.1)",
              }}
            >
              <h3 style={{ marginTop: 0, color: "#007bff" }}>
                {study.title || "Untitled Study"}
              </h3>
              <p style={{ fontSize: "14px", color: "#555" }}>
                <strong>NCT ID:</strong> {study.nct_id || "N/A"}
              </p>
              <p style={{ fontSize: "14px", color: "#555" }}>
                <strong>Status:</strong> {study.recruitment_status || "N/A"}
              </p>
              <p style={{ fontSize: "14px", color: "#555" }}>
                <strong>Location:</strong> {study.location || "N/A"}
              </p>
              <p style={{ fontSize: "14px", color: "#555" }}>
                <strong>Phase:</strong> {study.phase?.join(", ") || "N/A"}
              </p>
              <p style={{ fontSize: "14px", color: "#555" }}>
                <strong>Lead Sponsor:</strong> {study.sponsor || "N/A"}
              </p>
            </div>
          ))}
        </div>
      )}

      {/* ─────────────── Empty State ─────────────── */}
      {!results && !loading && !error && (
        <div
          style={{
            textAlign: "center",
            color: "#999",
            fontSize: "16px",
            marginTop: "50px",
          }}
        >
          <p>Enter a term above to find active trials.</p>
        </div>
      )}

      {/* ─────────────── CSS Animation ─────────────── */}
      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
        `}
      </style>
    </div>
  );
}

export default App;
