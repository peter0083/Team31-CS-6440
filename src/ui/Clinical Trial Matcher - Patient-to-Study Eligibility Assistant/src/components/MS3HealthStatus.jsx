// MS3HealthStatus.jsx - Enhanced with DuckDB loading progress

import React, { useState, useEffect } from "react";

function MS3HealthStatus() {
  const [health, setHealth] = useState(null);
  const [initStatus, setInitStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Use environment variables with fallbacks
  const MS3_HEALTH_URL = import.meta.env.VITE_MS3_HEALTH_URL || "http://localhost:8003/live";
  const MS3_INIT_URL = import.meta.env.VITE_MS3_INIT_URL || "http://localhost:8003/api/ms3/initialization-status";

  const checkHealth = async () => {
    setError(null);
    try {
      const response = await fetch(MS3_HEALTH_URL);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setHealth(data);
    } catch (err) {
      setError("Unable to connect to MS3 service");
      console.error("MS3 health check error:", err);
    } finally {
      setLoading(false);
    }
  };

  const checkInitStatus = async () => {
    try {
      const response = await fetch(MS3_INIT_URL);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      const data = await response.json();
      setInitStatus(data);
    } catch (err) {
      console.error("MS3 initialization status error:", err);
    }
  };

  // Check health on mount and every 10 seconds
  // Check init status more frequently (every 2 seconds) during initialization
  useEffect(() => {
    checkHealth();
    checkInitStatus();

    const healthInterval = setInterval(checkHealth, 10000);
    const initInterval = setInterval(checkInitStatus, 2000);

    return () => {
      clearInterval(healthInterval);
      clearInterval(initInterval);
    };
  }, []);

  const getStatusColor = () => {
    if (error) return "#dc3545"; // Red
    if (!health) return "#6c757d"; // Gray
    if (health.status === "alive") return "#28a745"; // Green
    return "#ffc107"; // Yellow
  };

  const getStatusIcon = () => {
    if (loading) return "⏳";
    if (error) return "❌";
    if (health?.status === "alive") return "✅";
    return "⚠️";
  };

  const getInitProgressPercentage = () => {
    if (!initStatus || !initStatus.progress) return 0;
    const total = initStatus.progress.total_files || 1;
    const processed = initStatus.progress.files_processed || 0;
    return Math.round((processed / total) * 100);
  };

  const renderInitializationStatus = () => {
    if (!initStatus) return null;

    if (initStatus.is_initialized) {
      return (
        <div style={{ fontSize: "12px", color: "#28a745", marginTop: "8px" }}>
          ✅ Fully Initialized
          <br />
          {initStatus.progress.patients.toLocaleString()} patients loaded
        </div>
      );
    }

    if (initStatus.is_loading) {
      const progress = getInitProgressPercentage();
      return (
        <div style={{ fontSize: "12px", color: "#ffc107", marginTop: "8px" }}>
          ⏳ Initializing DuckDB...
          <br />
          Progress: {progress}% ({initStatus.progress.files_processed}/{initStatus.progress.total_files} files)
          <br />
          <small>
            {initStatus.progress.patients.toLocaleString()} patients |{" "}
            {initStatus.progress.conditions.toLocaleString()} conditions |{" "}
            {initStatus.progress.observations.toLocaleString()} observations
          </small>
          <div
            style={{
              width: "100%",
              height: "4px",
              backgroundColor: "#e9ecef",
              borderRadius: "2px",
              marginTop: "4px",
              overflow: "hidden",
            }}
          >
            <div
              style={{
                height: "100%",
                width: `${progress}%`,
                backgroundColor: "#ffc107",
                transition: "width 0.3s ease",
              }}
            />
          </div>
        </div>
      );
    }

    if (initStatus.error) {
      return (
        <div style={{ fontSize: "12px", color: "#dc3545", marginTop: "8px" }}>
          ❌ Initialization Error
          <br />
          {initStatus.error}
        </div>
      );
    }

    return null;
  };

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "8px",
        padding: "12px",
        backgroundColor: "#f8f9fa",
        borderRadius: "4px",
        border: `2px solid ${getStatusColor()}`,
        fontWeight: "500",
        minWidth: "200px",
      }}
    >
      <span style={{ fontSize: "20px" }}>{getStatusIcon()}</span>
      <div>
        <div>
          {loading ? "Checking..." : error ? error : `Status: ${health?.status || "unknown"}`}
        </div>
        {renderInitializationStatus()}
      </div>
    </div>
  );
}

export default MS3HealthStatus;
