// MS3HealthStatus.jsx - Fixed to show "Patients fully loaded" when initialization is skipped

import React, { useState, useEffect } from "react";

function MS3HealthStatus() {
  const [health, setHealth] = useState(null);
  const [initStatus, setInitStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
      console.log("Init status updated:", data);
    } catch (err) {
      console.error("MS3 initialization status error:", err);
    }
  };

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
    if (error) return "#dc3545";
    if (!health) return "#6c757d";
    if (health.status === "alive") return "#28a745";
    return "#ffc107";
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
    if (!initStatus) {
      return (
        <div style={{ fontSize: "12px", color: "#666", marginTop: "8px" }}>
          ⏳ Fetching initialization status...
        </div>
      );
    }

    if (initStatus.is_initialized) {
      // NEW: Check if this is a skip-initialization case
      // (is_initialized=true but is_loading=false and files_processed=0)
      const isSkipped = initStatus.progress.files_processed === 0 && !initStatus.is_loading;
      
      if (isSkipped) {
        // Tables already populated - show "fully loaded" message
        return (
          <div style={{ fontSize: "12px", color: "#28a745", marginTop: "8px" }}>
            <div style={{ fontWeight: "600", marginBottom: "6px" }}>
              ✅ Patients Fully Loaded
            </div>
            <div>
              👥 <strong>{initStatus.progress.patients.toLocaleString()}</strong> patients
            </div>
            <div>
              🏥 <strong>{initStatus.progress.conditions.toLocaleString()}</strong> conditions
            </div>
            <div>
              📊 <strong>{initStatus.progress.observations.toLocaleString()}</strong> observations
            </div>
            <div>
              💊 <strong>{initStatus.progress.medications.toLocaleString()}</strong> medications
            </div>
          </div>
        );
      } else {
        // Normal initialization complete
        return (
          <div style={{ fontSize: "12px", color: "#28a745", marginTop: "8px" }}>
            ✅ Initialization Complete
            <br />
            {initStatus.progress.patients.toLocaleString()} patients loaded
          </div>
        );
      }
    }

    if (initStatus.is_loading) {
      const progress = getInitProgressPercentage();
      return (
        <div style={{ fontSize: "12px", color: "#ffc107", marginTop: "8px" }}>
          <div style={{ fontWeight: "600", marginBottom: "6px" }}>
            ⏳ Initializing DuckDB...
          </div>
          <div>
            <strong>Progress:</strong> {progress}% ({initStatus.progress.files_processed}/{initStatus.progress.total_files} files)
          </div>
          <div style={{ marginTop: "6px", fontSize: "11px" }}>
            <div>
              👥 <strong>{initStatus.progress.patients.toLocaleString()}</strong> patients
            </div>
            <div>
              🏥 <strong>{initStatus.progress.conditions.toLocaleString()}</strong> conditions
            </div>
            <div>
              📊 <strong>{initStatus.progress.observations.toLocaleString()}</strong> observations
            </div>
            <div>
              💊 <strong>{initStatus.progress.medications.toLocaleString()}</strong> medications
            </div>
          </div>
          <div
            style={{
              width: "100%",
              height: "6px",
              backgroundColor: "#e9ecef",
              borderRadius: "3px",
              marginTop: "8px",
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
        alignItems: "flex-start",
        gap: "12px",
        padding: "16px",
        backgroundColor: "#f8f9fa",
        borderRadius: "6px",
        border: `2px solid ${getStatusColor()}`,
        fontWeight: "500",
        minWidth: "280px",
      }}
    >
      <span style={{ fontSize: "24px", flexShrink: 0 }}>
        {getStatusIcon()}
      </span>
      <div style={{ flex: 1 }}>
        {/* Service Name */}
        <div style={{ fontSize: "14px", fontWeight: "600", marginBottom: "4px" }}>
          MS3 Service - Synthea Patient Loader Status
        </div>

        {/* Status */}
        <div style={{ fontSize: "13px", color: "#666" }}>
          {loading ? "Checking..." : error ? error : `Status: ${health?.status || "unknown"}`}
        </div>

        {/* Initialization Details */}
        {renderInitializationStatus()}
      </div>
    </div>
  );
}

export default MS3HealthStatus;
