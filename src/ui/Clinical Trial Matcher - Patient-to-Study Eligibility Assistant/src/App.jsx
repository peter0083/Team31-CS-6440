import React, { useState, useEffect } from "react";
import MS2HealthStatus from "./components/MS2HealthStatus.jsx";
import MS3HealthStatus from "./components/MS3HealthStatus.jsx";
import MS4TrialMatchResults from "./components/MS4TrialMatchResults.jsx";
import "../../index.css";
import "../../MS4TrialMatchResults.css";
import "../../HealthStatusHeader.css";


function App() {
  const [selectedCondition, setSelectedCondition] = useState("diabetes");
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [parsedCache, setParsedCache] = useState({});
  const [expandedTrial, setExpandedTrial] = useState(null);
  const [selectedTrial, setSelectedTrial] = useState(null);
  const [showMatchResults, setShowMatchResults] = useState(false);

  const CONDITIONS = ["diabetes", "dementia", "cancer"];

  // API URLs from environment variables
  const APISEARCHURL = import.meta.env.VITE_API_SEARCH_URL || "http://localhost:8000/search";
  const APIMS2URL = import.meta.env.VITE_API_MS2_URL || "http://localhost:8002";

  useEffect(() => {
    console.log("App mounted!");
  }, []);

  /**
   * Step 1: Search for trials by condition (calls MS1 → MS2)
   */
  const handleSearch = async () => {
    setError(null);
    setResults(null);
    setLoading(true);
    setSelectedTrial(null);
    setShowMatchResults(false);

    try {
      const res = await fetch(APISEARCHURL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term: selectedCondition }),
      });

      if (!res.ok) {
        throw new Error(`API returned ${res.status}`);
      }

      const data = await res.json();

      if (data.trials && data.trials.length > 0) {
        console.log(`✅ Found ${data.trials.length} trials for ${selectedCondition}`);
        setResults(data);
        setError(null);
        
        // Pre-fetch parsed criteria for all trials
        fetchParsedCriteria(data.trials);
      } else {
        setError(`No trials found for ${selectedCondition}`);
        setResults(null);
      }
    } catch (error) {
      console.error("API Error:", error);
      setError("Error fetching data. Please try again.");
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Pre-fetch parsed criteria from MS2 for all trials
   */
  const fetchParsedCriteria = async (trials) => {
    const newCache = { ...parsedCache };
    
    for (const trial of trials) {
      const nctId = trial.nct_id || trial.NCT_ID || trial.nctid;
      
      if (!nctId || newCache[nctId]) {
        continue; // Skip if already cached
      }

      try {
        const url = `${APIMS2URL}/api/ms2/parsed-criteria/${nctId}`;
        console.log(`Fetching criteria from: ${url}`);
        
        const response = await fetch(url);
        
        if (response.ok) {
          const criteriaData = await response.json();
          newCache[nctId] = criteriaData;
          console.log(`Successfully cached criteria for ${nctId}`);
        } else {
          console.warn(`Failed to fetch criteria for ${nctId}: ${response.status}`);
          newCache[nctId] = null;
        }
      } catch (err) {
        console.error(`Error fetching criteria for ${nctId}:`, err);
        newCache[nctId] = null;
      }
    }

    setParsedCache(newCache);
  };

  /**
   * Toggle trial details expansion
   */
    const toggleExpand = (nctId) => {
    setExpandedTrial(expandedTrial === nctId ? null : nctId);
  };

  /**
   * Handle trial selection - triggers MS4 matching
   */
  const handleSelectTrial = (trial) => {
    const trialId = trial.nct_id || trial.NCT_ID || trial.nctid || trial.id;
    console.log("Trial selected:", trialId);
    
    setSelectedTrial(trial);
    setShowMatchResults(true);
    
    // Scroll to results section after a brief delay
    setTimeout(() => {
      const element = document.querySelector(".match-results-section");
      if (element) {
        element.scrollIntoView({ behavior: "smooth" });
      }
    }, 100);
  };

  return (
    <div className="container">
      <header className="header">
        <h1>🏥 Clinical Trial Patient Matcher</h1>
        <p className="subtitle">
          Find the best clinical trials for patients with specific conditions
        </p>
      </header>

      {/* Health Status Dashboard */}
      <section className="health-status-section">
        { /* <h2>System Health Status</h2> */}
        <div className="health-status-grid">
            { /* <MS2HealthStatus /> */}
            { /* <MS3HealthStatus /> */}
        </div>
      </section>

    {/* Step 1: Condition Selection and Trial Search */}
    <section className="search-section card">
      <h2>Step 1: Select Condition and Search Trials</h2>

      <div className="input-group" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        {/* Dropdown */}
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: '8px' }}>
          <div style={{ flex: 1 }}>
            <label htmlFor="condition-select">Medical Condition:</label>
            <select
              id="condition-select"
              value={selectedCondition}
              onChange={(e) => setSelectedCondition(e.target.value)}
              className="select-input"
              style={{
                width: '100%',
                backgroundColor: 'var(--color-surface)',
                color: 'var(--color-text)',
                padding: '8px 12px',
                borderRadius: '4px',
                border: '1px solid var(--color-card-border)',
                cursor: 'pointer',
                fontSize: '16px'
              }}
            >
              {CONDITIONS.map((cond) => (
                <option key={cond} value={cond}>
                  {cond.charAt(0).toUpperCase() + cond.slice(1)}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Button - Separate Line */}
        <button
          onClick={handleSearch}
          disabled={loading}
          className="px-4 py-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 disabled:bg-gray-100 disabled:text-gray-400 font-semibold text-sm transition-all"
        >
          {loading ? "Searching..." : "Search Trials"}
        </button>

      {error && (
        <div className="error-message">
          <strong>Error:</strong> {error}
        </div>
      )}
      </div>
    </section>


     {/* Step 2: Trial Selection */}
{results && results.trials && results.trials.length > 0 && (
  <section className="results-section card">
    <h2>Step 2: Select a Trial</h2>
    <p className="info-text">
      Found <strong>{results.trials.length}</strong> trials for{" "}
      <strong>{selectedCondition}</strong>
    </p>

    <div className="trials-list">
      {results.trials.map((trial) => {
        const nctId = trial.nct_id || trial.NCT_ID || trial.nctid;
        const title = trial.official_title || trial.title || "No title available";
        const isExpanded = expandedTrial === nctId;
        const criteria = parsedCache[nctId];

        return (
          <div key={nctId} className="trial-card">
            {/* View Details Button */}
            <div
              className="px-4 py-2 bg-blue-100 text-blue-600 rounded-lg hover:bg-blue-200 transition-all"
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                cursor: 'pointer',
                width: 'fit-content',
                marginBottom: '8px'
              }}
              onClick={() => toggleExpand(nctId)}
            >
              <span>{isExpanded ? '▼' : '▶'}</span>
              <span>View Details</span>
            </div>

            {/* Trial Header */}
            <div
              className="trial-header"
              onClick={() => toggleExpand(nctId)}
              style={{ cursor: 'pointer'}}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', flex: 1 }}>
                <strong style={{ fontSize: '14px', color: '#666' }}>{nctId}</strong>
                <div className="trial-title">
                  <span className="trial-name" style={{ fontSize: '16px', fontWeight: '500' }}>
                    {title}
                  </span>
                </div>
              </div>
            </div>

            {/* Expanded Details Section */}
            {isExpanded && (
              <div className="trial-details" style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #eee' }}>
                <div className="detail-row" style={{ marginBottom: '8px' }}>
                  <strong>Phase:</strong> {trial.phase || "N/A"}
                </div>
                <div className="detail-row" style={{ marginBottom: '12px' }}>
                  <strong>Location:</strong> {trial.location || "N/A"}
                </div>

                {/* Eligibility Criteria */}
                {criteria ? (
                  <div className="criteria-section" style={{ marginTop: '12px' }}>
                    <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '8px' }}>
                      Eligibility Criteria
                    </h4>

                    {/* Inclusion Criteria */}
                    {criteria.inclusion_criteria && Array.isArray(criteria.inclusion_criteria) && criteria.inclusion_criteria.length > 0 && (
                      <div style={{ marginBottom: '12px' }}>
                        <h5 style={{ fontSize: '12px', color: '#28a745', fontWeight: '600', marginBottom: '6px' }}>
                          ✓ Inclusion Criteria ({criteria.inclusion_criteria.length})
                        </h5>
                        <ul style={{
                          fontSize: '13px',
                          paddingLeft: '24px',
                          marginTop: '0',
                          marginBottom: '8px',
                          lineHeight: '1.6'
                        }}>
                          {criteria.inclusion_criteria.map((item, i) => (
                            <li
                              key={i}
                              style={{
                                color: '#333',
                                marginBottom: '8px',
                                whiteSpace: 'normal',
                                wordWrap: 'break-word',
                                overflowWrap: 'break-word',
                                lineHeight: '1.6',
                                  color: '#e0e0e0'
                              }}
                            >
                              {item.description || item.raw_text || "N/A"}
                            </li>
                          ))}

                        </ul>
                      </div>
                    )}

                    {/* Exclusion Criteria */}
                    {criteria.exclusion_criteria && Array.isArray(criteria.exclusion_criteria) && criteria.exclusion_criteria.length > 0 && (
                      <div>
                        <h5 style={{ fontSize: '12px', color: '#c01f2f', fontWeight: '600', marginBottom: '6px' }}>
                          ✗ Exclusion Criteria ({criteria.exclusion_criteria.length})
                        </h5>
                        <ul style={{
                          fontSize: '13px',
                          paddingLeft: '24px',
                          marginTop: '0',
                          marginBottom: '0',
                          lineHeight: '1.6'
                        }}>
                          {criteria.exclusion_criteria.map((item, i) => (
                            <li
                              key={i}
                              style={{
                                color: '#333',
                                marginBottom: '8px',
                                whiteSpace: 'normal',
                                wordWrap: 'break-word',
                                overflowWrap: 'break-word',
                                lineHeight: '1.6',
                                  color: '#e0e0e0'
                              }}
                            >
                              {item.description || item.raw_text || "N/A"}
                            </li>
                          ))}

                        </ul>
                      </div>
                    )}
                  </div>
                ) : (
                  <p style={{ marginTop: '12px', color: '#999', fontSize: '13px' }}>
                    No criteria data available
                  </p>
                )}

                <div style={{
  marginTop: '16px',
  padding: '12px 16px',
  backgroundColor: '#2563eb',  // ✅ Blue box background
  borderRadius: '8px',
  border: '2px solid #1e40af',  // ✅ Darker blue border
  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.2)',  // ✅ Subtle shadow
  display: 'inline-block'
}}>
  <button
    className="btn-select-trial"
    onClick={() => handleSelectTrial(trial)}
    style={{
      background: 'none',
      border: 'none',
      color: '#ffffff',
      fontSize: '14px',
      fontWeight: '600',
      cursor: 'pointer',
      padding: '0',
      transition: 'transform 0.2s ease',
    }}
    onMouseEnter={(e) => e.target.style.transform = 'scale(1.05)'}
    onMouseLeave={(e) => e.target.style.transform = 'scale(1)'}
  >
    View Patient Matches →
  </button>
</div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  </section>
)}


      {/* Step 3: MS4 Patient-Trial Matching Results */}
      {showMatchResults && selectedTrial && (
        <section className="match-results-section card">
          <h2>Step 3: Patient-Trial Matching Results</h2>
          <div className="match-info">
            <p>
              Trial: <strong>{selectedTrial?.nct_id || "Unknown"}</strong>
            </p>
            <p className="info-text">
              MS4 will search <strong>all 1,097 cached patients</strong> and rank them by match percentage
            </p>
          </div>
          
          {/* MS4TrialMatchResults handles fetching from MS4's cache */}
          <MS4TrialMatchResults trialData={selectedTrial} />
        </section>
      )}
    </div>
  );
}

export default App;
