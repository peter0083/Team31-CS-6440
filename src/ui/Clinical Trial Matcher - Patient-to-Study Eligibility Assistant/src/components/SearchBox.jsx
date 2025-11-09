import { useState } from "react";

export default function SearchBox({ onResults }) {
  const [term, setTerm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSearch = async () => {
    if (!term.trim()) {
      setError("Please enter a search term");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/search-trials", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      console.log("Search complete:", data);
      onResults(data);
      setTerm("");
    } catch (err) {
      setError("Search failed. Please try again.");
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
    <div className="w-full bg-white rounded-lg shadow-md p-6 mb-6">
      <h2 className="text-2xl font-bold text-blue-600 mb-4">Search Clinical Trials</h2>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          placeholder="Enter a search term (e.g., diabetes, cancer)..."
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          onKeyPress={handleKeyPress}
          disabled={loading}
          className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100"
        />
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold transition-all whitespace-nowrap"
        >
          {loading ? "Searching..." : "Search"}
        </button>
      </div>

      {error && (
        <div className="text-red-600 bg-red-50 p-3 rounded-lg border border-red-200 text-sm">
          {error}
        </div>
      )}
    </div>
  );
}
