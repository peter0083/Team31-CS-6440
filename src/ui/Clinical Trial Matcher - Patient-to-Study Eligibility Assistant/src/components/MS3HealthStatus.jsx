import React, { useState, useEffect } from "react";

/**
 * MS3HealthStatus.jsx - Simplified to show only initialization status
 * 
 * Shows whether MS3's patient database initialization is complete
 */

function MS3HealthStatus() {
  const [isInitialized, setIsInitialized] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const MS3_INIT_URL = 
    import.meta.env.VITE_MS3_INIT_URL || "http://localhost:8003/api/ms3/initialization-status";

  /**
   * Check MS3 initialization status
   */
  const checkInitStatus = async () => {
    try {
      setError(null);
      const response = await fetch(MS3_INIT_URL);
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      setIsInitialized(data.is_initialized || false);
      console.log("✅ MS3 initialization status:", data.is_initialized);
    } catch (err) {
      console.error("Error checking MS3 initialization status:", err);
      setError("Unable to connect to MS3");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // Initial check
    checkInitStatus();

    // Poll for status updates every 5 seconds until initialized
    const interval = setInterval(() => {
      checkInitStatus();
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  // Render loading state
  if (loading) {
    return (
    <div className="card">
      <div className="health-status-card">
        <div className="status-header">
          <h3>🗄️ MS3 - Patient Data Loader</h3>
          <span className="status-badge loading">⏳ Checking...</span>
        </div>
      </div>
    </div>
    );
  }

  // Render error state
  if (error) {
    return (
    <div className="card">
      <div className="health-status-card">
        <div className="status-header">
          <h3>🗄️ MS3 - Patient Data Loader</h3>
          <span className="status-badge error">❌ Error</span>
        </div>
        <div className="status-content">
          <p className="error-message">{error}</p>
        </div>
      </div>
    </div>
    );
  }

  // Render initialization status
  return (
  <div className="card">
    <div className="health-status-card">
      <div className="status-header">
        <h3>🗄️ MS3 - Patient Data Loader</h3>
        {isInitialized ? (
          <span className="status-badge success">✅ Ready</span>
        ) : (
          <span className="status-badge warning">⏳ Initializing...</span>
        )}
      </div>

      <div className="status-content">
        {isInitialized ? (
          <div className="status-info">
            <p className="status-message success">
              ✅ <strong>Patient database initialized</strong>
            </p>
            <p className="status-detail">
              All patient records are loaded and available
            </p>
          </div>
        ) : (
          <div className="status-info">
            <p className="status-message warning">
              ⏳ <strong>Initializing patient database...</strong>
            </p>
            <p className="status-detail">
              Loading patient records from database, please wait
            </p>
          </div>
        )}
      </div>
    </div>
  </div>
  );
}

export default MS3HealthStatus;
