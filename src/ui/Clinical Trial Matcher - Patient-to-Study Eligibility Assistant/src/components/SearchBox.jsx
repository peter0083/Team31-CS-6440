// SearchBox.jsx - Enhanced to show "No matches found" message

import { useState } from "react";

export default function SearchBox({ onResults }) {
  const [term, setTerm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchStatus, setSearchStatus] = useState(null);

  const handleSearch = async () => {
    if (!term.trim()) {
      setError("Please enter a search term");
      return;
    }

    setError("");
    setSearchStatus(null);
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/search-trials", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ term }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Search complete:", data);

      // Check if results are empty
      const trialCount = data?.trials?.length || 0;
      if (trialCount === 0) {
        setSearchStatus({
          type: "no-results",
          message: `No clinical trials found matching "${term}"`,
        });
      } else {
        setSearchStatus({
          type: "success",
          message: `Found ${trialCount} clinical trial${trialCount !== 1 ? "s" : ""}`,
        });
      }

      onResults(data);
      setTerm("");
    } catch (err) {
      setError("Search failed. Please try again.");
      setSearchStatus({
        type: "error",
        message: "Failed to search trials",
      });
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !loading) {
      handleSearch();
    }
  };

  return (
    <div style={{ marginBottom: "20px" }}>
      <div style={{ display: "flex", gap: "10px", marginBottom: "10px" }}>
        <input
          type="text"
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Search clinical trials (e.g., diabetes, hypertension)"
          disabled={loading}
          style={{
            flex: 1,
            padding: "10px",
            border: "1px solid #ddd",
            borderRadius: "4px",
            fontSize: "14px",
            opacity: loading ? 0.6 : 1,
          }}
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          style={{
            padding: "10px 20px",
            backgroundColor: loading ? "#ccc" : "#007bff",
            color: "white",
            border: "none",
            borderRadius: "4px",
            cursor: loading ? "not-allowed" : "pointer",
            fontWeight: "500",
          }}
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {error && (
        <div
          style={{
            color: "#dc3545",
            padding: "10px",
            backgroundColor: "#f8d7da",
            borderRadius: "4px",
            marginBottom: "10px",
          }}
        >
          ❌ {error}
        </div>
      )}

      {searchStatus && (
        <div
          style={{
            padding: "10px",
            backgroundColor:
              searchStatus.type === "success"
                ? "#d4edda"
                : searchStatus.type === "no-results"
                ? "#fff3cd"
                : "#f8d7da",
            color:
              searchStatus.type === "success"
                ? "#155724"
                : searchStatus.type === "no-results"
                ? "#856404"
                : "#721c24",
            borderRadius: "4px",
            marginBottom: "10px",
          }}
        >
          {searchStatus.type === "success"
            ? "✅"
            : searchStatus.type === "no-results"
            ? "ℹ️"
            : "❌"}{" "}
          {searchStatus.message}
        </div>
      )}
    </div>
  );
}
