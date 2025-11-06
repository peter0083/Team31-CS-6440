import React, { useState } from "react";

function App() {
  const [term, setTerm] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!/^[a-zA-Z0-9\s]+$/.test(term)) {
      setError("❌ Please enter only letters and numbers.");
      setResults(null);
      return;
    }

    setError("");
    setResults(null);
    setLoading(true);

    try {
      const res = await fetch("http://127.0.0.1:8000/search-trials", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term }),
      });
      const data = await res.json();

      if (data.message && data.message.includes("No results")) {
        setError(data.message);
        setResults(null);
      } else {
        const recv = await fetch("http://127.0.0.1:8002/display");
        const recvData = await recv.json();
        setResults(recvData);
      }
    } catch (err) {
      setError("⚠️ Error fetching data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: "40px", fontFamily: "Arial, sans-serif" }}>
      {/* ─────────────── Banner ─────────────── */}
      <header
        style={{
          backgroundColor: "#004080",
          color: "white",
          padding: "15px",
          textAlign: "center",
          fontSize: "1.8em",
          borderRadius: "8px",
          marginBottom: "25px",
        }}
      >
        Clinical Trial Matcher: Patient-to-Study Eligibility Assistant
      </header>

      {/* ─────────────── Search Bar ─────────────── */}
      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "20px" }}>
        <input
          type="text"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="Enter a medical condition or keyword"
          style={{
            width: "400px",
            padding: "10px",
            border: "1px solid #ccc",
            borderRadius: "6px",
            fontSize: "1em",
          }}
          disabled={loading}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            backgroundColor: loading ? "#6c757d" : "#004080",
            color: "white",
            border: "none",
            padding: "10px 16px",
            borderRadius: "6px",
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {/* ─────────────── Error ─────────────── */}
      {error && (
        <p style={{ color: "red", marginTop: "10px", fontWeight: "bold" }}>{error}</p>
      )}

      {/* ─────────────── Loading Spinner ─────────────── */}
      {loading && (
        <div style={{ marginTop: "20px", textAlign: "center" }}>
          <div
            style={{
              display: "inline-block",
              width: "60px",
              height: "60px",
              border: "6px solid #f3f3f3",
              borderTop: "6px solid #004080",
              borderRadius: "50%",
              animation: "spin 1s linear infinite",
            }}
          />
          <p style={{ marginTop: "10px" }}>Fetching studies...</p>
        </div>
      )}

      {/* ─────────────── Results ─────────────── */}
      <div style={{ marginTop: "20px" }}>
        {results && Array.isArray(results) && results.length > 0 && !loading ? (
          <ul style={{ listStyleType: "none", padding: 0 }}>
            {results.map((study, idx) => (
              <li
                key={idx}
                style={{
                  marginBottom: "12px",
                  padding: "10px",
                  border: "1px solid #ccc",
                  borderRadius: "8px",
                  backgroundColor: "#f8f9fa",
                }}
              >
                <strong>{study.title}</strong>
                <p style={{ margin: "8px 0" }}>
                  <b>Status:</b> {study.recruitment_status || "N/A"} <br />
                  <b>Location:</b> {study.location || "N/A"} <br />
                  <b>Phase:</b> {study.phase?.join(", ") || "N/A"} <br />
                  <b>Lead Sponsor:</b> {study.sponsor || "N/A"}
                </p>
              </li>
            ))}
          </ul>
        ) : (
          !error && !loading && <p>Enter a term above to find active trials.</p>
        )}
      </div>

      {/* ─────────────── Spinner Animation CSS ─────────────── */}
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
