import { useState } from "react";

export default function SearchBox({ onResults }) {
  const [term, setTerm] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!term.trim()) return;
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/search-trials", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term }),
      });

      const data = await response.json();
      console.log("Search complete:", data);
      onResults(data);
    } catch (err) {
      console.error("Search failed:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ textAlign: "center", margin: "2em" }}>
      <input
        type="text"
        placeholder="Enter a condition (e.g., diabetes)"
        value={term}
        onChange={(e) => setTerm(e.target.value)}
        style={{ padding: "0.5em", width: "300px" }}
      />
      <button onClick={handleSearch} disabled={loading} style={{ marginLeft: "1em" }}>
        {loading ? "Searching..." : "Search"}
      </button>
    </div>
  );
}
