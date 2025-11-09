import React, { useState, useEffect } from "react";
import HealthStatus from "./components/HealthStatus";

function App() {
  const [selectedCondition, setSelectedCondition] = useState("diabetes");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [parsedCache, setParsedCache] = useState({});
  const [expandedTrial, setExpandedTrial] = useState(null);

  const CONDITIONS = ["diabetes", "dementia", "cancer"];
  const API_SEARCH_URL = import.meta.env.VITE_API_SEARCH_URL || "http://localhost:8001/search-trials";
  const API_MS2_URL = import.meta.env.VITE_API_DISPLAY_URL || "http://localhost:8002/api/ms2";

  const handleSearch = async () => {
    setError("");
    setResults(null);
    setLoading(true);

    try {
      const res = await fetch(API_SEARCH_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term: selectedCondition }),
      });
      const data = await res.json();

      if (data.trials && data.trials.length > 0) {
        setResults(data);
        setError("");
        fetchParsedCriteria(data.trials);
      } else if (data.message) {
        setError(data.message);
        setResults(null);
      } else {
        setError("❌ No trials found");
        setResults(null);
      }
    } catch (error) {
      console.error("API Error:", error);
      setError("❌ Error fetching data. Please try again.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchParsedCriteria = async (trials) => {
    const cache = { ...parsedCache };
    for (const trial of trials) {
      const nctId = trial.nct_id;
      if (cache[nctId]) continue;

      try {
        const response = await fetch(`${API_MS2_URL}/parsed-criteria/${nctId}`);
        if (response.ok) {
          const parsed = await response.json();
          cache[nctId] = parsed;
        }
      } catch (err) {
        console.error(`Error fetching criteria for ${nctId}:`, err);
      }
    }
    setParsedCache(cache);
  };

  const toggleExpanded = (nctId) => {
    setExpandedTrial(expandedTrial === nctId ? null : nctId);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white py-8">
      <div className="max-w-6xl mx-auto px-4">
        <HealthStatus />

        <div className="bg-white rounded-lg shadow-lg p-8 mb-8">
          <h1 className="text-4xl font-bold text-blue-600 mb-4">
            Find Clinical Trials
          </h1>
          <p className="text-gray-600 mb-6">
            Select a condition and discover clinical trials that match your health needs
          </p>

          <div className="flex gap-3 mb-6">
            {CONDITIONS.map((condition) => (
              <button
                key={condition}
                onClick={() => setSelectedCondition(condition)}
                className={`px-6 py-2 rounded-lg font-semibold transition-all ${
                  selectedCondition === condition
                    ? "bg-blue-600 text-white shadow-md"
                    : "bg-gray-200 text-gray-700 hover:bg-gray-300"
                }`}
              >
                {condition.charAt(0).toUpperCase() + condition.slice(1)}
              </button>
            ))}
          </div>

          <button
            onClick={handleSearch}
            disabled={loading}
            className="w-full px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-semibold text-lg transition-all"
          >
            {loading ? "Searching..." : "Search Trials"}
          </button>

          {error && (
            <div className="text-red-600 bg-red-50 p-4 rounded-lg mt-4 border border-red-200">
              {error}
            </div>
          )}

          {loading && (
            <div className="text-center py-8 mt-4">
              <div className="inline-block">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
              </div>
              <p className="text-gray-600 mt-2">Fetching studies...</p>
            </div>
          )}
        </div>

        {results && results.trials && results.trials.length > 0 && (
          <div className="grid gap-6">
            {results.trials.map((trial) => {
              const parsed = parsedCache[trial.nct_id];
              const isExpanded = expandedTrial === trial.nct_id;

              return (
                <div
                  key={trial.nct_id}
                  className="bg-white rounded-lg shadow-md border-l-4 border-blue-500 overflow-hidden"
                >
                  <div className="p-6">
                    <h2 className="text-2xl font-bold text-blue-600 mb-4">
                      {trial.nct_id}
                    </h2>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
                      <div className="text-gray-700">
                        <span className="font-semibold">Status:</span>
                        <p>{trial.recruitment_status || "N/A"}</p>
                      </div>
                      <div className="text-gray-700">
                        <span className="font-semibold">Location:</span>
                        <p>{trial.location || "N/A"}</p>
                      </div>
                      <div className="text-gray-700">
                        <span className="font-semibold">Phase:</span>
                        <p>{trial.phase?.join(", ") || "Not specified"}</p>
                      </div>
                      <div className="text-gray-700">
                        <span className="font-semibold">Sponsor:</span>
                        <p>{trial.sponsor || "N/A"}</p>
                      </div>
                      <div className="text-gray-700">
                        <span className="font-semibold">Location:</span>
                        <p>{trial.location || "N/A"}</p>
                      </div>
                      <div className="text-gray-700">
                        <span className="font-semibold">Intervention:</span>
                        <p>{trial.intervention || "N/A"}</p>
                      </div>
                    </div>

                    {parsed && (
                      <div className="border-t pt-4">
                        <button
                          onClick={() => toggleExpanded(trial.nct_id)}
                          className="text-blue-600 hover:text-blue-700 font-semibold mb-4"
                        >
                          {isExpanded ? "Hide Details ▼" : "View Details ▶"}
                        </button>

                        {isExpanded && (
                          <div className="bg-blue-50 rounded-lg p-4 space-y-4">
                            <div className="grid grid-cols-3 gap-4 text-sm">
                              <div>
                                <p className="font-semibold text-gray-700">Model Used</p>
                                <p className="text-blue-600">{parsed.model_used}</p>
                              </div>
                              <div>
                                <p className="font-semibold text-gray-700">Confidence</p>
                                <p className="text-blue-600">{(parsed.parsing_confidence * 100).toFixed(0)}%</p>
                              </div>
                              <div>
                                <p className="font-semibold text-gray-700">Rules Extracted</p>
                                <p className="text-blue-600">{parsed.total_rules_extracted}</p>
                              </div>
                            </div>

                            {parsed.inclusion_criteria && parsed.inclusion_criteria.length > 0 && (
                              <div>
                                <p className="font-semibold text-green-700 mb-2">✅ Inclusion Criteria:</p>
                                <ul className="space-y-1 text-sm text-gray-700">
                                  {parsed.inclusion_criteria.map((rule, idx) => (
                                    <li key={idx}>• {rule.description}</li>
                                  ))}
                                </ul>
                              </div>
                            )}

                            {parsed.exclusion_criteria && parsed.exclusion_criteria.length > 0 && (
                              <div>
                                <p className="font-semibold text-red-700 mb-2">❌ Exclusion Criteria:</p>
                                <ul className="space-y-1 text-sm text-gray-700">
                                  {parsed.exclusion_criteria.map((rule, idx) => (
                                    <li key={idx}>• {rule.description}</li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    )}

                    {!parsed && !loading && (
                      <div className="text-center py-2 text-gray-500 text-sm">
                        ⏳ Parsed criteria loading...
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}

        {!loading && !results && !error && (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">Select a condition above and click Search to find trials.</p>
          </div>
        )}

        {!loading && results && (!results.trials || results.trials.length === 0) && !error && (
          <div className="text-center py-12 text-gray-500">
            <p className="text-lg">No trials found. Try another condition.</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
