import React, { useState, useEffect } from "react";

function HealthStatus() {
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Use environment variable with fallback
  const MS2_HEALTH_URL = import.meta.env.VITE_MS2_HEALTH_URL || "http://localhost:8002/api/ms2/health";

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(MS2_HEALTH_URL);
      const data = await response.json();
      setHealth(data);
    } catch (err) {
      setError("Unable to connect to MS2 service");
      console.error("Health check error:", err);
    } finally {
      setLoading(false);
    }
  };

  // Check health on mount and every 30 seconds
  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = () => {
    if (error) return "#dc3545"; // Red
    if (!health) return "#6c757d"; // Gray
    if (health.status === "healthy") return "#28a745"; // Green
    return "#ffc107"; // Yellow
  };

  const getStatusIcon = () => {
    if (loading) return "⏳";
    if (error) return "❌";
    if (health?.status === "healthy") return "✅";
    return "⚠️";
  };

  return (
    <div
      style={{
        position: "fixed",
        top: "20px",
        right: "20px",
        padding: "12px 16px",
        background: "white",
        borderRadius: "8px",
        boxShadow: "0 2px 8px rgba(0,0,0,0.15)",
        minWidth: "200px",
        zIndex: 1000,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
        <div
          style={{
            width: "10px",
            height: "10px",
            borderRadius: "50%",
            background: getStatusColor(),
            animation: loading ? "pulse 1.5s infinite" : "none",
          }}
        />
        <strong style={{ fontSize: "14px" }}>MS2 Service</strong>
      </div>

      <div style={{ marginTop: "8px", fontSize: "12px", color: "#666" }}>
        {loading && <div>Checking...</div>}
        {error && <div style={{ color: "#dc3545" }}>{getStatusIcon()} {error}</div>}
        {health && !error && (
          <div>
            <div style={{ color: getStatusColor() }}>
              {getStatusIcon()} {health.status || "Unknown"}
            </div>
            {health.database && (
              <div style={{ marginTop: "4px" }}>
                DB: {health.database === "connected" ? "✓" : "✗"}
              </div>
            )}
            {health.version && (
              <div style={{ marginTop: "2px", fontSize: "11px", color: "#999" }}>
                v{health.version}
              </div>
            )}
          </div>
        )}
      </div>

      <button
        onClick={checkHealth}
        disabled={loading}
        style={{
          marginTop: "8px",
          padding: "4px 8px",
          fontSize: "11px",
          background: "#f8f9fa",
          border: "1px solid #ddd",
          borderRadius: "4px",
          cursor: loading ? "not-allowed" : "pointer",
          width: "100%",
        }}
      >
        {loading ? "Checking..." : "Refresh"}
      </button>

      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.3; }
          }
        `}
      </style>
    </div>
  );
}

export default HealthStatus;
