import React, { useState, useEffect } from 'react';
import MS2HealthStatus from './components/MS2HealthStatus.jsx';
import MS3HealthStatus from './components/MS3HealthStatus.jsx';
import MS4TrialMatchResults from './components/MS4TrialMatchResults.jsx';
import '../../index.css';
import '../../MS4TrialMatchResults.css';
import '../../HealthStatusHeader.css';

/**
 * Clinical Trial Patient Matcher App
 * Workflow:
 * 1. User selects a condition (diabetes, dementia, cancer)
 * 2. Search for trials matching that condition (MS2)
 * 3. Fetch patient phenotypes (MS3)
 * 4. Display matched patients to selected trial (MS4)
 */
function App() {
  const [selectedCondition, setSelectedCondition] = useState('diabetes');
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);
  const [parsedCache, setParsedCache] = useState({});
  const [expandedTrial, setExpandedTrial] = useState(null);
  const [selectedTrial, setSelectedTrial] = useState(null);
  const [patients, setPatients] = useState([]);
  const [showMatchResults, setShowMatchResults] = useState(false);

  const CONDITIONS = ['diabetes', 'dementia', 'cancer'];

  const API_SEARCH_URL = import.meta.env.VITE_API_SEARCH_URL || 'http://localhost:8001/search-trials';
  const API_MS2_URL = import.meta.env.VITE_API_DISPLAY_URL || 'http://localhost:8002/api/ms2';
  const API_MS3_URL = import.meta.env.VITE_API_MS3_URL || 'http://localhost:8003/api/ms3';
  const API_MS4_URL = import.meta.env.VITE_API_MS4_URL || 'http://localhost:8004/api/ms4';

  // ============ Search for trials by condition ============
  const handleSearch = async () => {
    setError(null);
    setResults(null);
    setLoading(true);
    setSelectedTrial(null);
    setShowMatchResults(false);

    try {
      const res = await fetch(API_SEARCH_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term: selectedCondition })
      });

      const data = await res.json();
      console.log('=== API RESPONSE ===');
      console.log('Full response:', data);
      console.log('Trials array:', data.trials);
      console.log('First trial:', data.trials?.[0]);
      if (data.trials?.[0]) {
        console.log('First trial keys:', Object.keys(data.trials[0]));
      }

      if (data.trials && data.trials.length > 0) {
        setResults(data);
        setError('');
        fetchParsedCriteria(data.trials);
        // Fetch patients for selected condition
        fetchPatients(selectedCondition);
      } else if (data.message) {
        setError(data.message);
        setResults(null);
      } else {
        setError('No trials found');
        setResults(null);
      }
    } catch (error) {
      console.error('API Error:', error);
      setError('Error fetching data. Please try again.');
      setResults(null);
    } finally {
      setLoading(false);
    }
  };

  // ============ Fetch MS2 parsed criteria for trials ============
  const fetchParsedCriteria = async (trials) => {
    console.log('=== FETCHING CRITERIA FOR TRIALS ===');
    console.log('Trials received:', trials);
    console.log('Trials length:', trials.length);
    
    if (trials.length > 0) {
      const firstTrial = trials[0];
      console.log('First trial object:', firstTrial);
      console.log('First trial keys:', Object.keys(firstTrial));
      
      // Try different possible field names
      console.log('trial.nctid:', firstTrial.nctid);
      console.log('trial.NCT_ID:', firstTrial.NCT_ID);
      console.log('trial.nct_id:', firstTrial.nct_id);
      console.log('trial.id:', firstTrial.id);
    }

    const cache = { ...parsedCache };

    for (const trial of trials) {
      console.log('=== Processing trial ===');
      console.log('Trial object:', trial);
      
      // Try to find the NCT ID using different possible field names
      const nctId = trial.nctid || trial.NCT_ID || trial.nct_id || trial.id;
      
      console.log('Final nctId value:', nctId);
      
      if (!nctId) {
        console.warn('Could not find NCT ID in trial:', trial);
        continue;
      }
      
      if (cache[nctId]) {
        console.log('NCT ID already cached:', nctId);
        continue;
      }

      try {
        console.log('Fetching criteria from:', `${API_MS2_URL}/parsed-criteria/${nctId}`);
        const response = await fetch(`${API_MS2_URL}/parsed-criteria/${nctId}`);
        if (response.ok) {
          const parsed = await response.json();
          cache[nctId] = parsed;
          console.log('Successfully cached criteria for', nctId);
        } else {
          console.error('Failed to fetch criteria for', nctId, 'Status:', response.status);
        }
      } catch (err) {
        console.error(`Error fetching criteria for ${nctId}:`, err);
      }
    }

    setParsedCache(cache);
  };

  // ============ Fetch MS3 patients for selected condition ============
  const fetchPatients = async (condition) => {
    try {
      const response = await fetch(`${API_MS3_URL}/patients?condition=${condition}`);
      if (response.ok) {
        const data = await response.json();
        const patientIds = data.patients || [];

      console.log(`Fetching phenotypes for ${patientIds.length} patients...`);

      // Fetch full phenotype for each patient
      const fullPatients = await Promise.all(
        patientIds.map(p => {
          const id = p.patient_id || p.id;
          return fetch(`${API_MS3_URL}/patient-phenotype/${id}`)
            .then(r => r.json())
            .catch(err => {
              console.error(`Failed to fetch phenotype for ${id}:`, err);
              return p; // Fallback to minimal data
            });
        })
      );

      console.log(`Phenotypes loaded! First patient:`, fullPatients);
      setPatients(fullPatients);  // ← NOW HAS FULL DATA!
    } else {
      console.warn('No patients found for condition');
      setPatients([]);
    }
  } catch (err) {
    console.error('Error fetching patients:', err);
    setPatients([]);
  }
};

  // ============ Trial Expansion Toggle ============
  const toggleExpanded = (trialId) => {
    setExpandedTrial(expandedTrial === trialId ? null : trialId);
  };

  // ============ Handle trial selection to show MS4 match results ============
  const handleSelectTrial = (trial) => {
    const trialId = trial.nctid || trial.NCT_ID || trial.nct_id || trial.id;
    console.log('Trial selected:', trialId, 'patients count:', patients.length);
    setSelectedTrial(trial);  // pass full trial object
    setShowMatchResults(true);

    // Scroll to match results
    setTimeout(() => {
      const element = document.querySelector('.match-results-section');
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }, 100);
  };

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Clinical Trial Patient Matcher</h1>
        <p>Find the best clinical trials for patients based on their health profiles</p>

        {/* MS2, MS3 HEALTH STATUS - ABOVE DROPDOWN */}
        <div className="services-health-bar">
          <div className="service-status">
            <label>MS2 Status</label>
            <MS2HealthStatus nctId="system" />
          </div>
          <div className="service-status">
            <label>MS3 Status</label>
            <MS3HealthStatus patientId="system" />
          </div>
        </div>
      </header>

      <main className="app-main">
        {/* Step 1: Condition Selection & Search */}
        <section className="search-section card">
          <h2>Step 1: Select a Medical Condition</h2>

          <div className="condition-selector">
            <label htmlFor="condition-select">Choose a condition</label>
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
              {loading ? 'Searching...' : 'Search Trials'}
            </button>
          </div>

          {error && <div className="alert alert-error">{error}</div>}
        </section>

        {/* Step 2: Trial Results with MS2 Criteria */}
        {results && results.trials && (
          <section className="trials-section card">
            <h2>
              Step 2: Clinical Trials for{' '}
              {selectedCondition.charAt(0).toUpperCase() + selectedCondition.slice(1)}
            </h2>

            <div className="trials-list">
              {results.trials.map((trial) => {
                // Handle multiple possible field names for trial ID
                const trialId = trial.nctid || trial.NCT_ID || trial.nct_id || trial.id;
                const parsed = parsedCache[trialId];
                const isExpanded = expandedTrial === trialId;

                return (
                  <div key={trialId} className="trial-card card">
                    <div className="trial-header">
                      <div
                        className="trial-info"
                        onClick={() => toggleExpanded(trialId)}
                        style={{ cursor: 'pointer', flex: 1}}
                      >
                        <h3 className="trial-title">{trial.title}</h3>
                        <p className="trial-location">
                          Location: {trial.location || 'N/A'}
                        </p>
                        <p className="trial-nct">NCT ID: {trialId}</p>
                      </div>

                      <div className="trial-actions">
                        <span
                          className="toggle-icon"
                          onClick={() => toggleExpanded(trialId)}
                          style={{ cursor: 'pointer' }}
                        >
                          {isExpanded ? '▼' : '▶'}
                        </span>
                      </div>
                    </div>

                    {isExpanded && (
                      <div className="trial-body">
                        <p className="trial-summary">{trial.briefsummary}</p>

                        {parsed && (
  <div className="trial-criteria-summary">
    <h4>Eligibility Criteria Analysis</h4>
    <div className="criteria-stats">
      <div className="stat">
        <span className="stat-label">Model: </span>
        <span className="stat-value">
          {parsed.modelused || parsed.model_used || 'N/A'}
        </span>
      </div>
      <div className="stat">
        <span className="stat-label">Confidence: </span>
        <span className="stat-value">
          {parsed.parsingconfidence !== undefined && parsed.parsingconfidence !== null
            ? (parsed.parsingconfidence * 100).toFixed(1)
            : parsed.parsing_confidence !== undefined && parsed.parsing_confidence !== null
            ? (parsed.parsing_confidence * 100).toFixed(1)
            : 'N/A'}%
        </span>
      </div>
      <div className="stat">
        <span className="stat-label">Rules Extracted: </span>
        <span className="stat-value">
          {parsed.totalrulesextracted || parsed.total_rules_extracted || 0}
        </span>
      </div>
    </div>
  </div>
)}


                        {/* BUTTON WITH BETTER STATE INDICATION */}
                        <button
                          onClick={() => handleSelectTrial(trial)}
                          className={`btn btn--primary ${
                            selectedTrial === trialId ? 'btn--active' : ''
                          }`}
                          style={{
                            backgroundColor:
                              selectedTrial === trialId
                                ? '#10b981'
                                : undefined
                          }}
                        >
                          {selectedTrial === trialId
                            ? '✓ Viewing Patient Matches'
                            : 'View Patient Matches →'}
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
                Trial: <strong>
                  {selectedTrial?.nct_id || selectedTrial?.nctid || selectedTrial?.title || 'Unknown'}
                </strong>
              </p>
              <p>Patients Analyzed: <strong>{patients.length}</strong></p>
            </div>

            <MS4TrialMatchResults
              trialData={selectedTrial}
              patients={patients.map(p => ({
                patient_id: p.patient_id || p.id,
                id: p.id || p.patient_id,
                general: p.general || { demographics: p.demographics || {} },
                conditions: p.conditions || [],
                lab_results: p.lab_results || [],
                observations: p.observations || [],
                medications: p.medications || [],
                name: p.name
              }))}
            />
          </section>
        )}
      </main>

      <footer className="app-footer">
        <p>
          Team 31 - Clinical Trial Matching System (MS1, MS2, MS3, MS4
          Integration)
        </p>
      </footer>
    </div>
  );
}

export default App;