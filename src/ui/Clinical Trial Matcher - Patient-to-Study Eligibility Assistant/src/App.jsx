import React, { useState, useEffect } from "react";
import MS2HealthStatus from "./components/MS2HealthStatus.jsx";
import MS3HealthStatus from "./components/MS3HealthStatus.jsx";
import MS4TrialMatchResults from "./components/MS4TrialMatchResults.jsx";
import "../../index.css";
import "../../MS4TrialMatchResults.css";
import "../../HealthStatusHeader.css";

/**
 * Clinical Trial Patient Matcher App
 * 
 * Workflow:
 * 1. User selects a condition (diabetes, dementia, cancer)
 * 2. Search for trials matching that condition (MS2)
 * 3. Fetch patient phenotypes (MS3)
 * 4. Display matched patients to selected trial (MS4)
 */

function App() {
  const [selectedCondition, setSelectedCondition] = useState("diabetes");
  const [results, setResults] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [parsedCache, setParsedCache] = useState({});
  const [expandedTrial, setExpandedTrial] = useState(null);
  const [selectedTrial, setSelectedTrial] = useState(null);
  const [patients, setPatients] = useState([]);
  const [showMatchResults, setShowMatchResults] = useState(false);

  const CONDITIONS = ["diabetes", "dementia", "cancer"];
  const API_SEARCH_URL =
    import.meta.env.VITE_API_SEARCH_URL || "http://localhost:8001/search-trials";
  const API_MS2_URL =
    import.meta.env.VITE_API_DISPLAY_URL || "http://localhost:8002/api/ms2";
  const API_MS3_URL =
    import.meta.env.VITE_API_MS3_URL || "http://localhost:8003/api/ms3";
  const API_MS4_URL =
    import.meta.env.VITE_API_MS4_URL || "http://localhost:8004/api/ms4";

  // Search for trials by condition
  const handleSearch = async () => {
    setError("");
    setResults(null);
    setLoading(true);
    setSelectedTrial(null);
    setShowMatchResults(false);

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
        // Fetch patients for selected condition
        fetchPatients(selectedCondition);
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

  // Fetch MS2 parsed criteria for trials
  const fetchParsedCriteria = async (trials) => {
    const cache = { ...parsedCache };

    for (const trial of trials) {
      const nctId = trial.nct_id;
      if (cache[nctId]) continue;

      try {
        const response = await fetch(
          `${API_MS2_URL}/parsed-criteria/${nctId}`
        );
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

  // Fetch MS3 patients for selected condition
  const fetchPatients = async (condition) => {
    try {
      const response = await fetch(`${API_MS3_URL}/patients?condition=${condition}`);

      if (response.ok) {
        const data = await response.json();
        setPatients(data.patients || []);
      } else {
        console.warn("No patients found for condition");
        setPatients([]);
      }
    } catch (err) {
      console.error("Error fetching patients:", err);
      setPatients([]);
    }
  };

  const toggleExpanded = (nctId) => {
    setExpandedTrial(expandedTrial === nctId ? null : nctId);
  };

  // ✅ FIXED: Handle trial selection to show MS4 match results
  const handleSelectTrial = (trial) => {
    console.log("🎯 Trial selected:", { trialId: trial.nct_id, patientsCount: patients.length });
    setSelectedTrial(trial.nct_id);
    setShowMatchResults(true);
    
    // Scroll to match results
    setTimeout(() => {
      const element = document.querySelector(".match-results-section");
      if (element) {
        element.scrollIntoView({ behavior: "smooth" });
      }
    }, 100);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>🏥 Clinical Trial Patient Matcher</h1>
        <p>
          Find the best clinical trials for patients based on their health
          profiles
        </p>

        {/* ✅ MS2 & MS3 HEALTH STATUS ABOVE DROPDOWN */}
        <div className="services-health-bar">
          <div className="service-status">
            <label>MS2 Status:</label>
            <MS2HealthStatus nctId="system" />
          </div>
          <div className="service-status">
            <label>MS3 Status:</label>
            <MS3HealthStatus patientId="system" />
          </div>
        </div>
      </header>

      <main className="app-main">
        {/* Step 1: Condition Selection & Search */}
        <section className="search-section card">
          <h2>Step 1: Select a Medical Condition</h2>

          <div className="condition-selector">
            <label htmlFor="condition-select">Choose a condition:</label>
            <select
              id="condition-select"
              value={selectedCondition}
              onChange={(e) => setSelectedCondition(e.target.value)}
              className="form-control"
            >
              {CONDITIONS.map((condition) => (
                <option key={condition} value={condition}>
                  {condition.charAt(0).toUpperCase() + condition.slice(1)}
                </option>
              ))}
            </select>

            <button
              onClick={handleSearch}
              disabled={loading}
              className="btn btn--primary"
            >
              {loading ? "Searching..." : "🔍 Search Trials"}
            </button>
          </div>

          {error && <div className="alert alert-error">{error}</div>}
        </section>

        {/* Step 2: Trial Results with MS2 Criteria */}
        {results && results.trials && (
          <section className="trials-section card">
            <h2>
              Step 2: Clinical Trials for{" "}
              {selectedCondition.charAt(0).toUpperCase() +
                selectedCondition.slice(1)}
            </h2>

            <div className="trials-list">
              {results.trials.map((trial) => {
                const parsed = parsedCache[trial.nct_id];
                const isExpanded = expandedTrial === trial.nct_id;

                return (
                  <div key={trial.nct_id} className="trial-card card">
                    <div
                      className="trial-header"
                      onClick={() => toggleExpanded(trial.nct_id)}
                    >
                      <div className="trial-info">
                        <h3 className="trial-title">{trial.title}</h3>
                          <p className="trial-location">Location: {trial.location}</p>
                        <p className="trial-nct">NCT ID: {trial.nct_id}</p>
                      </div>

                      <div className="trial-status">
                        <span className="toggle-icon">
                          {isExpanded ? "▼" : "▶"}
                        </span>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="trial-body">
                        <p className="trial-summary">
                          {trial.brief_summary}
                        </p>

                        {parsed && (
                          <div className="trial-criteria-summary">
                            <h4>Eligibility Criteria Analysis</h4>
                            <div className="criteria-stats">
                              <div className="stat">
                                <span className="stat-label">Model:</span>
                                <span className="stat-value">
                                  {parsed.model_used}
                                </span>
                              </div>
                              <div className="stat">
                                <span className="stat-label">Confidence:</span>
                                <span className="stat-value">
                                  {(parsed.parsing_confidence * 100).toFixed(0)}
                                  %
                                </span>
                              </div>
                              <div className="stat">
                                <span className="stat-label">
                                  Rules Extracted:
                                </span>
                                <span className="stat-value">
                                  {parsed.total_rules_extracted}
                                </span>
                              </div>
                            </div>
                          </div>
                        )}

                        {/* ✅ BUTTON WITH BETTER STATE INDICATION */}
                        <button
                          onClick={() => handleSelectTrial(trial)}
                          className={`btn btn--primary ${
                            selectedTrial === trial.nct_id ? "btn--active" : ""
                          }`}
                          style={{
                            backgroundColor:
                              selectedTrial === trial.nct_id
                                ? "#10b981"
                                : undefined,
                          }}
                        >
                          {selectedTrial === trial.nct_id
                            ? "✓ Viewing Patient Matches"
                            : "View Patient Matches →"}
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Step 3: MS4 Patient-Trial Matching */}
        {showMatchResults && selectedTrial && patients.length > 0 && (
          <section className="match-results-section card">
            <h2>Step 3: Patient-Trial Matching Results</h2>

            <div className="match-info">
              <p>
                Trial: <strong>{selectedTrial}</strong>
              </p>
              <p>
                Patients Analyzed: <strong>{patients.length}</strong>
              </p>
            </div>

            <MS4TrialMatchResults
              trialData={{ nct_id: selectedTrial }}
              patients={patients}
            />
          </section>
        )}

        {/* Step 4: Patient Phenotypes (MS3) */}
        {patients.length > 0 && (
          <section className="patients-section card">
            <h2>Patient Phenotypes (MS3)</h2>

            <div className="patients-grid">
                {patients.slice(0, 3).map((patient) => (
                  <div key={patient.patient_id || patient.id} className="patient-card">
                    <h4>Patient: {patient.patient_id || patient.id}</h4>
                    <p>Status: Loaded from MS3</p>
                  </div>
                ))}
            </div>

            {patients.length > 3 && (
              <p className="text-secondary">
                ... and {patients.length - 3} more patients
              </p>
            )}
          </section>
        )}
      </main>

      <footer className="app-footer">
        <p>
          Team 31 - Clinical Trial Matching System | MS1, MS2, MS3, MS4
          Integration
        </p>
      </footer>
    </div>
  );
}

export default App;
